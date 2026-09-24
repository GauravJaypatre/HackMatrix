"""Unit tests for HackMatrix Phase 1 Isolation Forest Anomaly Detection."""

import json
import unittest
import numpy as np
import pandas as pd

from data.detection.models import RuleResult
from data.ml.features.account_features import (
    FEATURE_GROUPS,
    LEAKAGE_EXCLUSIONS,
)
from data.ml.features.feature_store import FeatureStore
from data.ml.models.isolation_forest import IsolationForestDetector
from data.ml.evaluation.isolation_forest_eval import run_isolation_forest_evaluation


class TestIsolationForestPipeline(unittest.TestCase):
    """Test suite for feature extraction, store partitioning, model, and explainability."""

    @classmethod
    def setUpClass(cls):
        cls.store = FeatureStore()
        cls.store.load_raw_data()

    def test_leakage_exclusion_strict(self):
        """Verify that absolutely no leakage columns exist in feature matrices."""
        matrix_no_x = self.store.get_feature_matrix(include_experimental_group_x=False)
        matrix_with_x = self.store.get_feature_matrix(include_experimental_group_x=True)

        for name in LEAKAGE_EXCLUSIONS:
            self.assertNotIn(name, matrix_no_x.columns, f"Leakage column {name} found in matrix without X")
            self.assertNotIn(name, matrix_with_x.columns, f"Leakage column {name} found in matrix with X")

    def test_dataset_splits_counts(self):
        """Verify exact account counts: 1,846 background, 38 labeled evaluation (19 susp + 19 legit)."""
        X_bg, X_ev, y_ev, meta = self.store.get_dataset_splits(include_experimental_group_x=False)

        self.assertEqual(len(X_bg), 1846, f"Expected 1,846 background accounts, got {len(X_bg)}")
        self.assertEqual(len(X_ev), 38, f"Expected 38 evaluation accounts, got {len(X_ev)}")
        self.assertEqual(len(y_ev), 38, f"Expected 38 labels, got {len(y_ev)}")

        # Check balance
        counts = y_ev.value_counts().to_dict()
        self.assertEqual(counts.get(1), 19, "Expected 19 suspicious evaluation accounts")
        self.assertEqual(counts.get(0), 19, "Expected 19 legitimate evaluation accounts")

        # Disjoint check
        overlap = set(X_bg.index).intersection(set(X_ev.index))
        self.assertEqual(len(overlap), 0, "Background and evaluation sets must be disjoint")

    def test_no_missing_values(self):
        """Verify zero NaN/inf values in computed feature matrices."""
        matrix = self.store.get_feature_matrix(include_experimental_group_x=True)
        self.assertEqual(int(matrix.isna().sum().sum()), 0, "Feature matrix contains NaN values")
        self.assertTrue(np.all(np.isfinite(matrix.values)), "Feature matrix contains non-finite values")

    def test_group_x_toggle_ablation(self):
        """Verify feature dimensions when toggling experimental Group X."""
        names_off = self.store.get_feature_names(include_experimental_group_x=False)
        names_on = self.store.get_feature_names(include_experimental_group_x=True)

        self.assertEqual(len(names_off), 40, f"Expected 40 features without Group X, got {len(names_off)}")
        self.assertEqual(len(names_on), 44, f"Expected 44 features with Group X, got {len(names_on)}")

        diff = set(names_on) - set(names_off)
        expected_diff = set(FEATURE_GROUPS["group_x"])
        self.assertEqual(diff, expected_diff, f"Group X diff mismatch: {diff} vs {expected_diff}")

    def test_isolation_forest_fit_and_score(self):
        """Verify detector trains strictly on background accounts and produces valid anomaly scores."""
        X_bg, X_ev, y_ev, meta = self.store.get_dataset_splits(include_experimental_group_x=False)

        detector = IsolationForestDetector(n_estimators=100, random_state=42)
        detector.fit(X_bg)

        self.assertTrue(detector.is_fitted_)
        self.assertEqual(len(detector.bg_scores_), 1846)

        scores = detector.score_accounts(X_ev)
        self.assertEqual(len(scores), 38)
        self.assertTrue((scores > 0.0).all() and (scores < 1.0).all(), "Scores should lie strictly in (0, 1)")

    def test_explainability_and_attribution(self):
        """Verify explain_account computes valid, non-fabricated feature contributions."""
        X_bg, X_ev, y_ev, meta = self.store.get_dataset_splits(include_experimental_group_x=False)
        detector = IsolationForestDetector(n_estimators=100, random_state=42).fit(X_bg)

        sample = X_ev.iloc[0]
        top_features = detector.explain_account(sample, top_k=5)

        self.assertEqual(len(top_features), 5)
        for feat in top_features:
            self.assertIn("feature", feat)
            self.assertIn("score_delta", feat)
            self.assertIn("value", feat)
            self.assertIn("baseline_median", feat)
            self.assertIn("direction", feat)
            self.assertIn(feat["direction"], ["elevated", "depressed", "normal"])

    def test_to_rule_result_schema_and_serialization(self):
        """Verify RuleResult generation adheres strictly to detection models and serializes cleanly."""
        X_bg, X_ev, y_ev, meta = self.store.get_dataset_splits(include_experimental_group_x=False)
        detector = IsolationForestDetector(n_estimators=100, random_state=42).fit(X_bg)

        acc_id = X_ev.index[0]
        score = float(detector.score_accounts(X_ev.loc[[acc_id]]).iloc[0])
        features = X_ev.loc[acc_id]

        rule_res = detector.to_rule_result(
            account_id=acc_id,
            features=features,
            anomaly_score=score,
            group_x_included=False,
            top_k=4,
        )

        self.assertIsInstance(rule_res, RuleResult)
        self.assertEqual(rule_res.rule_id, "ML.ISOLATION_FOREST")
        self.assertEqual(rule_res.detection_category, "ML_ANOMALY")
        self.assertEqual(rule_res.account_id, acc_id)
        self.assertGreater(len(rule_res.evidence), 0)

        # JSON roundtrip test
        json_str = rule_res.to_json()
        self.assertIsInstance(json_str, str)
        restored = RuleResult.from_json(json_str)
        self.assertEqual(restored.rule_id, rule_res.rule_id)
        self.assertEqual(restored.account_id, rule_res.account_id)
        self.assertEqual(restored.metrics["anomaly_score"], rule_res.metrics["anomaly_score"])

    def test_s19_and_l19_holdouts(self):
        """Verify S19 (circular transfer) and L19 holdout results."""
        res_off = run_isolation_forest_evaluation(include_experimental_group_x=False, n_estimators=100)

        s19 = res_off.s19_result
        l19 = res_off.l19_result

        self.assertEqual(s19["scenario_id"], "S19")
        self.assertEqual(l19["scenario_id"], "L19")
        self.assertTrue(s19["above_threshold"], "S19 anomaly score should exceed background threshold")
        # S19 should score higher than L19
        self.assertGreater(s19["anomaly_score"], l19["anomaly_score"], "S19 score should exceed L19 score")


if __name__ == "__main__":
    unittest.main()
