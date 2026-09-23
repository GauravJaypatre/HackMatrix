"""Unit tests for the common deterministic rule interface."""

from copy import deepcopy
import unittest

from data.detection.base_rule import Rule
from data.detection.models import Evidence, RuleResult


class DummyRule(Rule):
    """Minimal test-only rule; it is not a production detector."""

    def __init__(self):
        super().__init__(
            rule_id="TEST.DUMMY",
            rule_name="Dummy rule",
            detection_category="test",
            description="Returns one result for interface testing.",
        )

    def _evaluate(self, context, configuration):
        return [
            RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                detection_category=self.detection_category,
                triggered=bool(context["triggered"]),
                account_id=context.get("account_id"),
                employee_id=context.get("employee_id"),
                transaction_ids=list(context.get("transaction_ids", [])),
                access_event_ids=list(context.get("access_event_ids", [])),
                explanation=self.description,
                thresholds=dict(configuration),
                evidence=list(context.get("evidence", [])),
            )
        ]


class BaseRuleTests(unittest.TestCase):
    def test_rule_metadata_and_standard_result(self):
        rule = DummyRule()

        result = rule.evaluate({
            "triggered": True,
            "account_id": "800085BF0",
            "transaction_ids": ["SYN_S19_001"],
        }, {"minimum_transaction_count": 3})[0]

        self.assertEqual(rule.rule_id, "TEST.DUMMY")
        self.assertEqual(rule.rule_name, "Dummy rule")
        self.assertEqual(rule.detection_category, "test")
        self.assertTrue(result.triggered)
        self.assertEqual(result.transaction_ids, ["SYN_S19_001"])
        self.assertEqual(result.thresholds["minimum_transaction_count"], 3)

    def test_rule_accepts_employee_access_and_profile_evidence(self):
        rule = DummyRule()
        evidence = [
            Evidence("synthetic_hr", "access_event", "EVT_090040", "access"),
            Evidence("synthetic_hr", "profile_change", "CHG_000206", "profile"),
        ]

        result = rule.evaluate({
            "triggered": True,
            "employee_id": "EMP_0047",
            "access_event_ids": ["EVT_090040"],
            "evidence": evidence,
        })[0]

        self.assertEqual(result.employee_id, "EMP_0047")
        self.assertEqual(result.access_event_ids, ["EVT_090040"])
        self.assertEqual([item.record_id for item in result.evidence], [
            "EVT_090040",
            "CHG_000206",
        ])

    def test_evaluation_is_deterministic_and_does_not_mutate_context(self):
        rule = DummyRule()
        context = {
            "triggered": False,
            "account_id": "800085BF0",
            "transaction_ids": ["SYN_S19_001"],
        }
        original = deepcopy(context)

        first = rule.evaluate(context)[0].to_dict()
        second = rule.evaluate(context)[0].to_dict()

        self.assertEqual(context, original)
        self.assertEqual(first, second)

    def test_invalid_result_type_is_rejected(self):
        class InvalidRule(DummyRule):
            def _evaluate(self, context, configuration):
                return ["not a rule result"]

        with self.assertRaises(TypeError):
            InvalidRule().evaluate({"triggered": True})

    def test_rule_result_metadata_must_match_rule(self):
        class MismatchedRule(DummyRule):
            def _evaluate(self, context, configuration):
                return [RuleResult(
                    rule_id="OTHER.RULE",
                    rule_name=self.rule_name,
                    detection_category=self.detection_category,
                    triggered=False,
                )]

        with self.assertRaises(ValueError):
            MismatchedRule().evaluate({"triggered": False})


if __name__ == "__main__":
    unittest.main()