"""Repository-backed tests for the privilege-change rule."""

from pathlib import Path
import unittest

import pandas as pd

from data.detection.rules.privilege_change import PrivilegeChangeRule


DATA_DIR = Path(__file__).resolve().parents[3] / "data"


class PrivilegeChangeRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.access_events = pd.read_csv(
            DATA_DIR / "synthetic_hr" / "access_events.csv",
            dtype=str,
        ).fillna("").to_dict("records")
        cls.profile_changes = pd.read_csv(
            DATA_DIR / "synthetic_hr" / "profile_changes.csv",
            dtype=str,
        ).fillna("").to_dict("records")
        cls.employees = pd.read_csv(
            DATA_DIR / "synthetic_hr" / "employees.csv",
            dtype=str,
        ).fillna("").to_dict("records")
        cls.rule = PrivilegeChangeRule()

    def evaluate(self, access_events=None, profile_changes=None):
        return self.rule.evaluate({
            "access_events": self.access_events if access_events is None else access_events,
            "profile_changes": self.profile_changes if profile_changes is None else profile_changes,
            "employees": self.employees,
        })

    def test_s01_to_s06_known_examples(self):
        results = self.evaluate()
        by_event = {
            result.access_event_ids[0]: result
            for result in results
        }

        expected = {
            "EVT_090001": "CHG_090001",
            "EVT_090002": "CHG_090002",
            # CHG_090003 is five minutes after EVT_090003 in the live data,
            # so it is intentionally not paired under the same-timestamp rule.
            "EVT_090003": None,
            "EVT_090004": None,
            "EVT_090005": "CHG_090004",
            "EVT_090006": None,
        }
        for event_id, change_id in expected.items():
            self.assertIn(event_id, by_event)
            if change_id:
                self.assertEqual(by_event[event_id].profile_change_ids, [change_id])
            else:
                self.assertEqual(by_event[event_id].profile_change_ids, [])

    def test_qualifying_access_change_triggers_with_investigator_details(self):
        results = self.evaluate()
        result = next(item for item in results if item.access_event_ids == ["EVT_090001"])

        self.assertTrue(result.triggered)
        self.assertEqual(result.employee_id, "EMP_0011")
        self.assertEqual(result.account_id, "800056370")
        self.assertEqual(result.metrics["action"], "modify")
        self.assertEqual(result.metrics["old_value"], "transfer_limit=10000")
        self.assertEqual(result.metrics["new_value"], "transfer_limit=100000")
        self.assertEqual(result.detection_timestamp, "2022-09-06 14:12:46")

    def test_access_only_qualifying_event_is_reported(self):
        results = self.evaluate()
        result = next(item for item in results if item.access_event_ids == ["EVT_090004"])

        self.assertEqual(result.profile_change_ids, [])
        self.assertEqual([item.record_id for item in result.evidence], ["EVT_090004"])

    def test_s08_fraud_alert_and_l04_view_only_are_administrative_events(self):
        results = self.evaluate()
        by_event = {
            result.access_event_ids[0]: result
            for result in results
        }

        self.assertIn("EVT_090008", by_event)
        self.assertIn("EVT_090024", by_event)
        self.assertEqual(by_event["EVT_090008"].account_id, "800057620")
        self.assertEqual(by_event["EVT_090024"].account_id, "80005A6B0")

    def test_matching_profile_change_is_one_logical_signal(self):
        results = self.evaluate()
        matching = [item for item in results if item.access_event_ids == ["EVT_090001"]]

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].metrics["paired_profile_change_count"], 1)
        self.assertEqual(
            [item.record_id for item in matching[0].evidence],
            ["EVT_090001", "CHG_090001"],
        )

    def test_legitimate_lookalike_is_reported_without_malicious_label(self):
        results = self.evaluate()
        result = next(item for item in results if item.access_event_ids == ["EVT_090021"])

        self.assertTrue(result.triggered)
        self.assertEqual(result.account_id, "800059C00")
        self.assertIsNone(result.scenario_id)
        self.assertNotIn("fraud", result.explanation.lower())
        self.assertNotIn("malicious", result.explanation.lower())

    def test_unrelated_ordinary_profile_change_does_not_trigger(self):
        profile = next(
            item for item in self.profile_changes
            if item["change_id"] == "CHG_000001"
        )

        self.assertEqual(self.evaluate(access_events=[], profile_changes=[profile]), [])

    def test_missing_optional_profile_pair_is_safe(self):
        event = next(item for item in self.access_events if item["event_id"] == "EVT_090004")

        results = self.evaluate(access_events=[event], profile_changes=[])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].profile_change_ids, [])

    def test_malformed_and_empty_input_is_safe(self):
        malformed = [
            {},
            {"event_id": "", "employee_id": "EMP_0001", "action": "grant",
             "target_account_id": "800056370", "old_value": "",
             "new_value": "full_access", "timestamp": "2022-09-01 09:00:00"},
            {"event_id": "EVT_BAD", "employee_id": "EMP_0001", "action": "modify",
             "target_account_id": "", "old_value": "", "new_value": "",
             "timestamp": "2022-09-01 09:00:00"},
            {"event_id": "EVT_BAD_2", "employee_id": "EMP_0001", "action": "modify",
             "target_account_id": "800056370", "old_value": "address=A",
             "new_value": "address=B", "timestamp": "2022-09-01 09:00:00"},
        ]

        self.assertEqual(self.evaluate(access_events=malformed, profile_changes=None), [])


if __name__ == "__main__":
    unittest.main()