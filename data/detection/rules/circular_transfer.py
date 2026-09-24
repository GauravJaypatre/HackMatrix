"""Deterministic AML circular-transfer rule."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ..base_rule import Rule
from ..config import load_rule_configuration
from ..models import Evidence, RuleResult


class CircularTransferRule(Rule):
    """Detect chronological directed transaction paths that return to origin."""

    _REQUIRED_FIELDS = (
        "transaction_id",
        "timestamp",
        "from_account",
        "to_account",
    )
    _TIMESTAMP_FORMATS = (
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    )

    def __init__(self) -> None:
        super().__init__(
            rule_id="AML.CIRCULAR_TRANSFER",
            rule_name="Circular transfer",
            detection_category="AML",
            description="Detects a closed directed transaction path returning to its origin.",
        )

    def _evaluate(
        self,
        context: Mapping[str, Any],
        configuration: Mapping[str, Any],
    ) -> List[RuleResult]:
        rule_configuration = self._validated_configuration(configuration)
        if not rule_configuration["enabled"]:
            return []

        transactions = self._transactions(context)
        cycles: Dict[Tuple[str, ...], List[Mapping[str, Any]]] = {}
        for transaction in transactions:
            for cycle in self._find_cycles_from(
                transaction,
                transactions,
                rule_configuration,
            ):
                key = self._canonical_cycle_key(cycle)
                cycles.setdefault(key, cycle)

        return [
            self._build_result(cycle, rule_configuration)
            for cycle in cycles.values()
        ]

    def _find_cycles_from(
        self,
        first: Mapping[str, Any],
        transactions: Sequence[Mapping[str, Any]],
        configuration: Mapping[str, Any],
    ) -> List[List[Mapping[str, Any]]]:
        origin = first["from_account"]
        start_time = first["parsed_timestamp"]
        deadline = start_time + timedelta(
            hours=configuration["time_window_hours"]
        )
        cycles: List[List[Mapping[str, Any]]] = []

        def walk(path: List[Mapping[str, Any]], visited: set) -> None:
            current = path[-1]["to_account"]
            if current == origin:
                if len(path) >= configuration["minimum_transactions"]:
                    cycles.append(path.copy())
                return

            if current in visited:
                return

            for candidate in transactions:
                if candidate["from_account"] != current:
                    continue
                if candidate["transaction_id"] in {
                    item["transaction_id"] for item in path
                }:
                    continue
                if candidate["parsed_timestamp"] < path[-1]["parsed_timestamp"]:
                    continue
                if candidate["parsed_timestamp"] > deadline:
                    continue
                if candidate["to_account"] in visited and candidate["to_account"] != origin:
                    continue
                walk(path + [candidate], visited | {current})

        walk([first], {origin})
        return cycles

    def _build_result(
        self,
        cycle: Sequence[Mapping[str, Any]],
        configuration: Mapping[str, Any],
    ) -> RuleResult:
        origin = cycle[0]["from_account"]
        path_accounts = [cycle[0]["from_account"]]
        path_accounts.extend(item["to_account"] for item in cycle)
        transaction_ids = [item["transaction_id"] for item in cycle]
        timestamps = [item["timestamp"] for item in cycle]
        path = " -> ".join(path_accounts)
        window_hours = configuration["time_window_hours"]
        explanation = (
            f"Rule {self.rule_id} ({self.rule_name}) triggered because transactions "
            f"formed a closed path returning to the originating account within the "
            f"configured {window_hours}-hour window: {path}."
        )
        evidence = [
            Evidence(
                source_dataset=item["source_dataset"],
                record_type=item["record_type"],
                record_id=item["transaction_id"],
                role="circular_path_transaction",
                details={
                    "from_account": item["from_account"],
                    "to_account": item["to_account"],
                    "timestamp": item["timestamp"],
                    "path": path,
                    "time_window_hours": window_hours,
                },
            )
            for item in cycle
        ]
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            detection_category=self.detection_category,
            triggered=True,
            entity_type="Account",
            entity_id=origin,
            account_id=origin,
            transaction_ids=transaction_ids,
            explanation=explanation,
            metrics={
                "transaction_count": len(transaction_ids),
                "participating_account_ids": path_accounts[:-1],
                "path": path,
            },
            thresholds={
                "time_window_hours": window_hours,
                "minimum_transactions": configuration["minimum_transactions"],
            },
            detection_timestamp=timestamps[-1],
            window_start=timestamps[0],
            window_end=timestamps[-1],
            evidence=evidence,
        )

    @classmethod
    def _transactions(cls, context: Mapping[str, Any]) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        sources = (
            ("injected_transactions", "synthetic_hr", "injected_transaction"),
            ("real_transactions", "entities", "real_transaction"),
            ("in_scope_real_transactions", "entities", "real_transaction"),
        )
        seen_ids = set()
        for key, source_dataset, record_type in sources:
            value = context.get(key)
            if isinstance(value, Mapping) or isinstance(value, (str, bytes)):
                continue
            try:
                rows = value or []
                for row in rows:
                    if not isinstance(row, Mapping):
                        continue
                    if not cls._has_required_fields(row):
                        continue
                    transaction_id = cls._text(row.get("transaction_id"))
                    from_account = cls._text(row.get("from_account"))
                    to_account = cls._text(row.get("to_account"))
                    timestamp = cls._text(row.get("timestamp"))
                    parsed_timestamp = cls._parse_timestamp(timestamp)
                    if not transaction_id or not from_account or not to_account:
                        continue
                    if parsed_timestamp is None or transaction_id in seen_ids:
                        continue
                    seen_ids.add(transaction_id)
                    records.append({
                        "transaction_id": transaction_id,
                        "timestamp": timestamp,
                        "parsed_timestamp": parsed_timestamp,
                        "from_account": from_account,
                        "to_account": to_account,
                        "source_dataset": source_dataset,
                        "record_type": record_type,
                    })
            except TypeError:
                continue
        records.sort(key=lambda item: (item["parsed_timestamp"], item["transaction_id"]))
        return records

    @classmethod
    def _canonical_cycle_key(cls, cycle: Sequence[Mapping[str, Any]]) -> Tuple[str, ...]:
        transaction_ids = [item["transaction_id"] for item in cycle]
        rotations = [
            tuple(transaction_ids[index:] + transaction_ids[:index])
            for index in range(len(transaction_ids))
        ]
        return min(rotations)

    @classmethod
    def _validated_configuration(
        cls,
        configuration: Mapping[str, Any],
    ) -> Dict[str, Any]:
        default = load_rule_configuration()[cls().rule_id]
        merged = dict(default)
        merged.update(dict(configuration))
        if not isinstance(merged["enabled"], bool):
            raise ValueError("Circular-transfer 'enabled' must be boolean")
        if not isinstance(merged["time_window_hours"], (int, float)) or merged["time_window_hours"] <= 0:
            raise ValueError("Circular-transfer 'time_window_hours' must be positive")
        if not isinstance(merged["minimum_transactions"], int) or merged["minimum_transactions"] < 3:
            raise ValueError("Circular-transfer 'minimum_transactions' must be an integer of at least 3")
        return merged

    @classmethod
    def _parse_timestamp(cls, value: str):
        for timestamp_format in cls._TIMESTAMP_FORMATS:
            try:
                return datetime.strptime(value, timestamp_format)
            except ValueError:
                continue
        return None

    @staticmethod
    def _has_required_fields(record: Mapping[str, Any]) -> bool:
        return all(field in record for field in CircularTransferRule._REQUIRED_FIELDS)

    @staticmethod
    def _text(value: Any) -> str:
        if value is None:
            return ""
        try:
            if value != value:
                return ""
        except Exception:
            pass
        return str(value).strip()