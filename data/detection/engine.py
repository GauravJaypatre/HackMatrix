"""Unified orchestrator for deterministic AML and insider-threat rules."""

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import json
from typing import Any, Dict, List, Mapping, Optional

from .models import RuleResult
from .registry import RuleRegistry


@dataclass
class RuleFailure:
    """An observable failure from one rule execution."""

    rule_id: str
    rule_name: str
    error_type: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class EngineResult:
    """Collected results and failures from one engine execution."""

    results: List[RuleResult] = field(default_factory=list)
    failures: List[RuleFailure] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "results": [result.to_dict() for result in self.results],
            "failures": [failure.to_dict() for failure in self.failures],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


class RuleEngine:
    """Run registered rules through one deterministic execution path."""

    def __init__(self, registry: RuleRegistry) -> None:
        self.registry = registry

    def run(
        self,
        context: Mapping[str, Any],
        configuration: Optional[Mapping[str, Any]] = None,
        *,
        account_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        employee_id: Optional[str] = None,
    ) -> EngineResult:
        """Run all enabled rules against a full or scoped data context.

        Scope values are copied into the rule context under ``scope``. Results
        that do not match the requested scope are excluded from the outcome.
        Source context and configuration mappings are never modified.
        """
        if not isinstance(context, Mapping):
            raise TypeError("context must be a mapping")

        scope = {
            key: value
            for key, value in (
                ("account_id", account_id),
                ("entity_id", entity_id),
                ("employee_id", employee_id),
            )
            if value is not None
        }
        base_configuration = configuration or {}
        outcome = EngineResult()

        for rule in self.registry.get_enabled_rules():
            try:
                rule_context = deepcopy(dict(context))
                rule_context["scope"] = dict(scope)
                rule_configuration = self._configuration_for_rule(
                    base_configuration, rule.rule_id
                )
                if "enabled" in rule_configuration and not isinstance(
                    rule_configuration["enabled"], bool
                ):
                    raise ValueError("Rule configuration 'enabled' must be boolean")
                if rule_configuration.get("enabled", True) is False:
                    continue
                results = rule.evaluate(
                    rule_context,
                    deepcopy(dict(rule_configuration)),
                )
                outcome.results.extend(
                    result
                    for result in results
                    if self._matches_scope(result, scope)
                )
            except Exception as error:  # Continue with independent rules.
                outcome.failures.append(
                    RuleFailure(
                        rule_id=rule.rule_id,
                        rule_name=rule.rule_name,
                        error_type=type(error).__name__,
                        message=str(error),
                    )
                )

        return outcome

    @staticmethod
    def _configuration_for_rule(
        configuration: Mapping[str, Any], rule_id: str
    ) -> Mapping[str, Any]:
        configured = configuration.get(rule_id)
        if isinstance(configured, Mapping):
            return configured
        return configuration

    @staticmethod
    def _matches_scope(result: RuleResult, scope: Mapping[str, str]) -> bool:
        if not scope:
            return True

        if "account_id" in scope:
            account_values = {result.account_id}
            if result.entity_type == "Account":
                account_values.add(result.entity_id)
            if scope["account_id"] not in account_values:
                return False

        if "employee_id" in scope:
            employee_values = {result.employee_id}
            if result.entity_type == "Employee":
                employee_values.add(result.entity_id)
            if scope["employee_id"] not in employee_values:
                return False

        if "entity_id" in scope:
            entity_values = {
                result.entity_id,
                result.account_id,
                result.employee_id,
                result.customer_id,
            }
            if scope["entity_id"] not in entity_values:
                return False

        return True