"""Common interface for deterministic AML and insider-threat rules."""

from abc import ABC, abstractmethod
from typing import Any, List, Mapping, Optional

from .models import RuleResult


class Rule(ABC):
    """Base class for one deterministic, read-only detection rule.

    A rule receives only the context and configuration supplied by the caller.
    It must not mutate either input, use ML, or calculate a global risk score.
    """

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        detection_category: str,
        description: str,
    ) -> None:
        for field_name, value in (
            ("rule_id", rule_id),
            ("rule_name", rule_name),
            ("detection_category", detection_category),
            ("description", description),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        self.rule_id = rule_id
        self.rule_name = rule_name
        self.detection_category = detection_category
        self.description = description

    def evaluate(
        self,
        context: Mapping[str, Any],
        configuration: Optional[Mapping[str, Any]] = None,
    ) -> List[RuleResult]:
        """Evaluate this rule and return standardized results.

        ``context`` may contain transaction data or employee/access/profile
        data. The concrete rule decides which context entries it needs.
        """
        results = self._evaluate(context, configuration or {})
        if not isinstance(results, list):
            raise TypeError("A rule must return a list of RuleResult objects")

        for result in results:
            if not isinstance(result, RuleResult):
                raise TypeError("A rule result must be a RuleResult instance")
            if result.rule_id != self.rule_id:
                raise ValueError("RuleResult.rule_id does not match the rule")
            if result.rule_name != self.rule_name:
                raise ValueError("RuleResult.rule_name does not match the rule")
            if result.detection_category != self.detection_category:
                raise ValueError(
                    "RuleResult.detection_category does not match the rule"
                )

        return results

    @abstractmethod
    def _evaluate(
        self,
        context: Mapping[str, Any],
        configuration: Mapping[str, Any],
    ) -> List[RuleResult]:
        """Implement the rule-specific deterministic evaluation."""
        raise NotImplementedError