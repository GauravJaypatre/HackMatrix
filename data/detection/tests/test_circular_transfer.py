"""Tests for AML.CIRCULAR_TRANSFER using repository and focused records."""

from pathlib import Path
import unittest

import pandas as pd

from data.detection.config import load_rule_configuration
from data.detection.rules.circular_transfer import CircularTransferRule


DATA_DIR = Path(__file__).resolve().parents[3] / "data"
RULE_ID = "AML.CIRCULAR_TRANSFER"


class CircularTransferRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transactions = pd.read_csv(
            DATA_DIR / "synthetic_hr" / "injected_transactions.csv",
            dtype=str,
        ).fillna("").to_dict("records")
        cls.rule = CircularTransferRule()
        cls.configuration = load_rule_configuration()[RULE_ID]

    def evaluate(self, transactions, configuration=None):
        return self.rule.evaluate(
            {"injected_transactions": transactions},
            self.configuration if configuration is None else configuration,
        )

    def test_s19_circular_path_triggers(self):
        transactions = [row for row in self.transactions if row["scenario_id"] == "S19"]

        results = self.evaluate(transactions)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].triggered)
        self.assertEqual(results[0].account_id, "800085BF0")
        self.assertEqual(results[0].transaction_ids, [
            "SYN_S19_001",
            "SYN_S19_002",
            "SYN_S19_003",
        ])

    def test_l19_linear_path_does_not_trigger(self):
        transactions = [row for row in self.transactions if row["scenario_id"] == "L19"]

        self.assertEqual(self.evaluate(transactions), [])

    def test_minimum_three_transactions_is_required(self):
        transactions = self._cycle_rows()[:2]
        transactions.append(dict(self._cycle_rows()[2]))
        configuration = dict(self.configuration)
        configuration["minimum_transactions"] = 4

        self.assertEqual(self.evaluate(transactions, configuration), [])

    def test_closed_path_is_required(self):
        transactions = self._cycle_rows()
        transactions[-1] = dict(transactions[-1])
        transactions[-1]["to_account"] = "D"

        self.assertEqual(self.evaluate(transactions), [])

    def test_configured_48_hour_window_is_used(self):
        results = self.evaluate(self._cycle_rows())

        self.assertEqual(results[0].thresholds["time_window_hours"], 48)
        self.assertEqual(results[0].window_start, "2022-09-01 00:00:00")
        self.assertEqual(results[0].window_end, "2022-09-02 00:00:00")

    def test_cycle_outside_window_does_not_trigger(self):
        transactions = self._cycle_rows()
        transactions[-1] = dict(transactions[-1])
        transactions[-1]["timestamp"] = "2022-09-03 00:00:01"

        self.assertEqual(self.evaluate(transactions), [])

    def test_duplicate_cycle_detection_is_collapsed(self):
        transactions = self._cycle_rows()
        rotated = [dict(row) for row in transactions[1:] + transactions[:1]]

        results = self.evaluate(transactions + rotated)

        self.assertEqual(len(results), 1)

    def test_evidence_contains_every_transaction_and_account(self):
        result = self.evaluate([
            row for row in self.transactions if row["scenario_id"] == "S19"
        ])[0]

        self.assertEqual(
            [item.record_id for item in result.evidence],
            ["SYN_S19_001", "SYN_S19_002", "SYN_S19_003"],
        )
        self.assertEqual(
            result.metrics["participating_account_ids"],
            ["800085BF0", "800093C80", "8001C3570"],
        )
        self.assertTrue(all(item.details["path"].endswith("800085BF0") for item in result.evidence))

    def test_explanation_is_complete_and_does_not_claim_intent(self):
        result = self.evaluate([
            row for row in self.transactions if row["scenario_id"] == "S19"
        ])[0]

        self.assertIn("AML.CIRCULAR_TRANSFER", result.explanation)
        self.assertIn("Circular transfer", result.explanation)
        self.assertIn("800085BF0 -> 800093C80 -> 8001C3570 -> 800085BF0", result.explanation)
        self.assertIn("48-hour window", result.explanation)
        self.assertNotIn("fraud", result.explanation.lower())
        self.assertNotIn("malicious", result.explanation.lower())

    def test_disabled_configuration_produces_no_detections(self):
        configuration = dict(self.configuration)
        configuration["enabled"] = False

        self.assertEqual(self.evaluate(self._cycle_rows(), configuration), [])

    def test_empty_and_malformed_transactions_are_safe(self):
        malformed = [
            {},
            {"transaction_id": "", "timestamp": "2022-09-01 00:00:00",
             "from_account": "A", "to_account": "B"},
            {"transaction_id": "TX_BAD", "timestamp": "not-a-time",
             "from_account": "A", "to_account": "B"},
            "not a record",
        ]

        self.assertEqual(self.evaluate(malformed), [])
        self.assertEqual(self.evaluate([]), [])

    @staticmethod
    def _cycle_rows():
        return [
            {"transaction_id": "TX_A", "timestamp": "2022-09-01 00:00:00",
             "from_account": "A", "to_account": "B"},
            {"transaction_id": "TX_B", "timestamp": "2022-09-01 12:00:00",
             "from_account": "B", "to_account": "C"},
            {"transaction_id": "TX_C", "timestamp": "2022-09-02 00:00:00",
             "from_account": "C", "to_account": "A"},
        ]


if __name__ == "__main__":
    unittest.main()