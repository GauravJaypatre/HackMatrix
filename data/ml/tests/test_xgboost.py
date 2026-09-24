"""Unit tests for HackMatrix Phase 2 XGBoost Supervised Detection."""

import unittest
import numpy as np
import pandas as pd

from data.detection.models import RuleResult
from data.ml.features.account_features import LEAKAGE_EXCLUSIONS
from data.ml.features.feature_store import FeatureStore
from data.ml.models.xgboost_classifier import XGBoostDetector
from data.ml.evaluation.xgboost_eval import evaluate_loso_xgboost


class TestXGBoostPipeline(unittest.TestCase):
    """Test suite for XGBoost dataset construction, classifier, LOSO evaluation, and SHAP."""

    @classmethod
    def setUpClass(cls):
        cls.store = FeatureStore()
        cls.store.load_raw_data()

    def test_strict_leakage_exclusion_xgboost(self):
        """Verify no leakage fields, including background_real_laundering_count, exist in XGBoost dataset."""
        for g in [False, True]:
            for x in [False, True]:
                X, y, meta = self.store.get_xgboost_dataset(
                    include_group_g=g,
                    include_experimental_group_x=x,
                )
                for col in LEAKAGE_EXCLUSIONS:
                    self.assertNotIn(col, X.columns, f"Leakage column {col} in XGBoost dataset (G={g}, X={x})")
                # background_real_laundering_count is specifically prohibited from XGBoost
                self.assertNotIn(
                    "background_real_laundering_count",
                    X.columns,
                    "background_real_laundering_count must be excluded from XGBoost",
                )

    def test_dataset_dimensions_and_target_balance(self):
        """Verify 38 labeled accounts with 19 suspicious and 19 legitimate samples."""
        X_base, y, meta = self.store.get_xgboost_dataset(include_group_g=False, include_experimental_group_x=False)
        self.assertEqual(X_base.shape, (38, 41))
        self.assertEqual(len(y), 38)
        self.assertEqual(int((y == 1).sum()), 19)
        self.assertEqual(int((y == 0).sum()), 19)
        self.assertEqual(int(X_base.isna().sum().sum()), 0)

    def test_feature_counts_across_ablation_grid(self):
        """Verify feature dimensions for all 4 ablation configurations."""
        X1, _, _ = self.store.get_xgboost_dataset(include_group_g=False, include_experimental_group_x=False)
        X2, _, _ = self.store.get_xgboost_dataset(include_group_g=True, include_experimental_group_x=False)
        X3, _, _ = self.store.get_xgboost_dataset(include_group_g=False, include_experimental_group_x=True)
        X4, _, _ = self.store.get_xgboost_dataset(include_group_g=True, include_experimental_group_x=True)

        self.assertEqual(X1.shape[1], 41)
        self.assertEqual(X2.shape[1], 44)
        self.assertEqual(X3.shape[1], 45)
        self.assertEqual(X4.shape[1], 48)

    def test_detector_fit_predict_and_shap(self):
        """Verify detector trains and produces valid probabilities and SHAP explanations."""
        X, y, _ = self.store.get_xgboost_dataset(include_group_g=False, include_experimental_group_x=False)
        detector = XGBoostDetector(n_estimators=20, random_state=42)
        detector.fit(X, y)

        self.assertTrue(detector.is_fitted_)
        probs = detector.predict_proba(X)
        self.assertEqual(len(probs), 38)
        self.assertTrue(np.all((probs >= 0.0) & (probs <= 1.0)))

        # SHAP single account explanation
        shap_top = detector.explain_account(X.iloc[0], top_k=5)
        self.assertEqual(len(shap_top), 5)
        for item in shap_top:
            self.assertIn("feature", item)
            self.assertIn("shap_value", item)
            self.assertIn("feature_value", item)
            self.assertIn(item["impact"], ["suspicious", "legitimate", "neutral"])

        # SHAP global importance
        global_shap = detector.get_global_feature_importance(X, top_k=10)
        self.assertEqual(len(global_shap), 10)
        self.assertGreater(global_shap[0]["mean_abs_shap"], 0.0)

    def test_to_rule_result_conformity_and_json(self):
        """Verify RuleResult serialization from XGBoostDetector."""
        X, y, _ = self.store.get_xgboost_dataset(include_group_g=True, include_experimental_group_x=False)
        detector = XGBoostDetector(n_estimators=20, random_state=42).fit(X, y)

        acc_id = X.index[0]
        prob = float(detector.predict_proba(X.loc[[acc_id]])[0])
        rule_res = detector.to_rule_result(
            account_id=acc_id,
            features=X.loc[acc_id],
            probability=prob,
            threshold=0.5,
            group_g_included=True,
            group_x_included=False,
            top_k=4,
        )

        self.assertIsInstance(rule_res, RuleResult)
        self.assertEqual(rule_res.rule_id, "ML.XGBOOST")
        self.assertEqual(rule_res.detection_category, "ML_SUPERVISED")
        self.assertEqual(rule_res.account_id, acc_id)
        self.assertGreater(len(rule_res.evidence), 0)

        # JSON roundtrip
        json_str = rule_res.to_json()
        restored = RuleResult.from_json(json_str)
        self.assertEqual(restored.rule_id, "ML.XGBOOST")
        self.assertEqual(restored.metrics["suspicious_probability"], rule_res.metrics["suspicious_probability"])

    def test_loso_evaluation_and_holdouts(self):
        """Verify LOSO evaluation correctly classifies holdouts S19 and L19."""
        res = evaluate_loso_xgboost(
            include_group_g=False,
            include_experimental_group_x=False,
            feature_store=self.store,
        )

        self.assertGreaterEqual(res.roc_auc_mean, 0.70)
        self.assertEqual(res.s19_result["scenario_id"], "S19")
        self.assertEqual(res.l19_result["scenario_id"], "L19")

        # S19 must be correctly classified as suspicious, L19 as legitimate
        self.assertTrue(res.s19_result["correct"], "S19 should be correctly predicted as suspicious")
        self.assertTrue(res.l19_result["correct"], "L19 should be correctly predicted as legitimate")
        self.assertGreater(
            res.s19_result["predicted_prob"],
            res.l19_result["predicted_prob"],
            "S19 probability must exceed L19 probability",
        )

    def test_save_reload_scoring_exact_match(self):
        """Verify model saves, reloads, and scores the exact same account with unchanged predictions."""
        import tempfile
        from pathlib import Path

        X, y, _ = self.store.get_xgboost_dataset(include_group_g=True, include_experimental_group_x=False)
        original = XGBoostDetector(n_estimators=30, random_state=42).fit(X, y)

        with tempfile.TemporaryDirectory() as tmp_dir:
            model_file = Path(tmp_dir) / "test_xgb.json"
            meta_file = Path(tmp_dir) / "test_xgb_meta.json"

            original.save_model(str(model_file), str(meta_file))

            # Reload model
            reloaded = XGBoostDetector.load_model(str(model_file), str(meta_file))

            # Score test accounts: S19 and L19
            s19_feats = X.loc["800085BF0"]
            l19_feats = X.loc["80026A5A0"]

            prob_orig_s19 = float(original.predict_proba(pd.DataFrame([s19_feats]))[0])
            prob_reloaded_s19 = float(reloaded.predict_proba(pd.DataFrame([s19_feats]))[0])

            prob_orig_l19 = float(original.predict_proba(pd.DataFrame([l19_feats]))[0])
            prob_reloaded_l19 = float(reloaded.predict_proba(pd.DataFrame([l19_feats]))[0])

            # Exact match verification
            self.assertAlmostEqual(prob_orig_s19, prob_reloaded_s19, places=6)
            self.assertAlmostEqual(prob_orig_l19, prob_reloaded_l19, places=6)

            # Test predict_account single-account inference API
            res_s19 = reloaded.predict_account(s19_feats, account_id="800085BF0")
            self.assertEqual(res_s19["account_id"], "800085BF0")
            self.assertEqual(res_s19["predicted_class"], 1)
            self.assertEqual(res_s19["predicted_label"], "suspicious")
            self.assertAlmostEqual(res_s19["suspicious_probability"], prob_orig_s19, places=4)
            self.assertEqual(res_s19["rule_result"].rule_id, "ML.XGBOOST")
            self.assertGreater(len(res_s19["top_shap_features"]), 0)


if __name__ == "__main__":
    unittest.main()
