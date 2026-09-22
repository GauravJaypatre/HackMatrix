"""
validate_joins.py — Cross-Dataset Join Validation for FIN04
============================================================
Validates that the synthetic HR/Access layer correctly joins against
the IBM AML transaction data, and reports row counts for all produced files.

Usage:
    python validate_joins.py

Run from the /data directory or the project root.
"""

import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent

# All expected files
EXPECTED_FILES = {
    "IBM AML": {
        "transactions_clean.csv": DATA_DIR / "ibm_aml" / "transactions_clean.csv",
        "HI-Small_Trans.csv (raw)": DATA_DIR / "ibm_aml" / "HI-Small_Trans.csv",
    },
    "AMLSim": {
        "accounts.csv": DATA_DIR / "amlsim" / "accounts.csv",
        "transactions.csv": DATA_DIR / "amlsim" / "transactions.csv",
        "alert_patterns.csv": DATA_DIR / "amlsim" / "alert_patterns.csv",
        "alert_members.csv": DATA_DIR / "amlsim" / "alert_members.csv",
    },
    "Synthetic HR": {
        "employees.csv": DATA_DIR / "synthetic_hr" / "employees.csv",
        "access_events.csv": DATA_DIR / "synthetic_hr" / "access_events.csv",
        "profile_changes.csv": DATA_DIR / "synthetic_hr" / "profile_changes.csv",
        "employee_customer_map.csv": DATA_DIR / "synthetic_hr" / "employee_customer_map.csv",
        "labeled_scenarios.csv": DATA_DIR / "synthetic_hr" / "labeled_scenarios.csv",
        "injected_transactions.csv": DATA_DIR / "synthetic_hr" / "injected_transactions.csv",
    },
}


def check_files():
    """Check all expected files exist and report row counts."""
    print("=" * 70)
    print("FILE INVENTORY & ROW COUNTS")
    print("=" * 70)
    print()

    all_ok = True
    for group, files in EXPECTED_FILES.items():
        print(f"  {group}:")
        for name, path in files.items():
            if path.exists():
                try:
                    df = pd.read_csv(path, low_memory=False)
                    print(f"    [OK]  {name:40s}  {len(df):>8,} rows  x {len(df.columns):>3} cols")
                except Exception as e:
                    print(f"    [ERR] {name:40s}  Error reading: {e}")
                    all_ok = False
            else:
                print(f"    [MISSING] {name}")
                all_ok = False
        print()

    return all_ok


