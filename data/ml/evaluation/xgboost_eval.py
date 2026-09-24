"""LOSO cross-validation and evaluation pipeline for XGBoost AML classifier."""

from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from data.ml.features.feature_store import FeatureStore
from data.ml.models.xgboost_classifier import XGBoostDetector


@dataclass
class XGBoostExperimentResult:
    """Evaluation metrics for a single XGBoost configuration under LOSO-CV."""

    name: str
    group_g_included: bool
    group_x_included: bool
    feature_count: int
    feature_names: List[str]
    roc_auc_mean: float
    roc_auc_std: float
    precision_mean: float
    precision_std: float
    recall_mean: float
    recall_std: float
    f1_mean: float
    f1_std: float
    accuracy: float
    s19_result: Dict[str, Any]
    l19_result: Dict[str, Any]
    fixed_holdout_s19_prob: float
    fixed_holdout_l19_prob: float
    top_shap_features: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _jackknife_std(
    metric_fn: Callable[[np.ndarray, np.ndarray, np.ndarray], float],
    probs: np.ndarray,
    preds: np.ndarray,
    y_true: np.ndarray,
) -> float:
    """Calculate jackknife standard error across leave-one-out folds."""
    n = len(y_true)
    sub_scores = []
    for i in range(n):
        mask = [j for j in range(n) if j != i]
        sub_scores.append(metric_fn(y_true[mask], probs[mask], preds[mask]))
    sub_scores_arr = np.array(sub_scores)
    std_val = float(np.sqrt((n - 1) * np.var(sub_scores_arr, ddof=0)))
    return std_val


def evaluate_loso_xgboost(
    include_group_g: bool = False,
    include_experimental_group_x: bool = False,
    feature_store: Optional[FeatureStore] = None,
    name: Optional[str] = None,
) -> XGBoostExperimentResult:
    """Run full Leave-One-Scenario-Out cross-validation across all 38 labeled accounts."""
    if feature_store is None:
        feature_store = FeatureStore()

    X_labeled, y_labeled, scenario_meta = feature_store.get_xgboost_dataset(
        include_group_g=include_group_g,
        include_experimental_group_x=include_experimental_group_x,
    )

    exp_name = name or (
        f"Group G {'ON' if include_group_g else 'OFF'} | "
        f"Group X {'ON' if include_experimental_group_x else 'OFF'}"
    )

    y = y_labeled.values.astype(int)
    n = len(y)
    oof_probs = np.zeros(n, dtype=float)
    oof_preds = np.zeros(n, dtype=int)

    # LOSO-CV Loop: 38 folds
    for i in range(n):
        train_idx = [j for j in range(n) if j != i]
        test_idx = [i]

        clf = XGBoostDetector(
            n_estimators=40,
            max_depth=3,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.5,
            reg_lambda=1.0,
            random_state=42,
        )
        clf.fit(X_labeled.iloc[train_idx], y_labeled.iloc[train_idx])
        prob = clf.predict_proba(X_labeled.iloc[test_idx])[0]
        oof_probs[i] = prob
        oof_preds[i] = 1 if prob >= 0.5 else 0

    # Primary OOF pooled point estimates
    auc_val = float(roc_auc_score(y, oof_probs))
    prec_val = float(precision_score(y, oof_preds, zero_division=0))
    rec_val = float(recall_score(y, oof_preds))
    f1_val = float(f1_score(y, oof_preds))
    acc_val = float(accuracy_score(y, oof_preds))

    # Fold-level jackknife standard deviations
    auc_std = _jackknife_std(lambda yt, pb, pr: roc_auc_score(yt, pb), oof_probs, oof_preds, y)
    prec_std = _jackknife_std(lambda yt, pb, pr: precision_score(yt, pr, zero_division=0), oof_probs, oof_preds, y)
    rec_std = _jackknife_std(lambda yt, pb, pr: recall_score(yt, pr), oof_probs, oof_preds, y)
    f1_std = _jackknife_std(lambda yt, pb, pr: f1_score(yt, pr), oof_probs, oof_preds, y)

    # Locate S19 and L19 in OOF
    acc_list = list(X_labeled.index)
    s19_acc = scenario_meta[scenario_meta["scenario_id"] == "S19"].index[0]
    l19_acc = scenario_meta[scenario_meta["scenario_id"] == "L19"].index[0]

    s19_idx = acc_list.index(s19_acc)
    l19_idx = acc_list.index(l19_acc)

    s19_res = {
        "scenario_id": "S19",
        "account_id": s19_acc,
        "true_label": int(y[s19_idx]),
        "predicted_prob": float(round(oof_probs[s19_idx], 4)),
        "predicted_class": int(oof_preds[s19_idx]),
        "correct": bool(oof_preds[s19_idx] == y[s19_idx]),
    }

    l19_res = {
        "scenario_id": "L19",
        "account_id": l19_acc,
        "true_label": int(y[l19_idx]),
        "predicted_prob": float(round(oof_probs[l19_idx], 4)),
        "predicted_class": int(oof_preds[l19_idx]),
        "correct": bool(oof_preds[l19_idx] == y[l19_idx]),
    }

    # Fixed Final Holdout: train on 36 accounts, evaluate on S19 + L19
    holdout_accs = {s19_acc, l19_acc}
    train_mask = [acc not in holdout_accs for acc in X_labeled.index]
    fixed_clf = XGBoostDetector(
        n_estimators=40,
        max_depth=3,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.5,
        reg_lambda=1.0,
        random_state=42,
    )
    fixed_clf.fit(X_labeled[train_mask], y_labeled[train_mask])
    holdout_probs = fixed_clf.predict_proba(X_labeled.loc[[s19_acc, l19_acc]])
    fixed_s19_prob = float(round(holdout_probs[0], 4))
    fixed_l19_prob = float(round(holdout_probs[1], 4))

    # Global SHAP feature importances across all 38 accounts
    full_clf = XGBoostDetector(
        n_estimators=40,
        max_depth=3,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.5,
        reg_lambda=1.0,
        random_state=42,
    )
    full_clf.fit(X_labeled, y_labeled)
    top_shap = full_clf.get_global_feature_importance(X_labeled, top_k=10)

    return XGBoostExperimentResult(
        name=exp_name,
        group_g_included=include_group_g,
        group_x_included=include_experimental_group_x,
        feature_count=X_labeled.shape[1],
        feature_names=list(X_labeled.columns),
        roc_auc_mean=float(round(auc_val, 4)),
        roc_auc_std=float(round(auc_std, 4)),
        precision_mean=float(round(prec_val, 4)),
        precision_std=float(round(prec_std, 4)),
        recall_mean=float(round(rec_val, 4)),
        recall_std=float(round(rec_std, 4)),
        f1_mean=float(round(f1_val, 4)),
        f1_std=float(round(f1_std, 4)),
        accuracy=float(round(acc_val, 4)),
        s19_result=s19_res,
        l19_result=l19_res,
        fixed_holdout_s19_prob=fixed_s19_prob,
        fixed_holdout_l19_prob=fixed_l19_prob,
        top_shap_features=top_shap,
    )


