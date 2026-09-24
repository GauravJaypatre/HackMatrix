"""Evaluation pipeline and ablation reporting for Isolation Forest anomaly detection."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from data.ml.features.feature_store import FeatureStore
from data.ml.models.isolation_forest import IsolationForestDetector


@dataclass
class IsolationForestEvaluationResult:
    """Structured evaluation results for an Isolation Forest run."""

    group_x_included: bool
    feature_matrix_shape: Tuple[int, int]
    n_train_background: int
    n_eval_total: int
    n_eval_suspicious: int
    n_eval_legitimate: int
    missing_values_count: int
    feature_names: List[str]
    roc_auc: float
    average_precision: float
    background_threshold: float
    suspicious_stats: Dict[str, float]
    legitimate_stats: Dict[str, float]
    background_stats: Dict[str, float]
    suspicious_above_threshold: int
    legitimate_above_threshold: int
    top_anomalous_accounts: List[Dict[str, Any]]
    s19_result: Dict[str, Any]
    l19_result: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _calc_stats(scores: pd.Series) -> Dict[str, float]:
    return {
        "mean": float(round(scores.mean(), 4)),
        "std": float(round(scores.std(), 4)),
        "median": float(round(scores.median(), 4)),
        "min": float(round(scores.min(), 4)),
        "max": float(round(scores.max(), 4)),
    }


def run_isolation_forest_evaluation(
    include_experimental_group_x: bool = False,
    contamination: float = 0.05,
    n_estimators: int = 200,
    random_state: int = 42,
    feature_store: FeatureStore = None,
) -> IsolationForestEvaluationResult:
    """Run full unsupervised training on 1,846 background accounts and evaluate on 38 scenario accounts."""
    if feature_store is None:
        feature_store = FeatureStore()

    X_bg, X_ev, y_ev, meta = feature_store.get_dataset_splits(
        include_experimental_group_x=include_experimental_group_x
    )

    full_matrix = feature_store.get_feature_matrix(
        include_experimental_group_x=include_experimental_group_x
    )
    missing_vals = int(full_matrix.isna().sum().sum())
    feat_names = list(full_matrix.columns)

    detector = IsolationForestDetector(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
    )
    detector.fit(X_bg)

    ev_scores = detector.score_accounts(X_ev)
    bg_scores = pd.Series(detector.bg_scores_, index=X_bg.index)

    auc = float(round(roc_auc_score(y_ev, ev_scores), 4))
    ap = float(round(average_precision_score(y_ev, ev_scores), 4))

    susp_scores = ev_scores[y_ev == 1]
    legit_scores = ev_scores[y_ev == 0]

    susp_stats = _calc_stats(susp_scores)
    legit_stats = _calc_stats(legit_scores)
    bg_stats = _calc_stats(bg_scores)

    threshold = detector.threshold_
    susp_above = int((susp_scores >= threshold).sum())
    legit_above = int((legit_scores >= threshold).sum())

    # Build top anomalous table
    eval_df = meta.copy()
    eval_df["anomaly_score"] = ev_scores
    eval_df = eval_df.sort_values(by="anomaly_score", ascending=False)

    top_anomalies: List[Dict[str, Any]] = []
    for rank, (acc_id, row) in enumerate(eval_df.iterrows(), 1):
        top_anomalies.append({
            "rank": rank,
            "account_id": acc_id,
            "scenario_id": row["scenario_id"],
            "scenario_type": row["scenario_type"],
            "anomaly_score": float(round(row["anomaly_score"], 4)),
            "above_threshold": bool(row["anomaly_score"] >= threshold),
        })

    # Holdouts: S19 and L19
    s19_meta = eval_df[eval_df["scenario_id"] == "S19"].iloc[0]
    l19_meta = eval_df[eval_df["scenario_id"] == "L19"].iloc[0]

    s19_rank = int(eval_df.index.get_loc(s19_meta.name)) + 1
    l19_rank = int(eval_df.index.get_loc(l19_meta.name)) + 1

    s19_expl = detector.explain_account(X_ev.loc[s19_meta.name], top_k=4)
    l19_expl = detector.explain_account(X_ev.loc[l19_meta.name], top_k=4)

    s19_result = {
        "scenario_id": "S19",
        "account_id": s19_meta.name,
        "scenario_type": "suspicious",
        "anomaly_score": float(round(s19_meta["anomaly_score"], 4)),
        "rank": s19_rank,
        "above_threshold": bool(s19_meta["anomaly_score"] >= threshold),
        "top_features": s19_expl,
    }

    l19_result = {
        "scenario_id": "L19",
        "account_id": l19_meta.name,
        "scenario_type": "legitimate",
        "anomaly_score": float(round(l19_meta["anomaly_score"], 4)),
        "rank": l19_rank,
        "above_threshold": bool(l19_meta["anomaly_score"] >= threshold),
        "top_features": l19_expl,
    }

    return IsolationForestEvaluationResult(
        group_x_included=include_experimental_group_x,
        feature_matrix_shape=(len(full_matrix), len(full_matrix.columns)),
        n_train_background=len(X_bg),
        n_eval_total=len(X_ev),
        n_eval_suspicious=len(susp_scores),
        n_eval_legitimate=len(legit_scores),
        missing_values_count=missing_vals,
        feature_names=feat_names,
        roc_auc=auc,
        average_precision=ap,
        background_threshold=float(round(threshold, 4)),
        suspicious_stats=susp_stats,
        legitimate_stats=legit_stats,
        background_stats=bg_stats,
        suspicious_above_threshold=susp_above,
        legitimate_above_threshold=legit_above,
        top_anomalous_accounts=top_anomalies[:15],
        s19_result=s19_result,
        l19_result=l19_result,
    )


def print_evaluation_summary() -> Tuple[IsolationForestEvaluationResult, IsolationForestEvaluationResult]:
    """Execute both Group X OFF and ON, printing comprehensive report."""
    fs = FeatureStore()

    print("================================================================================")
    print("           HACKMATRIX — PHASE 1: ISOLATION FOREST EVALUATION & ABLATION         ")
    print("================================================================================")

    res_off = run_isolation_forest_evaluation(include_experimental_group_x=False, feature_store=fs)
    res_on = run_isolation_forest_evaluation(include_experimental_group_x=True, feature_store=fs)

    for res in [res_off, res_on]:
        tag = "GROUP X (INJECTED TX) = ON [EXPERIMENTAL]" if res.group_x_included else "GROUP X = OFF [BASELINE APPROVED GROUPS A-E]"
        print(f"\n--- {tag} ---")
        print(f"Feature matrix shape:        {res.feature_matrix_shape} (Accounts x Features)")
        print(f"Training accounts:           {res.n_train_background} (Unlabeled background ONLY)")
        print(f"Evaluation accounts:         {res.n_eval_total} ({res.n_eval_suspicious} suspicious + {res.n_eval_legitimate} legitimate)")
        print(f"Missing values count:        {res.missing_values_count} (Handled via 0-fill / imputation)")
        print(f"Background threshold (p95):  {res.background_threshold:.4f}")
        print(f"ROC-AUC (Susp vs Legit):     {res.roc_auc:.4f}")
        print(f"Average Precision (PR-AUC):  {res.average_precision:.4f}")
        print("\nScore Distributions:")
        print(f"  Suspicious (n=19):  mean={res.suspicious_stats['mean']:.4f}, median={res.suspicious_stats['median']:.4f}, std={res.suspicious_stats['std']:.4f}, range=[{res.suspicious_stats['min']:.4f}, {res.suspicious_stats['max']:.4f}]")
        print(f"  Legitimate (n=19):  mean={res.legitimate_stats['mean']:.4f}, median={res.legitimate_stats['median']:.4f}, std={res.legitimate_stats['std']:.4f}, range=[{res.legitimate_stats['min']:.4f}, {res.legitimate_stats['max']:.4f}]")
        print(f"  Background (n=1846):mean={res.background_stats['mean']:.4f}, median={res.background_stats['median']:.4f}, std={res.background_stats['std']:.4f}, range=[{res.background_stats['min']:.4f}, {res.background_stats['max']:.4f}]")
        print(f"  Suspicious > threshold: {res.suspicious_above_threshold} / {res.n_eval_suspicious} ({res.suspicious_above_threshold/res.n_eval_suspicious*100:.1f}%)")
        print(f"  Legitimate > threshold: {res.legitimate_above_threshold} / {res.n_eval_legitimate} ({res.legitimate_above_threshold/res.n_eval_legitimate*100:.1f}%)")

        print("\nHoldout Scenarios Evaluation:")
        s19 = res.s19_result
        l19 = res.l19_result
        print(f"  S19 (Circular Transfer holdout): Score={s19['anomaly_score']:.4f}, Rank={s19['rank']}/38, Above Threshold={s19['above_threshold']}")
        print(f"      Top contributing features: {', '.join([f['feature'] + '=' + str(f['value']) for f in s19['top_features'][:3]])}")
        print(f"  L19 (Linear Multi-hop holdout):  Score={l19['anomaly_score']:.4f}, Rank={l19['rank']}/38, Above Threshold={l19['above_threshold']}")
        print(f"      Top contributing features: {', '.join([f['feature'] + '=' + str(f['value']) for f in l19['top_features'][:3]])}")

        print("\nTop 10 Most Anomalous Scenario Accounts:")
        print(f"  {'Rank':<5} {'Scenario':<10} {'Type':<12} {'Account ID':<15} {'Score':<8} {'Exceeds Threshold':<18}")
        for row in res.top_anomalous_accounts[:10]:
            print(f"  {row['rank']:<5} {row['scenario_id']:<10} {row['scenario_type']:<12} {row['account_id']:<15} {row['anomaly_score']:<8.4f} {str(row['above_threshold']):<18}")

    print("\n================================================================================")
    print("                       GROUP X ABLATION COMPARISON SUMMARY                      ")
    print("================================================================================")
    delta_auc = res_on.roc_auc - res_off.roc_auc
    delta_ap = res_on.average_precision - res_off.average_precision
    print(f"  Metric              Group X OFF        Group X ON         Delta (ON - OFF)")
    print(f"  ROC-AUC:            {res_off.roc_auc:<18.4f} {res_on.roc_auc:<18.4f} {delta_auc:+.4f}")
    print(f"  Average Precision:  {res_off.average_precision:<18.4f} {res_on.average_precision:<18.4f} {delta_ap:+.4f}")
    print(f"  Features Count:     {len(res_off.feature_names):<18} {len(res_on.feature_names):<18} +{len(res_on.feature_names)-len(res_off.feature_names)}")
    print(f"  S19 Score:          {res_off.s19_result['anomaly_score']:<18.4f} {res_on.s19_result['anomaly_score']:<18.4f} {res_on.s19_result['anomaly_score']-res_off.s19_result['anomaly_score']:+.4f}")
    print(f"  L19 Score:          {res_off.l19_result['anomaly_score']:<18.4f} {res_on.l19_result['anomaly_score']:<18.4f} {res_on.l19_result['anomaly_score']-res_off.l19_result['anomaly_score']:+.4f}")
    print("================================================================================")

    return res_off, res_on


if __name__ == "__main__":
    print_evaluation_summary()
