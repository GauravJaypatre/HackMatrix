"""Tests for deterministic rule configuration."""

from copy import deepcopy
from pathlib import Path
import unittest

import pandas as pd

from data.detection.config import load_rule_configuration
from data.detection.engine import RuleEngine
from data.detection.registry import RuleRegistry
from data.detection.rules.privilege_change import PrivilegeChangeRule


DATA_DIR = Path(__file__).resolve().parents[3] / "data"
RULE_ID = "INSIDER.PRIVILEGE_CHANGE"


class RuleConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = DATA_DIR / "synthetic_hr"
        cls.access_events = pd.read_csv(
            base / "access_events.csv", dtype=str
        ).fillna("").to_dict("records")
        cls.profile_changes = pd.read_csv(
            base / "profile_changes.csv", dtype=str
        ).fillna("").to_dict("records")
        cls.employees = pd.read_csv(
            base / "employees.csv", dtype=str
        ).fillna("").to_dict("records")

    def default_configuration(self):
        return deepcopy(load_rule_configuration()[RULE_ID])

    def context(self, access_events=None, profile_changes=None):
        return {
            "access_events": self.access_events if access_events is None else access_events,
            "profile_changes": self.profile_changes if profile_changes is None else profile_changes,
            "employees": self.employees,
        }

    def test_rule_is_enabled_by_default(self):
        configuration = load_rule_configuration()

        self.assertTrue(configuration[RULE_ID]["enabled"])

    def test_engine_can_disable_rule_from_configuration(self):
        registry = RuleRegistry()
        registry.register(PrivilegeChangeRule())
        configuration = {RULE_ID: self.default_configuration()}
        configuration[RULE_ID]["enabled"] = False

        outcome = RuleEngine(registry).run(self.context(), configuration)

        self.assertEqual(outcome.results, [])
        self.assertEqual(outcome.failures, [])

    def test_configured_administrative_categories_are_used(self):
        event = next(item for item in self.access_events if item["event_id"] == "EVT_090001")
        configuration = self.default_configuration()
        configuration["qualifying_administrative_categories"] = ["api"]

        results = PrivilegeChangeRule().evaluate(
            self.context(access_events=[event]), configuration
        )

        self.assertEqual(results, [])

    def test_configured_profile_fields_are_used(self):
        event = next(item for item in self.access_events if item["event_id"] == "EVT_090001")
        change = next(item for item in self.profile_changes if item["change_id"] == "CHG_090001")
        configured_change = dict(change)
        configured_change["field_changed"] = "phone"
        configuration = self.default_configuration()
        configuration["qualifying_profile_change_fields"] = ["phone"]

        results = PrivilegeChangeRule().evaluate(
            self.context(access_events=[event], profile_changes=[configured_change]),
            configuration,
        )

        self.assertEqual(results[0].profile_change_ids, ["CHG_090001"])

    def test_timestamp_matching_is_exact_and_visible_in_output(self):
        event = next(item for item in self.access_events if item["event_id"] == "EVT_090003")
        change = next(item for item in self.profile_changes if item["change_id"] == "CHG_090003")

        result = next(item for item in PrivilegeChangeRule().evaluate(
            self.context(access_events=[event], profile_changes=[change])
        ))

        self.assertEqual(result.profile_change_ids, [])
        self.assertEqual(result.thresholds["paired_record_window"], "exact")
        self.assertEqual(
            result.evidence[0].details["configuration"]["matching_timestamp"],
            "exact",
        )

    def test_invalid_configuration_fails_clearly(self):
        invalid_cases = [
            {"enabled": "yes"},
            {"qualifying_administrative_categories": "access"},
            {"qualifying_profile_change_fields": []},
            {"matching_timestamp": "within_window"},
            {"require_matching_employee": "yes"},
            {"minimum_qualifying_events": 2},
        ]

        for invalid in invalid_cases:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    PrivilegeChangeRule().evaluate(self.context(), invalid)


if __name__ == "__main__":
    unittest.main()