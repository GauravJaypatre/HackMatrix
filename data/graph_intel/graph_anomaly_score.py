"""
graph_anomaly_score.py — Standalone Graph Anomaly Score Computation

Combines structural graph features (Part 1) and Node2Vec DBSCAN clustering (Part 2)
into a single, explainable graph_anomaly_score per account in the [0.0, 1.0] range.

Formula Design (Linear, Explainable, Evidence-Backed):
1. Circular Transfer Component (Weight: 0.35):
   - Participation in any detected simple cycle (length 2-6) in the SENT_TO subgraph.
   - Closed-loop fund cycles are a signature typology in money laundering.
2. Flow Centrality Component (Weight: 0.20):
   - Normalized betweenness centrality in the fund-routing network.
   - High betweenness identifies critical intermediary accounts / money mules routing flows.
3. Local Clustering Component (Weight: 0.15):
   - Clustering coefficient in the transaction network.
   - Elevated clustering flags localized circular cliques / dense transaction clusters.
4. Embedding Anomaly Component (Weight: 0.20):
   - DBSCAN outlier status (label -1): +0.20.
   - Isolated micro-cluster (cluster size <= 10): +0.10.
5. Flow Volume / Privilege Touch Component (Weight: 0.10):
   - Multiple connected internal employees (num_connected_employees >= 2): +0.05.
   - High transaction volume / velocity (total in + out transactions > 50): +0.05.

Outputs:
- data/graph_intel/graph_anomaly_scores.csv (columns: account_id, graph_anomaly_score, contributing_factors)
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Paths configuration
BASE_DIR = Path(__file__).resolve().parent.parent
INTEL_DIR = BASE_DIR / "graph_intel"
HR_DIR = BASE_DIR / "synthetic_hr"

STRUCTURAL_FILE = INTEL_DIR / "account_structural_features.csv"
CLUSTERS_FILE = INTEL_DIR / "account_clusters.csv"
SCENARIOS_FILE = HR_DIR / "labeled_scenarios.csv"
SCORES_FILE = INTEL_DIR / "graph_anomaly_scores.csv"


def compute_graph_anomaly_scores(
    structural_path: Path = STRUCTURAL_FILE,
    clusters_path: Path = CLUSTERS_FILE,
    output_path: Path = SCORES_FILE
) -> pd.DataFrame:
    """
    Computes explainable graph anomaly scores for all accounts.
    """
    print("=" * 75)
    print("COMPUTING STANDALONE GRAPH ANOMALY SCORES")
    print("=" * 75)
    
    struct_df = pd.read_csv(structural_path)
    clust_df = pd.read_csv(clusters_path)
    
    merged = pd.merge(struct_df, clust_df, on="account_id", how="inner")
    print(f"Loaded {len(merged):,} accounts for anomaly scoring")
    
    # Compute 90th percentile of positive betweenness centrality for normalization
    pos_bc = merged[merged['betweenness_centrality'] > 0]['betweenness_centrality']
    bc_scale = float(pos_bc.quantile(0.90)) if len(pos_bc) > 0 else 1e-5
    if bc_scale <= 0:
        bc_scale = 1e-5
        
    records = []
    for _, row in merged.iterrows():
        acc_id = str(row['account_id'])
        score = 0.0
        factors = []
        
        # 1. Circular Transfer Cycle (Weight: 0.35)
        if bool(row.get('is_on_any_cycle', False)):
            score += 0.35
            factors.append("participates in circular transfer cycle")
            
        # 2. Betweenness Centrality (Weight: 0.20)
        bc = float(row.get('betweenness_centrality', 0.0))
        if bc > 0:
            norm_bc = min(1.0, bc / bc_scale)
            score += norm_bc * 0.20
            if norm_bc >= 0.4:
                factors.append(f"high flow betweenness centrality (bc={bc:.2e})")
                
        # 3. Clustering Coefficient (Weight: 0.15)
        cc = float(row.get('clustering_coefficient', 0.0))
        if cc > 0:
            norm_cc = min(1.0, cc)
            score += norm_cc * 0.15
            if norm_cc >= 0.05:
                factors.append(f"elevated clustering coefficient (cc={cc:.3f})")
                
        # 4. DBSCAN Outlier / Small Cluster (Weight: 0.20)
        is_out = bool(row.get('is_outlier', False))
        c_sz = int(row.get('cluster_size', 1))
        if is_out:
            score += 0.20
            factors.append("topological outlier in Node2Vec space (DBSCAN outlier)")
        elif c_sz <= 10:
            score += 0.10
            factors.append(f"isolated micro-cluster (size={c_sz})")
            
        # 5. Connected Employees & Transaction Volume (Weight: 0.10)
        num_emps = int(row.get('num_connected_employees', 0))
        if num_emps >= 2:
            score += 0.05
            factors.append(f"multiple connected employees ({num_emps} internal contacts)")
            
        in_d = int(row.get('in_degree', 0))
        out_d = int(row.get('out_degree', 0))
        if (in_d + out_d) > 50:
            score += 0.05
            factors.append(f"high transaction volume (in={in_d}, out={out_d})")
            
        score = min(1.0, round(score, 4))
        explanation = "; ".join(factors) if factors else "baseline structural profile; no graph anomalies detected"
        
        records.append({
            "account_id": acc_id,
            "graph_anomaly_score": score,
            "contributing_factors": explanation
        })
        
    scores_df = pd.DataFrame(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scores_df.to_csv(output_path, index=False)
    print(f"\n[OUTPUT] Saved graph anomaly scores to {output_path}")
    return scores_df


def evaluate_scenarios(
    scores_df: pd.DataFrame,
    scenarios_path: Path = SCENARIOS_FILE
) -> pd.DataFrame:
    """
    Evaluates and prints scores for all 38 scenarios (suspicious vs legitimate).
    """
    scenarios_df = pd.read_csv(scenarios_path)
    score_map = dict(zip(scores_df['account_id'], scores_df['graph_anomaly_score']))
    factors_map = dict(zip(scores_df['account_id'], scores_df['contributing_factors']))
    
    rows = []
    for _, sc in scenarios_df.iterrows():
        sid = str(sc['scenario_id'])
        stype = str(sc['scenario_type'])
        acc_str = str(sc['account_id'])
        accs = [a.strip() for a in acc_str.split(';') if a.strip()]
        
        # Primary scenario account score
        primary_acc = accs[0]
        acc_scores = [score_map.get(a, 0.0) for a in accs]
        max_score = max(acc_scores) if acc_scores else 0.0
        
        # Find which account had the max score
        best_acc = accs[acc_scores.index(max_score)] if acc_scores else primary_acc
        factors = factors_map.get(best_acc, "no data")
        
        rows.append({
            "scenario_id": sid,
            "scenario_type": stype,
            "account_id": best_acc if len(accs) > 1 else primary_acc,
            "graph_anomaly_score": max_score,
            "contributing_factors": factors
        })
        
    eval_df = pd.DataFrame(rows)
    
    print("\n" + "=" * 75)
    print("ALL 38 SCENARIOS GRAPH ANOMALY SCORES EVALUATION")
    print("=" * 75)
    print(eval_df.to_string(index=False))
    
    # Group statistics
    susp_scores = eval_df[eval_df['scenario_type'] == 'suspicious']['graph_anomaly_score']
    legit_scores = eval_df[eval_df['scenario_type'] == 'legitimate']['graph_anomaly_score']
    
    print("\n" + "=" * 75)
    print("SUMMARY COMPARISON: SUSPICIOUS VS LEGITIMATE SCENARIOS")
    print("=" * 75)
    print(f"SUSPICIOUS Scenarios ({len(susp_scores)}):")
    print(f"  Mean Score:   {susp_scores.mean():.4f}")
    print(f"  Median Score: {susp_scores.median():.4f}")
    print(f"  Min / Max:    {susp_scores.min():.4f} / {susp_scores.max():.4f}")
    print(f"  Scores >= 0.20: {(susp_scores >= 0.20).sum()}/{len(susp_scores)} ({(susp_scores >= 0.20).mean()*100:.1f}%)")
    
    print(f"\nLEGITIMATE Scenarios ({len(legit_scores)}):")
    print(f"  Mean Score:   {legit_scores.mean():.4f}")
    print(f"  Median Score: {legit_scores.median():.4f}")
    print(f"  Min / Max:    {legit_scores.min():.4f} / {legit_scores.max():.4f}")
    print(f"  Scores >= 0.20: {(legit_scores >= 0.20).sum()}/{len(legit_scores)} ({(legit_scores >= 0.20).mean()*100:.1f}%)")
    
    print("\nKEY VALIDATION PAIR COMPARISON:")
    s19_row = eval_df[eval_df['scenario_id'] == 'S19'].iloc[0]
    l19_row = eval_df[eval_df['scenario_id'] == 'L19'].iloc[0]
    print(f"  S19 (Circular Transfer Loop): Score = {s19_row['graph_anomaly_score']:.4f} | {s19_row['contributing_factors']}")
    print(f"  L19 (Legitimate Multi-Hop):   Score = {l19_row['graph_anomaly_score']:.4f} | {l19_row['contributing_factors']}")
    print("=" * 75)
    
    return eval_df


if __name__ == "__main__":
    scores_df = compute_graph_anomaly_scores()
    evaluate_scenarios(scores_df)
