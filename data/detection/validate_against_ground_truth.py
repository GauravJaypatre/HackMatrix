"""Evaluate the implemented deterministic rules against labeled scenarios.

This module is an evaluation tool. Scenario labels are loaded only for
comparison after the Rule Engine has evaluated runtime transaction and HR data.
"""

from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Set, Tuple

import pandas as pd

from . import RuleEngine, RuleRegistry, RuleResult, load_rule_configuration
from .rules import CircularTransferRule, PrivilegeChangeRule, TransactionSplittingRule


DATA_DIR = Path(__file__).resolve().parent.parent
HR_DIR = DATA_DIR / "synthetic_hr"
ENTITIES_DIR = DATA_DIR / "entities"

SIGNAL_TO_RULE = {
    "privilege_change": "INSIDER.PRIVILEGE_CHANGE",
    "circular_transfer": "AML.CIRCULAR_TRANSFER",
    "transaction_splitting": "AML.TRANSACTION_SPLITTING",
}
RULE_TO_SIGNAL = {rule_id: signal for signal, rule_id in SIGNAL_TO_RULE.items()}


def _load_records(path: Path) -> List[Dict[str, str]]:
    return pd.read_csv(path, dtype=str).fillna("").to_dict("records")


def _split_ids(value: str) -> List[str]:
    return [item.strip() for item in str(value or "").replace(";", ",").split(",") if item.strip()]


def load_runtime_context() -> Dict[str, List[Dict[str, str]]]:
    """Load runtime data without loading ground-truth scenario labels."""
    context = {
        "access_events": _load_records(HR_DIR / "access_events.csv"),
        "profile_changes": _load_records(HR_DIR / "profile_changes.csv"),
        "employees": _load_records(HR_DIR / "employees.csv"),
        "injected_transactions": _load_records(HR_DIR / "injected_transactions.csv"),
    }
    # Scenario ground truth is represented by injected_transactions.csv. The
    # real transaction ledger is intentionally excluded here because the
    # current transaction rules perform full in-memory scans and this tool is
    # evaluating the 38 labeled synthetic scenarios.
    return context


def build_engine() -> RuleEngine:
    registry = RuleRegistry()
    registry.register(PrivilegeChangeRule())
    registry.register(CircularTransferRule())
    registry.register(TransactionSplittingRule())
    return RuleEngine(registry)


def _result_matches_account(result: RuleResult, account_id: str) -> bool:
    return account_id in {
        result.account_id,
        result.entity_id,
        result.customer_id,
    }


def _run_for_accounts(
    engine: RuleEngine,
    context: Mapping[str, Sequence[Mapping[str, str]]],
    configuration: Mapping[str, Mapping[str, object]],
    account_ids: Sequence[str],
) -> List[RuleResult]:
    """Run the existing engine for each scenario account and deduplicate results."""
    results: List[RuleResult] = []
    seen: Set[Tuple[str, str, Tuple[str, ...], Tuple[str, ...]]] = set()
    for account_id in account_ids:
        outcome = engine.run(context, configuration, account_id=account_id)
        for result in outcome.results:
            key = (
                result.rule_id,
                result.account_id or result.entity_id or "",
                tuple(result.transaction_ids),
                tuple(result.access_event_ids + result.profile_change_ids),
            )
            if key not in seen:
                seen.add(key)
                results.append(result)
    return results


def _signals(results: Iterable[RuleResult]) -> Set[str]:
    return {RULE_TO_SIGNAL[result.rule_id] for result in results if result.rule_id in RULE_TO_SIGNAL}


def _format_signal_results(expected: Set[str], actual: Set[str]) -> str:
    parts = []
    for signal in sorted(expected):
        parts.append(f"{signal}: {'MATCH' if signal in actual else 'MISS'}")
    for signal in sorted(actual - expected):
        parts.append(f"{signal}: UNEXPECTED")
    return "; ".join(parts) or "none"


def _scenario_row(
    scenario: Mapping[str, str],
    results: Sequence[RuleResult],
) -> Dict[str, object]:
    expected = set(_split_ids(scenario["expected_signals"]))
    testable = expected & set(SIGNAL_TO_RULE)
    not_testable = expected - set(SIGNAL_TO_RULE)
    actual = _signals(results)
    unexpected_legitimate = sorted(actual - expected) if scenario["scenario_type"] == "legitimate" else []
    notes = []
    if unexpected_legitimate:
        notes.append("observable rule trigger is not listed in expected_signals")
    if scenario["scenario_type"] not in ("suspicious", "legitimate"):
        notes.append("unexpected scenario_type")
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_type": scenario["scenario_type"],
        "account_ids": _split_ids(scenario["account_id"]),
        "expected_signals_testable": sorted(testable),
        "expected_signals_not_yet_testable": sorted(not_testable),
        "actually_detected_signals": sorted(actual),
        "signal_results": _format_signal_results(testable, actual),
        "unexpected_signal_on_legitimate": unexpected_legitimate,
        "notes": "; ".join(notes),
        "results": list(results),
    }