def validate_joins():
    """Validate join between access_events and IBM AML transactions."""
    print("=" * 70)
    print("JOIN VALIDATION")
    print("=" * 70)
    print()

    # Load IBM AML clean data
    ibm_path = DATA_DIR / "ibm_aml" / "transactions_clean.csv"
    if not ibm_path.exists():
        print("  SKIP: IBM AML transactions_clean.csv not found")
        return False

    ibm_df = pd.read_csv(ibm_path, low_memory=False)

    # Gather all account IDs from IBM AML (try common column names)
    ibm_account_ids = set()
    for col in ibm_df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in ["account", "from", "to", "sender", "receiver", "id"]):
            if ibm_df[col].dtype == "object" or "int" in str(ibm_df[col].dtype):
                ibm_account_ids.update(ibm_df[col].dropna().astype(str).unique())

    print(f"  IBM AML unique account-like IDs: {len(ibm_account_ids):,}")
    print()

    # ─── Join 1: access_events.target_account_id -> IBM AML accounts ─────
    acc_path = DATA_DIR / "synthetic_hr" / "access_events.csv"
    if acc_path.exists():
        acc_df = pd.read_csv(acc_path, low_memory=False)
        acc_ids = set(acc_df["target_account_id"].dropna().astype(str).unique())
        matched = acc_ids & ibm_account_ids
        match_rate = len(matched) / len(acc_ids) * 100 if acc_ids else 0

        print(f"  Join: access_events.target_account_id <-> IBM AML accounts")
        print(f"    Unique IDs in access_events:  {len(acc_ids):,}")
        print(f"    Matched with IBM AML:         {len(matched):,}")
        print(f"    Match rate:                   {match_rate:.1f}%")

        # Row-level match count
        acc_df["_matched"] = acc_df["target_account_id"].astype(str).isin(ibm_account_ids)
        row_matches = acc_df["_matched"].sum()
        print(f"    Rows with matched account:    {row_matches:,} / {len(acc_df):,} ({row_matches/len(acc_df)*100:.1f}%)")
        print()

        if match_rate < 50:
            print("  WARNING: Match rate below 50%! Check ID generation in generate.py")
            return False
    else:
        print("  SKIP: access_events.csv not found")

    # ─── Join 2: profile_changes.customer_id -> IBM AML accounts ─────────
    prof_path = DATA_DIR / "synthetic_hr" / "profile_changes.csv"
    if prof_path.exists():
        prof_df = pd.read_csv(prof_path, low_memory=False)
        prof_ids = set(prof_df["customer_id"].dropna().astype(str).unique())
        matched = prof_ids & ibm_account_ids
        match_rate = len(matched) / len(prof_ids) * 100 if prof_ids else 0

        print(f"  Join: profile_changes.customer_id <-> IBM AML accounts")
        print(f"    Unique IDs in profile_changes: {len(prof_ids):,}")
        print(f"    Matched with IBM AML:          {len(matched):,}")
        print(f"    Match rate:                    {match_rate:.1f}%")
        print()

    # ─── Join 3: employee_customer_map.customer_id -> IBM AML accounts ───
    map_path = DATA_DIR / "synthetic_hr" / "employee_customer_map.csv"
    if map_path.exists():
        map_df = pd.read_csv(map_path, low_memory=False)
        map_ids = set(map_df["customer_id"].dropna().astype(str).unique())
        matched = map_ids & ibm_account_ids
        match_rate = len(matched) / len(map_ids) * 100 if map_ids else 0

        print(f"  Join: employee_customer_map.customer_id <-> IBM AML accounts")
        print(f"    Unique IDs in map:             {len(map_ids):,}")
        print(f"    Matched with IBM AML:          {len(matched):,}")
        print(f"    Match rate:                    {match_rate:.1f}%")
        print()

    # ─── Scenario validation ─────────────────────────────────────────────
    sc_path = DATA_DIR / "synthetic_hr" / "labeled_scenarios.csv"
    if sc_path.exists():
        sc_df = pd.read_csv(sc_path, low_memory=False)
        print(f"  Labeled scenarios:")
        print(f"    Total:       {len(sc_df)}")
        print(f"    Suspicious:  {(sc_df['scenario_type'] == 'suspicious').sum()}")
        print(f"    Legitimate:  {(sc_df['scenario_type'] == 'legitimate').sum()}")

        # Check scenario account IDs match IBM AML
        sc_acct_ids = set()
        for _, row in sc_df.iterrows():
            ids = str(row["account_id"]).split(";")
            sc_acct_ids.update(ids)
        sc_matched = sc_acct_ids & ibm_account_ids
        print(f"    Scenario accounts in IBM AML: {len(sc_matched)}/{len(sc_acct_ids)}")
        print()

    return True


