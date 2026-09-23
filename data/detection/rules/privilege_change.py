"""Deterministic insider-threat privilege-change rule."""

from typing import Any, Dict, List, Mapping, Sequence

from ..base_rule import Rule
from ..config import load_rule_configuration
from ..models import Evidence, RuleResult


class PrivilegeChangeRule(Rule):
    """Detect qualifying administrative access changes and paired audit rows."""

    def __init__(self) -> None:
        super().__init__(
            rule_id="INSIDER.PRIVILEGE_CHANGE",
            rule_name="Privilege change",
            detection_category="insider-threat",
            description=(
                "Detects an administrative access or account-configuration "
                "change and preserves matching audit evidence."
            ),
        )

    def _evaluate(
        self,
        context: Mapping[str, Any],
        configuration: Mapping[str, Any],
    ) -> List[RuleResult]:
        rule_configuration = self._validated_configuration(configuration)
        if not rule_configuration["enabled"]:
            return []
        access_events = self._records(context.get("access_events"))
        profile_changes = self._records(context.get("profile_changes"))
        employees = self._employee_lookup(context.get("employees"))
        results: List[RuleResult] = []

        for event in access_events:
            if not self._has_required_fields(event, (
                "event_id",
                "employee_id",
                "action",
                "target_account_id",
                "old_value",
                "new_value",
                "timestamp",
            )):
                continue
            if not self._is_qualifying_event(
                event,
                rule_configuration["qualifying_administrative_categories"],
            ):
                continue

            employee_id = self._text(event.get("employee_id"))
            timestamp = self._text(event.get("timestamp"))
            event_id = self._text(event.get("event_id"))
            if not employee_id or not timestamp or not event_id:
                continue
            targets = self._split_targets(event.get("target_account_id"))
            employee = employees.get(employee_id, {})

            for account_id in targets:
                paired_changes = self._matching_profile_changes(
                    profile_changes,
                    timestamp,
                    account_id,
                    employee_id,
                    rule_configuration,
                )
                results.append(self._build_result(
                    event=event,
                    account_id=account_id,
                    employee=employee,
                    paired_changes=paired_changes,
                    event_id=event_id,
                    configuration=rule_configuration,
                ))

        return results

    def _build_result(
        self,
        event: Mapping[str, Any],
        account_id: str,
        employee: Mapping[str, Any],
        paired_changes: Sequence[Mapping[str, Any]],
        event_id: str,
        configuration: Mapping[str, Any],
    ) -> RuleResult:
        employee_id = self._text(event.get("employee_id"))
        timestamp = self._text(event.get("timestamp"))
        action = self._text(event.get("action"))
        old_value = self._text(event.get("old_value"))
        new_value = self._text(event.get("new_value"))
        profile_ids = [
            self._text(change.get("change_id"))
            for change in paired_changes
            if self._text(change.get("change_id"))
        ]

        evidence = [Evidence(
            source_dataset="synthetic_hr",
            record_type="access_event",
            record_id=event_id,
            role="triggering_access_event",
            details={
                "employee_id": employee_id,
                "target_account_id": account_id,
                "action": action,
                "old_value": old_value,
                "new_value": new_value,
                "timestamp": timestamp,
                "configuration": {
                    "qualifying_administrative_categories": configuration[
                        "qualifying_administrative_categories"
                    ],
                    "matching_timestamp": configuration["matching_timestamp"],
                    "require_matching_employee": configuration[
                        "require_matching_employee"
                    ],
                },
            },
        )]
        for change in paired_changes:
            change_id = self._text(change.get("change_id"))
            if not change_id:
                continue
            evidence.append(Evidence(
                source_dataset="synthetic_hr",
                record_type="profile_change",
                record_id=change_id,
                role="paired_profile_change",
                details={
                    "customer_id": self._text(change.get("customer_id")),
                    "field_changed": self._text(change.get("field_changed")),
                    "old_value": self._text(change.get("old_value")),
                    "new_value": self._text(change.get("new_value")),
                    "changed_by_employee_id": self._text(
                        change.get("changed_by_employee_id")
                    ),
                    "timestamp": self._text(change.get("timestamp")),
                },
            ))

        employee_name = self._text(employee.get("name"))
        employee_role = self._text(employee.get("role"))
        employee_description = employee_id
        if employee_name:
            employee_description = f"{employee_name} ({employee_id})"
        explanation = (
            f"Employee {employee_description} performed administrative action "
            f"'{action}' on account {account_id}: '{old_value}' -> '{new_value}'."
        )

        metrics: Dict[str, Any] = {
            "qualifying_event_count": 1,
            "paired_profile_change_count": len(profile_ids),
            "action": action,
            "old_value": old_value,
            "new_value": new_value,
        }
        if employee_role:
            metrics["employee_role"] = employee_role

        thresholds = {
            "minimum_qualifying_events": configuration[
                "minimum_qualifying_events"
            ],
            "paired_record_window": configuration["matching_timestamp"],
        }

        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            detection_category=self.detection_category,
            triggered=True,
            entity_type="Employee",
            entity_id=employee_id,
            account_id=account_id,
            employee_id=employee_id,
            access_event_ids=[event_id],
            profile_change_ids=profile_ids,
            explanation=explanation,
            metrics=metrics,
            thresholds=thresholds,
            detection_timestamp=timestamp,
            window_start=timestamp,
            window_end=timestamp,
            evidence=evidence,
        )

    def _is_qualifying_event(
        self,
        event: Mapping[str, Any],
        categories: Sequence[str],
    ) -> bool:
        searchable = " ".join(
            self._text(event.get(field_name)).lower()
            for field_name in ("action", "old_value", "new_value")
        )
        return any(term in searchable for term in categories)

    @classmethod
    def _validated_configuration(
        cls,
        configuration: Mapping[str, Any],
    ) -> Dict[str, Any]:
        default = load_rule_configuration()[cls().rule_id]
        merged = dict(default)
        merged.update(dict(configuration))

        if not isinstance(merged["enabled"], bool):
            raise ValueError("Privilege-change 'enabled' must be boolean")
        for key in (
            "qualifying_administrative_categories",
            "qualifying_profile_change_fields",
        ):
            values = merged[key]
            if not isinstance(values, list) or not values or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                raise ValueError(f"Privilege-change '{key}' must be a non-empty list of strings")
            merged[key] = [value.strip().lower() for value in values]
        if merged["matching_timestamp"] != "exact":
            raise ValueError(
                "Privilege-change 'matching_timestamp' must be 'exact'"
            )
        if not isinstance(merged["require_matching_employee"], bool):
            raise ValueError(
                "Privilege-change 'require_matching_employee' must be boolean"
            )
        if merged["minimum_qualifying_events"] != 1:
            raise ValueError(
                "Privilege-change 'minimum_qualifying_events' must be 1"
            )
        return merged

    @classmethod
    def _matching_profile_changes(
        cls,
        profile_changes: Sequence[Mapping[str, Any]],
        timestamp: str,
        account_id: str,
        employee_id: str,
        configuration: Mapping[str, Any],
    ) -> List[Mapping[str, Any]]:
        matching: List[Mapping[str, Any]] = []
        for change in profile_changes:
            if not cls._has_required_fields(change, (
                "change_id",
                "customer_id",
                "field_changed",
                "changed_by_employee_id",
                "timestamp",
            )):
                continue
            if cls._text(change.get("timestamp")) != timestamp:
                continue
            if cls._text(change.get("customer_id")) != account_id:
                continue
            if (
                configuration["require_matching_employee"]
                and cls._text(change.get("changed_by_employee_id")) != employee_id
            ):
                continue
            field_changed = cls._text(change.get("field_changed")).lower()
            if field_changed not in configuration["qualifying_profile_change_fields"]:
                continue
            if not cls._text(change.get("change_id")):
                continue
            matching.append(change)
        return matching

    @staticmethod
    def _employee_lookup(records: Any) -> Dict[str, Mapping[str, Any]]:
        lookup: Dict[str, Mapping[str, Any]] = {}
        for record in PrivilegeChangeRule._records(records):
            employee_id = PrivilegeChangeRule._text(record.get("employee_id"))
            if employee_id:
                lookup[employee_id] = record
        return lookup

    @staticmethod
    def _records(value: Any) -> List[Mapping[str, Any]]:
        if value is None:
            return []
        if isinstance(value, Mapping):
            return [value]
        if isinstance(value, (str, bytes)):
            return []
        try:
            return [record for record in value if isinstance(record, Mapping)]
        except TypeError:
            return []

    @staticmethod
    def _has_required_fields(
        record: Mapping[str, Any],
        fields: Sequence[str],
    ) -> bool:
        return all(field_name in record for field_name in fields)

    @staticmethod
    def _split_targets(value: Any) -> List[str]:
        raw_value = PrivilegeChangeRule._text(value)
        return [target.strip() for target in raw_value.split(";") if target.strip()]

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