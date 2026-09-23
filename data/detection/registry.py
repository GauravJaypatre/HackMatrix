"""Registry for enabled deterministic detection rules."""

from typing import Dict, List

from .base_rule import Rule


class RuleRegistry:
    """Store registered rules and control which rules are enabled."""

    def __init__(self) -> None:
        self._rules: Dict[str, Rule] = {}
        self._enabled: Dict[str, bool] = {}

    def register(self, rule: Rule, enabled: bool = True) -> None:
        """Register a rule, optionally disabled until explicitly enabled."""
        if not isinstance(rule, Rule):
            raise TypeError("Only Rule instances can be registered")
        if rule.rule_id in self._rules:
            raise ValueError(f"Rule already registered: {rule.rule_id}")
        self._rules[rule.rule_id] = rule
        self._enabled[rule.rule_id] = enabled

    def enable(self, rule_id: str) -> None:
        """Enable a registered rule."""
        self._require_rule(rule_id)
        self._enabled[rule_id] = True

    def disable(self, rule_id: str) -> None:
        """Disable a registered rule without removing it."""
        self._require_rule(rule_id)
        self._enabled[rule_id] = False

    def get_enabled_rules(self) -> List[Rule]:
        """Return enabled rules in registration order."""
        return [
            rule
            for rule_id, rule in self._rules.items()
            if self._enabled[rule_id]
        ]

    def _require_rule(self, rule_id: str) -> None:
        if rule_id not in self._rules:
            raise KeyError(f"Rule is not registered: {rule_id}")