def validate_scenario_integrity():
    """Validate temporal ordering and ID resolution for scenarios."""
    print("=" * 70)
    print("SCENARIO INTEGRITY CHECKS")
    print("=" * 70)
    print()

    sc_path = DATA_DIR / "synthetic_hr" / "labeled_scenarios.csv"
    acc_path = DATA_DIR / "synthetic_hr" / "access_events.csv"
    inj_path = DATA_DIR / "synthetic_hr" / "injected_transactions.csv"

    for p in [sc_path, acc_path, inj_path]:
        if not p.exists():
            print(f"  SKIP: {p.name} not found")
            return False

    sc_df = pd.read_csv(sc_path, low_memory=False)
    acc_df = pd.read_csv(acc_path, low_memory=False)
    inj_df = pd.read_csv(inj_path, low_memory=False)

    # Parse timestamps
    acc_df["ts"] = pd.to_datetime(acc_df["timestamp"], errors="coerce")
    inj_df["ts"] = pd.to_datetime(inj_df["timestamp"], format="%Y/%m/%d %H:%M", errors="coerce")

    # Build lookup: injected transaction_id -> row
    inj_ids = set(inj_df["transaction_id"].dropna().astype(str).unique())

    pass_count = 0
    fail_count = 0
    failures = []

    for _, row in sc_df.iterrows():
        sid = row["scenario_id"]
        stype = row["scenario_type"]
        htc = row.get("has_transactional_consequence", True)
        related_ids_raw = str(row.get("related_transaction_ids", ""))
        related_evt_raw = str(row.get("related_event_ids", ""))

        # --- Check 1: has_transactional_consequence consistency ---
        if htc is False or str(htc).lower() == "false":
            if related_ids_raw and related_ids_raw not in ("", "nan", "NaN"):
                failures.append(f"{sid}: has_transactional_consequence=False but related_transaction_ids is not empty")
                fail_count += 1
                continue
            # No-txn scenario: valid as-is
            pass_count += 1
            continue

        # --- Check 2: ID resolution ---
        if not related_ids_raw or related_ids_raw in ("", "nan", "NaN"):
            failures.append(f"{sid}: has_transactional_consequence=True but related_transaction_ids is empty")
            fail_count += 1
            continue

        txn_ids = [t.strip() for t in related_ids_raw.split(",")]
        unresolved = [t for t in txn_ids if t not in inj_ids]
        if unresolved:
            failures.append(f"{sid}: {len(unresolved)} unresolved transaction IDs: {unresolved[:3]}...")
            fail_count += 1
            continue

        # --- Check 3: Temporal ordering (suspicious only) ---
        if stype == "suspicious":
            # Get access event timestamps for this scenario
            evt_ids = [e.strip() for e in related_evt_raw.split(";") if e.strip()]
            scenario_evts = acc_df[
                (acc_df["scenario_id"] == sid) | (acc_df["event_id"].isin(evt_ids))
            ]
            if scenario_evts.empty:
                failures.append(f"{sid}: No access events found")
                fail_count += 1
                continue

            latest_access = scenario_evts["ts"].max()

            # Get injected transaction timestamps
            scenario_txns = inj_df[inj_df["transaction_id"].isin(txn_ids)]
            if scenario_txns.empty:
                failures.append(f"{sid}: No matching injected transactions found")
                fail_count += 1
                continue

            earliest_txn = scenario_txns["ts"].min()

            if latest_access >= earliest_txn:
                failures.append(
                    f"{sid}: TEMPORAL VIOLATION - access event ({latest_access}) "
                    f"is NOT before earliest transaction ({earliest_txn})"
                )
                fail_count += 1
                continue

        pass_count += 1

    # Report
    total = pass_count + fail_count
    print(f"  Scenarios checked: {total}")
    print(f"  PASSED: {pass_count}")
    print(f"  FAILED: {fail_count}")

    if failures:
        print()
        for f in failures:
            print(f"  [FAIL] {f}")
    print()

    # Additional stats
    htc_true = sc_df[sc_df["has_transactional_consequence"] == True].shape[0]
    htc_false = sc_df[sc_df["has_transactional_consequence"] == False].shape[0]
    print(f"  has_transactional_consequence=True:  {htc_true}")
    print(f"  has_transactional_consequence=False: {htc_false}")
    print(f"  Injected transactions total:         {len(inj_df)}")
    print(f"  Unique scenario_ids in injected:     {inj_df['scenario_id'].nunique()}")
    print()

    return fail_count == 0


def main():
    print()
    files_ok = check_files()
    print()
    joins_ok = validate_joins()
    print()
    scenario_ok = validate_scenario_integrity()

    print()
    print("=" * 70)
    if files_ok and joins_ok and scenario_ok:
        print("VALIDATION PASSED - All files present, joins verified, scenarios validated")
    elif not files_ok:
        print("VALIDATION INCOMPLETE - Some files missing (see above)")
    elif not scenario_ok:
        print("VALIDATION FAILED - Scenario integrity issues (see above)")
    else:
        print("VALIDATION FAILED - Join issues detected (see above)")
    print("=" * 70)


if __name__ == "__main__":
    main()
