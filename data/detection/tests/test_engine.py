"""Unit tests for the unified deterministic Rule Engine."""

import unittest

from data.detection import Evidence, Rule, RuleEngine, RuleRegistry, RuleResult


class FixedRule(Rule):
    def __init__(self, rule_id, category, results=None, error=None):
        super().__init__(rule_id, rule_id, category, "Test rule")
        self._results = results or []
        self._error = error

    def _evaluate(self, context, configuration):
        if self._error:
            raise self._error
        return list(self._results)


def result_for(rule_id, category, **values):
    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_id,
        detection_category=category,
        triggered=values.pop("triggered", True),
        **values,
    )


class RuleEngineTests(unittest.TestCase):
    def test_zero_registered_rules(self):
        outcome = RuleEngine(RuleRegistry()).run({"transactions": []})

        self.assertEqual(outcome.results, [])
        self.assertEqual(outcome.failures, [])

    def test_one_rule_and_triggered_result(self):
        registry = RuleRegistry()
        registry.register(FixedRule(
            "AML.TEST",
            "aml_transaction",
            [result_for("AML.TEST", "aml_transaction", account_id="800085BF0")],
        ))

        outcome = RuleEngine(registry).run({"transactions": []})

        self.assertEqual(len(outcome.results), 1)
        self.assertTrue(outcome.results[0].triggered)

    def test_multiple_rules_include_non_triggered_results(self):
        registry = RuleRegistry()
        registry.register(FixedRule(
            "AML.TEST",
            "aml_transaction",
            [result_for("AML.TEST", "aml_transaction", triggered=False)],
        ))
        registry.register(FixedRule(
            "INSIDER.TEST",
            "insider_threat",
            [result_for("INSIDER.TEST", "insider_threat", triggered=True, employee_id="EMP_0047")],
        ))

        outcome = RuleEngine(registry).run({})

        self.assertEqual(
            [result.rule_id for result in outcome.results],
            ["AML.TEST", "INSIDER.TEST"],
        )
        self.assertFalse(outcome.results[0].triggered)
        self.assertTrue(outcome.results[1].triggered)

    def test_aml_and_insider_rules_share_one_engine_and_preserve_evidence(self):
        registry = RuleRegistry()
        registry.register(FixedRule(
            "AML.CYCLE",
            "aml_transaction",
            [result_for(
                "AML.CYCLE",
                "aml_transaction",
                account_id="800085BF0",
                transaction_ids=["SYN_S19_001", "SYN_S19_002", "SYN_S19_003"],
                evidence=[Evidence("synthetic_hr", "injected_transaction", "SYN_S19_001", "cycle")],
            )],
        ))
        registry.register(FixedRule(
            "INSIDER.ACCESS",
            "insider_threat",
            [result_for(
                "INSIDER.ACCESS",
                "insider_threat",
                employee_id="EMP_0047",
                access_event_ids=["EVT_090040"],
                evidence=[Evidence("synthetic_hr", "access_event", "EVT_090040", "access")],
            )],
        ))

        outcome = RuleEngine(registry).run({})

        self.assertEqual(len(outcome.results), 2)
        self.assertEqual(outcome.results[0].evidence[0].record_id, "SYN_S19_001")
        self.assertEqual(outcome.results[1].evidence[0].record_id, "EVT_090040")

    def test_rule_failure_is_reported_and_later_rules_run(self):
        registry = RuleRegistry()
        registry.register(FixedRule("BAD", "test", error=RuntimeError("broken rule")))
        registry.register(FixedRule(
            "GOOD",
            "test",
            [result_for("GOOD", "test")],
        ))

        outcome = RuleEngine(registry).run({})

        self.assertEqual(len(outcome.failures), 1)
        self.assertEqual(outcome.failures[0].rule_id, "BAD")
        self.assertEqual(outcome.failures[0].error_type, "RuntimeError")
        self.assertEqual([result.rule_id for result in outcome.results], ["GOOD"])

    def test_filtering_by_account_entity_and_employee(self):
        registry = RuleRegistry()
        registry.register(FixedRule(
            "MIXED",
            "test",
            [
                result_for("MIXED", "test", account_id="800085BF0"),
                result_for("MIXED", "test", entity_type="Customer", entity_id="800085BF0"),
                result_for("MIXED", "test", employee_id="EMP_0047"),
            ],
        ))
        engine = RuleEngine(registry)

        account = engine.run({}, account_id="800085BF0")
        entity = engine.run({}, entity_id="800085BF0")
        employee = engine.run({}, employee_id="EMP_0047")

        self.assertEqual(len(account.results), 1)
        self.assertEqual(len(entity.results), 2)
        self.assertEqual(len(employee.results), 1)
        self.assertEqual(employee.results[0].employee_id, "EMP_0047")


if __name__ == "__main__":
    unittest.main()