def run_all_xgboost_experiments() -> List[XGBoostExperimentResult]:
    """Execute all 4 mandatory XGBoost experiments with full ablation comparison."""
    fs = FeatureStore()
    experiments = [
        ("1. Rule Engine Flags OFF | Group X OFF", False, False),
        ("2. Rule Engine Flags ON  | Group X OFF", True, False),
        ("3. Rule Engine Flags OFF | Group X ON ", False, True),
        ("4. Rule Engine Flags ON  | Group X ON ", True, True),
    ]

    results: List[XGBoostExperimentResult] = []

    print("================================================================================")
    print("              HACKMATRIX — PHASE 2: XGBOOST SUPERVISED DETECTION                ")
    print("================================================================================")
    print("Note: Results are prototype-level evaluated via LOSO-CV on 38 labeled accounts.")
    print("Expect moderate variance due to sample size (n=38: 19 suspicious, 19 legitimate).")
    print("================================================================================")

    for name, use_g, use_x in experiments:
        res = evaluate_loso_xgboost(
            include_group_g=use_g,
            include_experimental_group_x=use_x,
            feature_store=fs,
            name=name,
        )
        results.append(res)

        print(f"\n--- {res.name} ---")
        print(f"Features:            {res.feature_count} features")
        print(f"ROC-AUC:             {res.roc_auc_mean:.4f} ± {res.roc_auc_std:.4f}")
        print(f"Precision:           {res.precision_mean:.4f} ± {res.precision_std:.4f}")
        print(f"Recall:              {res.recall_mean:.4f} ± {res.recall_std:.4f}")
        print(f"F1-Score:            {res.f1_mean:.4f} ± {res.f1_std:.4f}")
        print(f"Accuracy:            {res.accuracy:.4f}")
        print(f"S19 LOSO Prediction: Prob={res.s19_result['predicted_prob']:.4f} (True=1, Pred={res.s19_result['predicted_class']}) -> {'CORRECT' if res.s19_result['correct'] else 'WRONG'}")
        print(f"L19 LOSO Prediction: Prob={res.l19_result['predicted_prob']:.4f} (True=0, Pred={res.l19_result['predicted_class']}) -> {'CORRECT' if res.l19_result['correct'] else 'WRONG'}")
        print(f"Fixed Holdout (S19): Prob={res.fixed_holdout_s19_prob:.4f} (Trained on 36 accounts)")
        print(f"Fixed Holdout (L19): Prob={res.fixed_holdout_l19_prob:.4f} (Trained on 36 accounts)")
        print("Top 5 SHAP Features:")
        for item in res.top_shap_features[:5]:
            print(f"   * {item['feature']:<30}: mean |SHAP| = {item['mean_abs_shap']:.4f}")

    print("\n================================================================================")
    print("                         SUMMARY COMPARISON TABLE                               ")
    print("================================================================================")
    print(f"{'Experiment':<38} {'Feats':<6} {'ROC-AUC':<16} {'Precision':<16} {'Recall':<16} {'F1':<16}")
    print("-" * 108)
    for r in results:
        auc_str = f"{r.roc_auc_mean:.4f}±{r.roc_auc_std:.4f}"
        pr_str = f"{r.precision_mean:.4f}±{r.precision_std:.4f}"
        rec_str = f"{r.recall_mean:.4f}±{r.recall_std:.4f}"
        f1_str = f"{r.f1_mean:.4f}±{r.f1_std:.4f}"
        print(f"{r.name:<38} {r.feature_count:<6} {auc_str:<16} {pr_str:<16} {rec_str:<16} {f1_str:<16}")
    print("================================================================================")

    return results


if __name__ == "__main__":
    run_all_xgboost_experiments()