def _print_table(rows: Sequence[Mapping[str, object]]) -> None:
    columns = (
        "scenario_id", "scenario_type", "account_ids",
        "expected_signals_testable", "expected_signals_not_yet_testable",
        "actually_detected_signals", "signal_results",
        "unexpected_signal_on_legitimate", "notes",
    )
    print(" | ".join(columns))
    for row in rows:
        print(" | ".join(str(row[column]) for column in columns))


def _evidence_issues(
    rows: Sequence[Mapping[str, object]],
    access_events: Sequence[Mapping[str, str]],
    profile_changes: Sequence[Mapping[str, str]],
    injected_transactions: Sequence[Mapping[str, str]],
) -> Dict[str, List[object]]:
    event_ids = {row["event_id"] for row in access_events}
    change_ids = {row["change_id"] for row in profile_changes}
    transaction_ids = {row["transaction_id"] for row in injected_transactions}
    missing = []
    incorrect_entities = []
    incorrect_ids = []
    missing_explanations = []

    for row in rows:
        scenario = row["scenario"]
        account_ids = set(row["account_ids"])
        expected_events = set(_split_ids(scenario["related_event_ids"]))
        expected_changes = {
            change["change_id"]
            for change in profile_changes
            if change["customer_id"] in account_ids
            and change["changed_by_employee_id"] == scenario["employee_id"]
            and change["change_id"]
        }
        expected_transactions = set(_split_ids(scenario["related_transaction_ids"]))
        for result in row["results"]:
            evidence_ids = {evidence.record_id for evidence in result.evidence}
            if not result.explanation:
                missing_explanations.append((scenario["scenario_id"], result.rule_id))
            if not any(_result_matches_account(result, account_id) for account_id in account_ids):
                incorrect_entities.append((scenario["scenario_id"], result.rule_id, result.account_id, sorted(account_ids)))
            if result.rule_id == "INSIDER.PRIVILEGE_CHANGE":
                missing_ids = set(result.access_event_ids) - expected_events
                invalid_ids = set(result.access_event_ids) - event_ids
                invalid_changes = set(result.profile_change_ids) - change_ids
                unrelated_changes = set(result.profile_change_ids) - expected_changes
                if missing_ids or invalid_ids or invalid_changes or unrelated_changes:
                    missing.append((scenario["scenario_id"], result.rule_id, sorted(missing_ids)))
                    incorrect_ids.append((scenario["scenario_id"], sorted(invalid_ids | invalid_changes | unrelated_changes)))
            elif result.rule_id in ("AML.CIRCULAR_TRANSFER", "AML.TRANSACTION_SPLITTING"):
                # Splitting uses sliding windows, so each valid result may be
                # a subset of a scenario's related transactions. Validate the
                # result IDs rather than requiring every window to contain all
                # scenario transactions.
                missing_ids = set(result.transaction_ids) - expected_transactions
                invalid_transactions = set(result.transaction_ids) - transaction_ids
                if missing_ids or invalid_transactions:
                    missing.append((scenario["scenario_id"], result.rule_id, sorted(missing_ids)))
                    incorrect_ids.append((scenario["scenario_id"], sorted(invalid_transactions)))
            required_result_ids = set(result.transaction_ids + result.access_event_ids + result.profile_change_ids)
            if not required_result_ids.issubset(evidence_ids):
                incorrect_ids.append((scenario["scenario_id"], "result IDs absent from evidence", sorted(required_result_ids - evidence_ids)))

    return {
        "missing_evidence": missing,
        "incorrect_entity_ids": incorrect_entities,
        "incorrect_event_transaction_ids": incorrect_ids,
        "missing_explanations": missing_explanations,
    }


