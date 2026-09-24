"""Tests for AML.TRANSACTION_SPLITTING using repository data."""

from pathlib import Path
import unittest

import pandas as pd

from data.detection.config import load_rule_configuration
from data.detection.rules.transaction_splitting import TransactionSplittingRule


DATA_DIR = Path(__file__).resolve().parents[3] / "data"
RULE_ID = "AML.TRANSACTION_SPLITTING"


class TransactionSplittingRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transactions = pd.read_csv(
            DATA_DIR / "synthetic_hr" / "injected_transactions.csv",
            dtype=str,
        ).fillna("").to_dict("records")
        cls.rule = TransactionSplittingRule()
        cls.configuration = load_rule_configuration()[RULE_ID]

    def evaluate(self, transactions, configuration=None):
        return self.rule.evaluate(
            {"injected_transactions": transactions},
            self.configuration if configuration is None else configuration,
        )

    def scenario(self, scenario_id):
        return [row for row in self.transactions if row["scenario_id"] == scenario_id]

    def test_known_suspicious_splitting_patterns_trigger(self):
        for scenario_id in ("S01", "S07", "S09", "S10"):
            with self.subTest(scenario_id=scenario_id):
                results = self.evaluate(self.scenario(scenario_id))
                self.assertTrue(results)
                self.assertTrue(all(result.triggered for result in results))

    def test_legitimate_l01_payroll_split_is_detected_by_observable_pattern(self):
        results = self.evaluate(self.scenario("L01"))

        self.assertTrue(results)
        self.assertEqual(results[0].account_id, "800059C00")

    def test_fewer_than_three_transactions_does_not_trigger(self):
        self.assertEqual(self.evaluate(self._rows()[:2]), [])

    def test_three_transactions_without_sub_boundary_amount_does_not_trigger(self):
        rows = self._rows()
        for row in rows:
            row["amount_paid"] = "10000"

        self.assertEqual(self.evaluate(rows), [])

    def test_three_transactions_with_one_sub_boundary_amount_triggers(self):
        rows = self._rows()
        rows[0]["amount_paid"] = "9999.99"

        results = self.evaluate(rows)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].transaction_ids, ["TX_1", "TX_2", "TX_3"])

    def test_transactions_outside_window_are_not_grouped(self):
        rows = self._rows()
        rows[-1]["timestamp"] = "2022/09/03 00:00:01"

        self.assertEqual(self.evaluate(rows), [])

    def test_different_sending_accounts_are_not_grouped(self):
        rows = self._rows()
        rows[1]["from_account"] = "OTHER_ACCOUNT"

        self.assertEqual(self.evaluate(rows), [])

    def test_evidence_contains_all_matching_transactions_and_values(self):
        result = self.evaluate(self.scenario("S01"))[0]

        self.assertEqual(result.transaction_ids, [
            "SYN_S01_001",
            "SYN_S01_002",
            "SYN_S01_003",
            "SYN_S01_004",
            "SYN_S01_005",
            "SYN_S01_006",
            "SYN_S01_007",
            "SYN_S01_008",
            "SYN_S01_009",
            "SYN_S01_010",
            "SYN_S01_011",
            "SYN_S01_012",
        ])
        self.assertEqual(
            [item.record_id for item in result.evidence],
            result.transaction_ids,
        )
        self.assertTrue(all("to_account" in item.details for item in result.evidence))
        self.assertTrue(all("amount_paid" in item.details for item in result.evidence))
        self.assertTrue(all("payment_format" in item.details for item in result.evidence))

    def test_explanation_contains_observed_values(self):
        result = self.evaluate(self.scenario("S01"))[0]

        self.assertIn("AML.TRANSACTION_SPLITTING", result.explanation)
        self.assertIn("800056370", result.explanation)
        self.assertIn("12 outgoing transactions", result.explanation)
        self.assertIn("48-hour window", result.explanation)
        self.assertIn("$10,000.00", result.explanation)
        self.assertNotIn("fraud", result.explanation.lower())
        self.assertNotIn("malicious", result.explanation.lower())

    def test_disabled_configuration_produces_no_detections(self):
        configuration = dict(self.configuration)
        configuration["enabled"] = False

        self.assertEqual(self.evaluate(self.scenario("S01"), configuration), [])

    def test_empty_and_malformed_data_is_safe(self):
        malformed = [
            {},
            {"transaction_id": "", "timestamp": "2022/09/01 00:00",
             "from_account": "A", "to_account": "B", "amount_paid": "1",
             "payment_format": "Wire"},
            {"transaction_id": "BAD", "timestamp": "not-a-time",
             "from_account": "A", "to_account": "B", "amount_paid": "1",
             "payment_format": "Wire"},
            {"transaction_id": "BAD_AMOUNT", "timestamp": "2022/09/01 00:00",
             "from_account": "A", "to_account": "B", "amount_paid": "not-number",
             "payment_format": "Wire"},
            "not a record",
        ]

        self.assertEqual(self.evaluate(malformed), [])
        self.assertEqual(self.evaluate([]), [])

    @staticmethod
    def _rows():
        return [
            {"transaction_id": "TX_1", "timestamp": "2022/09/01 00:00",
             "from_account": "ACCOUNT_A", "to_account": "B",
             "amount_paid": "9999.99", "payment_format": "Wire"},
            {"transaction_id": "TX_2", "timestamp": "2022/09/01 12:00",
             "from_account": "ACCOUNT_A", "to_account": "C",
             "amount_paid": "12000", "payment_format": "Wire"},
            {"transaction_id": "TX_3", "timestamp": "2022/09/02 00:00",
             "from_account": "ACCOUNT_A", "to_account": "D",
             "amount_paid": "15000", "payment_format": "ACH"},
        ]


if __name__ == "__main__":
    unittest.main()