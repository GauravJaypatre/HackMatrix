"""Deterministic AML transaction-splitting rule."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ..base_rule import Rule
from ..config import load_rule_configuration
from ..models import Evidence, RuleResult


class TransactionSplittingRule(Rule):
    """Detect multiple outgoing transactions with at least one sub-boundary amount."""

    _REQUIRED_FIELDS = (
        "transaction_id",
        "timestamp",
        "from_account",
        "to_account",
        "amount_paid",
        "payment_format",
    )
    _TIMESTAMP_FORMATS = (
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    )

    def __init__(self) -> None:
        super().__init__(
            rule_id="AML.TRANSACTION_SPLITTING",
            rule_name="Transaction splitting",
            detection_category="AML",
            description="Detects grouped outgoing transactions with a sub-boundary amount.",
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
        grouped: Dict[Tuple[str, Tuple[str, ...]], List[Mapping[str, Any]]] = {}
        by_sender: Dict[str, List[Mapping[str, Any]]] = {}
        for transaction in transactions:
            by_sender.setdefault(transaction["from_account"], []).append(transaction)

        for sender_transactions in by_sender.values():
            for start_index, first in enumerate(sender_transactions):
                deadline = first["parsed_timestamp"] + timedelta(
                    hours=rule_configuration["time_window_hours"]
                )
                group = [
                    transaction
                    for transaction in sender_transactions[start_index:]
                    if transaction["parsed_timestamp"] <= deadline
                ]
                if len(group) < rule_configuration["minimum_outgoing_transactions"]:
                    continue
                if not any(
                    transaction["amount_paid"] < rule_configuration["below_reporting_boundary"]
                    for transaction in group
                ):
                    continue
                key = (group[0]["from_account"], tuple(
                    transaction["transaction_id"] for transaction in group
                ))
                grouped.setdefault(key, group)

        return [
            self._build_result(group, rule_configuration)
            for group in grouped.values()
        ]

    def _build_result(
        self,
        group: Sequence[Mapping[str, Any]],
        configuration: Mapping[str, Any],
    ) -> RuleResult:
        sender = group[0]["from_account"]
        transaction_ids = [item["transaction_id"] for item in group]
        timestamps = [item["timestamp"] for item in group]
        boundary = configuration["below_reporting_boundary"]
        window_hours = configuration["time_window_hours"]
        explanation = (
            f"Rule {self.rule_id} ({self.rule_name}) triggered because account "
            f"{sender} generated {len(group)} outgoing transactions within the "
            f"configured {window_hours}-hour window, including one or more "
            f"transactions below the configured ${boundary:,.2f} reporting boundary."
        )
        evidence = [
            Evidence(
                source_dataset=item["source_dataset"],
                record_type=item["record_type"],
                record_id=item["transaction_id"],
                role="transaction_splitting_group_member",
                details={
                    "from_account": item["from_account"],
                    "to_account": item["to_account"],
                    "timestamp": item["timestamp"],
                    "amount_paid": item["amount_paid"],
                    "payment_format": item["payment_format"],
                    "time_window_hours": window_hours,
                    "minimum_outgoing_transactions": configuration[
                        "minimum_outgoing_transactions"
                    ],
                    "below_reporting_boundary": boundary,
                },
            )
            for item in group
        ]
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            detection_category=self.detection_category,
            triggered=True,
            entity_type="Account",
            entity_id=sender,
            account_id=sender,
            transaction_ids=transaction_ids,
            explanation=explanation,
            metrics={
                "outgoing_transaction_count": len(group),
                "below_boundary_transaction_ids": [
                    item["transaction_id"]
                    for item in group
                    if item["amount_paid"] < boundary
                ],
                "amounts_paid": [item["amount_paid"] for item in group],
                "payment_formats": [item["payment_format"] for item in group],
            },
            thresholds={
                "time_window_hours": window_hours,
                "minimum_outgoing_transactions": configuration[
                    "minimum_outgoing_transactions"
                ],
                "below_reporting_boundary": boundary,
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
                    if not isinstance(row, Mapping) or not cls._has_required_fields(row):
                        continue
                    transaction_id = cls._text(row.get("transaction_id"))
                    timestamp = cls._text(row.get("timestamp"))
                    from_account = cls._text(row.get("from_account"))
                    to_account = cls._text(row.get("to_account"))
                    payment_format = cls._text(row.get("payment_format"))
                    parsed_timestamp = cls._parse_timestamp(timestamp)
                    try:
                        amount_paid = float(row.get("amount_paid"))
                    except (TypeError, ValueError):
                        continue
                    if (
                        not transaction_id
                        or not timestamp
                        or not from_account
                        or not to_account
                        or not payment_format
                        or parsed_timestamp is None
                        or transaction_id in seen_ids
                    ):
                        continue
                    seen_ids.add(transaction_id)
                    records.append({
                        "transaction_id": transaction_id,
                        "timestamp": timestamp,
                        "parsed_timestamp": parsed_timestamp,
                        "from_account": from_account,
                        "to_account": to_account,
                        "amount_paid": amount_paid,
                        "payment_format": payment_format,
                        "source_dataset": source_dataset,
                        "record_type": record_type,
                    })
            except TypeError:
                continue
        records.sort(key=lambda item: (
            item["from_account"], item["parsed_timestamp"], item["transaction_id"]
        ))
        return records

    @classmethod
    def _validated_configuration(
        cls,
        configuration: Mapping[str, Any],
    ) -> Dict[str, Any]:
        default = load_rule_configuration()[cls().rule_id]
        merged = dict(default)
        merged.update(dict(configuration))
        if not isinstance(merged["enabled"], bool):
            raise ValueError("Transaction-splitting 'enabled' must be boolean")
        if not isinstance(merged["time_window_hours"], (int, float)) or merged["time_window_hours"] <= 0:
            raise ValueError("Transaction-splitting 'time_window_hours' must be positive")
        if not isinstance(merged["minimum_outgoing_transactions"], int) or merged["minimum_outgoing_transactions"] < 3:
            raise ValueError("Transaction-splitting 'minimum_outgoing_transactions' must be at least 3")
        if not isinstance(merged["below_reporting_boundary"], (int, float)) or merged["below_reporting_boundary"] <= 0:
            raise ValueError("Transaction-splitting 'below_reporting_boundary' must be positive")
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
        return all(field in record for field in TransactionSplittingRule._REQUIRED_FIELDS)

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