def validate() -> None:
    scenarios = _load_records(HR_DIR / "labeled_scenarios.csv")
    context = load_runtime_context()
    configuration = load_rule_configuration()
    engine = build_engine()

    rows = []
    for scenario in scenarios:
        account_ids = _split_ids(scenario["account_id"])
        results = _run_for_accounts(engine, context, configuration, account_ids)
        row = _scenario_row(scenario, results)
        row["scenario"] = scenario
        rows.append(row)

    full_outcome = engine.run(context, configuration)
    all_results = full_outcome.results

    scenario_account_map = {
        scenario["scenario_id"]: set(_split_ids(scenario["account_id"]))
        for scenario in scenarios
    }

    print("SECTION 1\nFull per-scenario validation table")
    _print_table(rows)

    print("\nSECTION 2\nNot-yet-testable signals")
    not_testable = sorted({signal for row in rows for signal in row["expected_signals_not_yet_testable"]})
    print(not_testable or "none")

    circular_results = [result for result in all_results if result.rule_id == "AML.CIRCULAR_TRANSFER"]
    print("\nSECTION 3\nCircular-transfer special validation")
    print("number of circular-transfer results:", len(circular_results))
    if circular_results:
        circular = circular_results[0]
        print("originating account:", circular.account_id)
        print("accounts in cycle:", circular.metrics.get("participating_account_ids"))
        print("transaction IDs:", circular.transaction_ids)
        print("path:", circular.metrics.get("path"))
        expected_path = "800085BF0 -> 800093C80 -> 8001C3570 -> 800085BF0"
        print("Detected cycle matches S19:", "YES" if circular.metrics.get("path") == expected_path else "NO")
    else:
        print("Detected cycle matches S19: NO")

    splitting_results = [result for result in all_results if result.rule_id == "AML.TRANSACTION_SPLITTING"]
    relevant_accounts = set()
    relevant_scenarios = []
    for scenario in scenarios:
        if "transaction_splitting" in _split_ids(scenario["expected_signals"]):
            relevant_scenarios.append(scenario["scenario_id"])
            relevant_accounts.update(_split_ids(scenario["account_id"]))
    scenario_splitting = [result for result in splitting_results if result.account_id in relevant_accounts]
    background_splitting = [result for result in splitting_results if result.account_id not in relevant_accounts]
    print("\nSECTION 4\nTransaction-splitting breakdown")
    print("total transaction_splitting results:", len(splitting_results))
    print("scenario-related results:", len(scenario_splitting))
    print("scenario IDs considered:", relevant_scenarios)
    print("scenario-related accounts:", sorted(relevant_accounts))
    print("background-noise results:", len(background_splitting))
    print("background-noise accounts:", sorted({result.account_id for result in background_splitting}))

    suspicious_rows = [row for row in rows if row["scenario_type"] == "suspicious"]
    legitimate_rows = [row for row in rows if row["scenario_type"] == "legitimate"]
    expected_testable = sum(len(set(row["expected_signals_testable"])) for row in suspicious_rows)
    matched_testable = sum(
        sum(signal in _signals(row["results"]) for signal in row["expected_signals_testable"])
        for row in suspicious_rows
    )
    unexpected_legitimate = [
        (row["scenario_id"], signal)
        for row in legitimate_rows
        for signal in row["unexpected_signal_on_legitimate"]
    ]
    legitimate_with_unexpected = {
        scenario_id for scenario_id, _ in unexpected_legitimate
    }
    print("\nSECTION 5\nSummary metrics")
    print("suspicious-scenario true positive rate:", f"{matched_testable}/{expected_testable} = {matched_testable / expected_testable:.3f}" if expected_testable else "N/A")
    print("legitimate-scenario false positive rate:", f"{len(legitimate_with_unexpected)}/{len(legitimate_rows)} = {len(legitimate_with_unexpected) / len(legitimate_rows):.3f}")
    print("legitimate signal trigger count:", f"{len(unexpected_legitimate)}/{len(legitimate_rows)}")
    print("background-noise detections:", len([result for result in all_results if not any(result.account_id in accounts for accounts in scenario_account_map.values())]))

    issues = _evidence_issues(rows, context["access_events"], context["profile_changes"], context["injected_transactions"])
    print("\nSECTION 6\nEvidence/explainability validation")
    for name, values in issues.items():
        print(f"{name}:", values or "none")

    print("\nSECTION 7\nIssues requiring rule adjustment")
    print("No automatic rule changes made.")
    print("Known evaluation limitation: S03 lists CHG_090003 conceptually, but its live timestamp is five minutes after EVT_090003, so exact pairing does not occur.")
    print("Label mismatches are reported as observed rule triggers, not treated as malicious intent.")


if __name__ == "__main__":
    validate()