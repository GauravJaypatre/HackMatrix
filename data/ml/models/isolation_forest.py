"""Isolation Forest anomaly detection model for HackMatrix account-level detection."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from data.detection.models import Evidence, RuleResult


class IsolationForestDetector:
    """Isolation Forest unsupervised anomaly detector trained exclusively on background accounts."""

    def __init__(
        self,
        n_estimators: int = 200,
        max_samples: int = 256,
        contamination: float = 0.05,
        random_state: int = 42,
    ):
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.random_state = random_state

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )

        self.feature_names_: List[str] = []
        self.baseline_medians_: pd.Series = pd.Series(dtype=float)
        self.baseline_iqrs_: pd.Series = pd.Series(dtype=float)
        self.baseline_stds_: pd.Series = pd.Series(dtype=float)
        self.bg_scores_: np.ndarray = np.array([])
        self.threshold_: float = 0.5
        self.is_fitted_: bool = False

    def fit(self, X_train: pd.DataFrame) -> "IsolationForestDetector":
        """Train Isolation Forest on background accounts."""
        if not isinstance(X_train, pd.DataFrame):
            raise TypeError("X_train must be a pandas DataFrame with account_id as index.")

        self.feature_names_ = list(X_train.columns)
        self.model.fit(X_train.values)

        # Compute and record background distribution baselines for explainability
        self.baseline_medians_ = X_train.median(axis=0)
        q75 = X_train.quantile(0.75, axis=0)
        q25 = X_train.quantile(0.25, axis=0)
        self.baseline_iqrs_ = (q75 - q25).replace(0.0, 1.0)
        self.baseline_stds_ = X_train.std(axis=0).replace(0.0, 1.0)

        # Background anomaly scores
        # In scikit-learn, score_samples returns -s(x), so negative of that is Liu et al.'s s(x)
        self.bg_scores_ = -self.model.score_samples(X_train.values)

        # Threshold defined at (1 - contamination) percentile of background scores
        self.threshold_ = float(np.percentile(self.bg_scores_, (1.0 - self.contamination) * 100))
        self.is_fitted_ = True
        return self

    def score_accounts(self, X: pd.DataFrame) -> pd.Series:
        """Compute Liu et al. anomaly scores for accounts. Higher = more anomalous."""
        if not self.is_fitted_:
            raise RuntimeError("Detector must be fitted before scoring accounts.")
        raw_scores = -self.model.score_samples(X[self.feature_names_].values)
        return pd.Series(raw_scores, index=X.index, name="anomaly_score")

    def explain_account(
        self,
        account_series: pd.Series,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Calculate top contributing features for an anomalous account.

        Uses marginal attribution: measures the reduction in anomaly score when
        each individual feature is replaced by its background training median.
        """
        if not self.is_fitted_:
            raise RuntimeError("Detector must be fitted before explaining.")

        sample_vec = account_series[self.feature_names_].values.astype(float).reshape(1, -1)
        base_score = float(-self.model.score_samples(sample_vec)[0])

        contributions = []
        n_features = len(self.feature_names_)

        # Vectorized perturbation matrix: replace each feature with median
        pert_matrix = np.repeat(sample_vec, n_features, axis=0)
        for i, fname in enumerate(self.feature_names_):
            pert_matrix[i, i] = self.baseline_medians_[fname]

        pert_scores = -self.model.score_samples(pert_matrix)
        deltas = base_score - pert_scores

        for i, fname in enumerate(self.feature_names_):
            val = float(sample_vec[0, i])
            med = float(self.baseline_medians_[fname])
            iqr = float(self.baseline_iqrs_[fname])
            delta = float(deltas[i])
            z_dev = (val - med) / iqr

            contributions.append({
                "feature": fname,
                "score_delta": round(delta, 5),
                "value": round(val, 4),
                "baseline_median": round(med, 4),
                "iqr_deviation": round(z_dev, 2),
                "direction": "elevated" if val > med else ("depressed" if val < med else "normal"),
            })

        # Rank by score delta (highest reduction in anomaly when normalized), break ties by absolute iqr deviation
        ranked = sorted(
            contributions,
            key=lambda c: (c["score_delta"], abs(c["iqr_deviation"])),
            reverse=True,
        )
        return ranked[:top_k]

    def to_rule_result(
        self,
        account_id: str,
        features: pd.Series,
        anomaly_score: float,
        group_x_included: bool = False,
        top_k: int = 4,
    ) -> RuleResult:
        """Convert anomaly detection result into a standardized RuleResult with Evidence."""
        is_anomaly = bool(anomaly_score >= self.threshold_)
        top_features = self.explain_account(features, top_k=top_k)

        feat_str_parts = [
            f"{f['feature']}={f['value']:.2f} ({f['direction']}, median {f['baseline_median']:.2f})"
            for f in top_features
            if f["direction"] != "normal"
        ]
        top_str = "; ".join(feat_str_parts) if feat_str_parts else "unspecified feature interaction"

        explanation = (
            f"Isolation Forest anomaly score {anomaly_score:.4f} "
            f"({'EXCEEDS' if is_anomaly else 'below'} background threshold {self.threshold_:.4f}). "
            f"Top contributing features: {top_str}."
        )

        evidence_list = []
        for feat in top_features:
            evidence_list.append(
                Evidence(
                    source_dataset="data/entities/accounts.csv / in_scope_real_transactions.csv",
                    record_type="AccountFeature",
                    record_id=account_id,
                    role="anomaly_contributor",
                    details={
                        "feature": feat["feature"],
                        "value": feat["value"],
                        "baseline_median": feat["baseline_median"],
                        "score_delta": feat["score_delta"],
                        "direction": feat["direction"],
                    },
                )
            )

        metrics = {
            "anomaly_score": float(round(anomaly_score, 4)),
            "threshold": float(round(self.threshold_, 4)),
            "contamination": float(self.contamination),
            "experimental_group_x_included": bool(group_x_included),
            "top_contributing_features": top_features,
        }

        return RuleResult(
            rule_id="ML.ISOLATION_FOREST",
            rule_name="Isolation Forest Anomaly Detection",
            detection_category="ML_ANOMALY",
            triggered=is_anomaly,
            entity_type="Account",
            entity_id=account_id,
            account_id=account_id,
            explanation=explanation,
            metrics=metrics,
            thresholds={"anomaly_score": float(round(self.threshold_, 4))},
            evidence=evidence_list,
            detection_timestamp=datetime.now(timezone.utc).isoformat(),
        )
