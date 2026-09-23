"""Unit tests for standardized rule results and evidence."""

import json
import unittest

from data.detection.models import Evidence, RuleResult


class RuleResultTests(unittest.TestCase):
    def test_triggered_result_contains_investigation_fields(self):
        result = RuleResult(
            rule_id="AML.CIRCULAR_TRANSFER",
            rule_name="Circular transfer",
            detection_category="aml_transaction",
            triggered=True,
            entity_type="Account",
            entity_id="800085BF0",
            account_id="800085BF0",
            transaction_ids=[
                "SYN_S19_001",
                "SYN_S19_002",
                "SYN_S19_003",
            ],
            scenario_id="S19",
            explanation="Funds returned to the originating account.",
            metrics={"transaction_count": 3},
            thresholds={"maximum_window_hours": 48},
            detection_timestamp="2022/09/14 21:05",
            window_start="2022/09/14 10:15",
            window_end="2022/09/14 21:05",
            evidence=[
                Evidence(
                    source_dataset="synthetic_hr",
                    record_type="injected_transaction",
                    record_id="SYN_S19_001",
                    role="cycle_transaction",
                    details={"from_account": "800085BF0"},
                )
            ],
        )

        self.assertTrue(result.triggered)
        self.assertEqual(result.account_id, "800085BF0")
        self.assertEqual(result.scenario_id, "S19")
        self.assertEqual(result.evidence[0].record_id, "SYN_S19_001")

    def test_non_triggered_result_is_serializable(self):
        result = RuleResult(
            rule_id="AML.TRANSACTION_SPLITTING",
            rule_name="Transaction splitting",
            detection_category="aml_transaction",
            triggered=False,
            account_id="800085BF0",
            explanation="No configured splitting pattern was found.",
            metrics={"matching_transaction_count": 1},
            thresholds={"minimum_transaction_count": 3},
        )

        self.assertFalse(result.triggered)
        self.assertEqual(result.evidence, [])
        self.assertIsInstance(result.to_json(), str)

    def test_multiple_evidence_ids_are_preserved(self):
        result = RuleResult(
            rule_id="INSIDER.PRIVILEGE_CHANGE",
            rule_name="Privilege change",
            detection_category="insider_threat",
            triggered=True,
            entity_type="Employee",
            entity_id="EMP_0047",
            employee_id="EMP_0047",
            account_id="800085BF0",
            access_event_ids=["EVT_090040"],
            profile_change_ids=["CHG_000206", "CHG_000207"],
            evidence=[
                Evidence("synthetic_hr", "access_event", "EVT_090040", "access_change"),
                Evidence("synthetic_hr", "profile_change", "CHG_000206", "profile_change"),
            ],
        )

        restored = RuleResult.from_json(result.to_json())

        self.assertEqual(restored.access_event_ids, ["EVT_090040"])
        self.assertEqual(restored.profile_change_ids, ["CHG_000206", "CHG_000207"])
        self.assertEqual([item.record_id for item in restored.evidence], [
            "EVT_090040",
            "CHG_000206",
        ])

    def test_aml_evidence(self):
        evidence = Evidence(
            source_dataset="synthetic_hr",
            record_type="injected_transaction",
            record_id="SYN_S19_002",
            role="supporting_transaction",
            details={
                "from_account": "800093C80",
                "to_account": "8001C3570",
                "payment_format": "Wire",
            },
        )

        self.assertEqual(evidence.record_id, "SYN_S19_002")
        self.assertEqual(evidence.details["payment_format"], "Wire")

    def test_insider_threat_evidence(self):
        evidence = Evidence(
            source_dataset="synthetic_hr",
            record_type="access_event",
            record_id="EVT_090040",
            role="triggering_access",
            details={
                "employee_id": "EMP_0047",
                "target_account_id": "800085BF0",
            },
        )

        self.assertEqual(evidence.record_type, "access_event")
        self.assertEqual(evidence.details["employee_id"], "EMP_0047")

    def test_serialization_and_deserialization(self):
        result = RuleResult(
            rule_id="INSIDER.PROFILE_MISMATCH",
            rule_name="Profile mismatch",
            detection_category="insider_threat",
            triggered=True,
            customer_id="800085BF0",
            profile_change_ids=["CHG_000206"],
            explanation="Profile ownership changed to an unexpected entity.",
            evidence=[
                Evidence(
                    "synthetic_hr",
                    "profile_change",
                    "CHG_000206",
                    "triggering_profile_change",
                )
            ],
        )

        payload = result.to_dict()
        restored = RuleResult.from_dict(json.loads(json.dumps(payload)))

        self.assertEqual(restored.to_dict(), payload)
        self.assertIsInstance(restored.evidence[0], Evidence)


if __name__ == "__main__":
    unittest.main()