"""XGBoost supervised classifier and SHAP explainability for HackMatrix AML detection."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import shap
import xgboost as xgb

from data.detection.models import Evidence, RuleResult


class XGBoostDetector:
    """Conservative, regularized XGBoost classifier for prototype-level account detection."""

    def __init__(
        self,
        n_estimators: int = 40,
        max_depth: int = 3,
        learning_rate: float = 0.08,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        reg_alpha: float = 0.5,
        reg_lambda: float = 1.0,
        scale_pos_weight: float = 1.0,
        random_state: int = 42,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.reg_alpha = reg_alpha
        self.reg_lambda = reg_lambda
        self.scale_pos_weight = scale_pos_weight
        self.random_state = random_state

        self.model = xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            reg_alpha=self.reg_alpha,
            reg_lambda=self.reg_lambda,
            scale_pos_weight=self.scale_pos_weight,
            eval_metric="logloss",
            random_state=self.random_state,
            n_jobs=-1,
        )

        self.feature_names_: List[str] = []
        self.is_fitted_: bool = False
        self._explainer: Optional[shap.TreeExplainer] = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "XGBoostDetector":
        """Fit XGBoost classifier on training data."""
        if not isinstance(X, pd.DataFrame):
            raise TypeError("X must be a pandas DataFrame.")

        self.feature_names_ = list(X.columns)
        self.model.fit(X.values, y.values)
        self.is_fitted_ = True
        self._explainer = shap.TreeExplainer(self.model)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return predicted probability of being suspicious (class 1)."""
        if not self.is_fitted_:
            raise RuntimeError("Detector must be fitted before predict_proba.")
        probs = self.model.predict_proba(X[self.feature_names_].values)
        return probs[:, 1]

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        """Return binary prediction based on probability threshold."""
        probs = self.predict_proba(X)
        return (probs >= threshold).astype(int)

    def explain_account(
        self,
        account_series: pd.Series,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Compute SHAP contributions for a single account."""
        if not self.is_fitted_ or self._explainer is None:
            raise RuntimeError("Detector must be fitted before explain_account.")

        feat_values = account_series[self.feature_names_].values.reshape(1, -1).astype(float)
        shap_res = self._explainer(feat_values)
        values = shap_res.values[0]

        contributions: List[Dict[str, Any]] = []
        for i, fname in enumerate(self.feature_names_):
            val = float(feat_values[0, i])
            shap_val = float(values[i])
            contributions.append({
                "feature": fname,
                "shap_value": float(round(shap_val, 4)),
                "feature_value": float(round(val, 4)),
                "impact": "suspicious" if shap_val > 0 else ("legitimate" if shap_val < 0 else "neutral"),
            })

        # Rank by absolute SHAP contribution
        ranked = sorted(contributions, key=lambda c: abs(c["shap_value"]), reverse=True)
        return ranked[:top_k]

    def get_global_feature_importance(self, X: pd.DataFrame, top_k: int = 10) -> List[Dict[str, Any]]:
        """Compute mean absolute SHAP values across an evaluation population."""
        if not self.is_fitted_ or self._explainer is None:
            raise RuntimeError("Detector must be fitted before get_global_feature_importance.")

        shap_matrix = self._explainer(X[self.feature_names_].values).values
        mean_abs_shap = np.abs(shap_matrix).mean(axis=0)

        importance_list = [
            {"feature": fname, "mean_abs_shap": float(round(mean_abs_shap[i], 4))}
            for i, fname in enumerate(self.feature_names_)
        ]
        importance_list.sort(key=lambda item: item["mean_abs_shap"], reverse=True)
        return importance_list[:top_k]

    def save_model(
        self,
        model_path: str,
        metadata_path: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """Save the trained XGBoost model and associated feature/preprocessing metadata."""
        if not self.is_fitted_:
            raise RuntimeError("Cannot save an unfitted model.")

        from pathlib import Path
        import json

        m_path = Path(model_path)
        m_path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(m_path))

        meta_p = Path(metadata_path) if metadata_path else m_path.with_name(f"{m_path.stem}_metadata.json")

        metadata = {
            "model_name": "HackMatrix XGBoost Supervised AML Classifier",
            "model_version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model_file": m_path.name,
            "hyperparameters": {
                "n_estimators": self.n_estimators,
                "max_depth": self.max_depth,
                "learning_rate": self.learning_rate,
                "subsample": self.subsample,
                "colsample_bytree": self.colsample_bytree,
                "reg_alpha": self.reg_alpha,
                "reg_lambda": self.reg_lambda,
                "scale_pos_weight": self.scale_pos_weight,
                "random_state": self.random_state,
            },
            "feature_count": len(self.feature_names_),
            "feature_names": self.feature_names_,
            "preprocessing": {
                "default_threshold": 0.5,
                "risk_rating_mapping": {"low": 0.0, "medium": 1.0, "high": 2.0},
                "rule_engine_rules": [
                    "INSIDER.PRIVILEGE_CHANGE",
                    "AML.CIRCULAR_TRANSFER",
                    "AML.TRANSACTION_SPLITTING",
                ],
                "leakage_exclusions": [
                    "expected_signals",
                    "scenario_type",
                    "scenario_id",
                    "is_laundering",
                    "is_sar",
                    "alert_id",
                    "source",
                    "is_synthetic",
                    "related_event_ids",
                    "related_transaction_ids",
                    "description",
                    "has_transactional_consequence",
                    "background_real_laundering_count",
                ],
            },
        }

        if extra_metadata:
            metadata.update(extra_metadata)

        with open(meta_p, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return str(m_path), str(meta_p)

    @classmethod
    def load_model(
        cls,
        model_path: str,
        metadata_path: Optional[str] = None,
    ) -> "XGBoostDetector":
        """Load a saved XGBoost model and its feature metadata."""
        from pathlib import Path
        import json

        m_path = Path(model_path)
        meta_p = Path(metadata_path) if metadata_path else m_path.with_name(f"{m_path.stem}_metadata.json")

        if not m_path.exists():
            raise FileNotFoundError(f"Model file not found at: {m_path}")
        if not meta_p.exists():
            raise FileNotFoundError(f"Metadata file not found at: {meta_p}")

        with open(meta_p, "r", encoding="utf-8") as f:
            meta = json.load(f)

        params = meta.get("hyperparameters", {})
        instance = cls(
            n_estimators=params.get("n_estimators", 40),
            max_depth=params.get("max_depth", 3),
            learning_rate=params.get("learning_rate", 0.08),
            subsample=params.get("subsample", 0.8),
            colsample_bytree=params.get("colsample_bytree", 0.8),
            reg_alpha=params.get("reg_alpha", 0.5),
            reg_lambda=params.get("reg_lambda", 1.0),
            scale_pos_weight=params.get("scale_pos_weight", 1.0),
            random_state=params.get("random_state", 42),
        )

        instance.model.load_model(str(m_path))
        instance.feature_names_ = list(meta.get("feature_names", []))
        instance.is_fitted_ = True
        instance._explainer = shap.TreeExplainer(instance.model)
        return instance

    def predict_account(
        self,
        account_features: Any,
        account_id: str = "UNKNOWN_ACCOUNT",
        threshold: float = 0.5,
        top_k: int = 5,
        group_g_included: bool = True,
        group_x_included: bool = False,
    ) -> Dict[str, Any]:
        """Perform end-to-end inference on a single account feature vector.

        Returns:
            Dictionary containing:
                - account_id
                - suspicious_probability
                - predicted_class (1 or 0)
                - predicted_label ('suspicious' or 'legitimate')
                - threshold
                - top_shap_features (list of dicts)
                - explanation (human-readable string)
                - rule_result (standardized RuleResult object)
        """
        if isinstance(account_features, dict):
            feat_series = pd.Series(account_features)
        elif isinstance(account_features, pd.Series):
            feat_series = account_features.copy()
        elif isinstance(account_features, pd.DataFrame):
            feat_series = account_features.iloc[0].copy()
        else:
            raise TypeError("account_features must be a dict, pd.Series, or 1-row pd.DataFrame.")

        # Align features to model's exact schema
        aligned_series = feat_series.reindex(self.feature_names_).fillna(0.0)
        input_df = pd.DataFrame([aligned_series.values], columns=self.feature_names_)

        prob = float(self.predict_proba(input_df)[0])
        pred_class = int(prob >= threshold)
        pred_label = "suspicious" if pred_class == 1 else "legitimate"

        top_shap = self.explain_account(aligned_series, top_k=top_k)

        parts = [
            f"{item['feature']}={item['feature_value']:.2f} (SHAP {item['shap_value']:+.3f}, pushes {item['impact']})"
            for item in top_shap
            if abs(item["shap_value"]) > 0.001
        ]
        shap_summary = "; ".join(parts) if parts else "unspecified tree splits"

        explanation = (
            f"Account {account_id} classified as {pred_label.upper()} "
            f"with suspicious probability {prob:.4f} "
            f"({'EXCEEDS' if pred_class == 1 else 'below'} decision threshold {threshold:.4f}). "
            f"Top SHAP drivers: {shap_summary}."
        )

        rule_res = self.to_rule_result(
            account_id=account_id,
            features=aligned_series,
            probability=prob,
            threshold=threshold,
            group_g_included=group_g_included,
            group_x_included=group_x_included,
            top_k=top_k,
        )

        return {
            "account_id": account_id,
            "suspicious_probability": float(round(prob, 4)),
            "predicted_class": pred_class,
            "predicted_label": pred_label,
            "threshold": float(round(threshold, 4)),
            "top_shap_features": top_shap,
            "explanation": explanation,
            "rule_result": rule_res,
        }

    def to_rule_result(
        self,
        account_id: str,
        features: pd.Series,
        probability: float,
        threshold: float = 0.5,
        group_g_included: bool = False,
        group_x_included: bool = False,
        top_k: int = 4,
    ) -> RuleResult:
        """Convert XGBoost classification result into a standardized RuleResult with Evidence."""
        is_suspicious = bool(probability >= threshold)
        top_shap = self.explain_account(features, top_k=top_k)

        parts = [
            f"{item['feature']}={item['feature_value']:.2f} (SHAP {item['shap_value']:+.3f}, pushes {item['impact']})"
            for item in top_shap
            if abs(item["shap_value"]) > 0.001
        ]
        shap_summary = "; ".join(parts) if parts else "unspecified tree splits"

        explanation = (
            f"XGBoost suspicious probability {probability:.4f} "
            f"({'EXCEEDS' if is_suspicious else 'below'} decision threshold {threshold:.4f}). "
            f"Top SHAP drivers: {shap_summary}."
        )

        evidence_list = []
        for item in top_shap:
            evidence_list.append(
                Evidence(
                    source_dataset="data/entities / synthetic_hr / detection_rules",
                    record_type="AccountFeature",
                    record_id=account_id,
                    role="ml_discriminator",
                    details={
                        "feature": item["feature"],
                        "feature_value": item["feature_value"],
                        "shap_value": item["shap_value"],
                        "impact": item["impact"],
                    },
                )
            )

        metrics = {
            "suspicious_probability": float(round(probability, 4)),
            "threshold": float(round(threshold, 4)),
            "rule_engine_group_g_included": bool(group_g_included),
            "experimental_group_x_included": bool(group_x_included),
            "top_shap_features": top_shap,
        }

        return RuleResult(
            rule_id="ML.XGBOOST",
            rule_name="XGBoost Supervised AML Classifier",
            detection_category="ML_SUPERVISED",
            triggered=is_suspicious,
            entity_type="Account",
            entity_id=account_id,
            account_id=account_id,
            explanation=explanation,
            metrics=metrics,
            thresholds={"suspicious_probability": float(round(threshold, 4))},
            evidence=evidence_list,
            detection_timestamp=datetime.now(timezone.utc).isoformat(),
        )


def train_and_save_final_model(
    artifacts_dir: Optional[Any] = None,
) -> Tuple[str, str, XGBoostDetector]:
    """Train the final agreed XGBoost model on all 38 labeled accounts and save versioned artifacts."""
    from pathlib import Path
    from data.ml.features.feature_store import FeatureStore

    base_dir = Path(__file__).resolve().parent
    art_dir = Path(artifacts_dir) if artifacts_dir else base_dir / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)

    model_path = str(art_dir / "xgboost_v1.json")
    meta_path = str(art_dir / "xgboost_v1_metadata.json")

    fs = FeatureStore()
    X, y, meta = fs.get_xgboost_dataset(include_group_g=True, include_experimental_group_x=False)

    clf = XGBoostDetector(
        n_estimators=40,
        max_depth=3,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.5,
        reg_lambda=1.0,
        scale_pos_weight=1.0,
        random_state=42,
    )
    clf.fit(X, y)

    extra_meta = {
        "dataset_summary": {
            "total_accounts": len(X),
            "suspicious_accounts": int((y == 1).sum()),
            "legitimate_accounts": int((y == 0).sum()),
        },
        "feature_groups_included": ["A", "B", "C", "D", "E", "F", "G"],
    }
    saved_model, saved_meta = clf.save_model(model_path, meta_path, extra_metadata=extra_meta)
    return saved_model, saved_meta, clf


def load_xgboost_model(
    artifacts_dir: Optional[Any] = None,
    version: str = "v1",
) -> XGBoostDetector:
    """Load a versioned XGBoost model from the artifacts directory."""
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent
    art_dir = Path(artifacts_dir) if artifacts_dir else base_dir / "artifacts"

    model_path = art_dir / f"xgboost_{version}.json"
    meta_path = art_dir / f"xgboost_{version}_metadata.json"
    return XGBoostDetector.load_model(str(model_path), str(meta_path))
