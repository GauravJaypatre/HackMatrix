"""
evidence_schema.py — Evidence Object Schema & Builder for Alert Investigations

Defines the target JSON data contract for explainable, evidence-backed alerts
connecting employees, access rights, accounts, customers, and transactions.

Target Schema:
{
  "alert_id": str,
  "account_ids": list[str],
  "employee_id": str | None,
  "risk_tier": str,          # PLACEHOLDER until risk fusion exists
  "risk_score": float,       # PLACEHOLDER until risk fusion exists
  "signals": {
      "rule_engine": {},     # PLACEHOLDER - will be populated from Member 2
      "ml_model": {},        # PLACEHOLDER - will be populated from Member 2  
      "graph_intelligence": {}   # POPULATE THIS NOW from Part 3's output
  },
  "evidence_subgraph": {"nodes": [], "edges": []},
  "timeline": [],
  "explanation": str
}

Key Implementation Details:
- Prefixes node IDs by entity type in evidence_subgraph:
  "ACCT_<id>" for Account nodes, "CUST_<id>" for Customer nodes (eliminating
  the 1:1 ID string collision present in data/graph/nodes.csv), with "raw_id"
  preserved for database lookups.
- Connects all cycle and scenario transactions (including intermediate hops
  such as SYN_S19_002) in both evidence_subgraph and timeline.
- Timeline includes chronological scenario events labeled with category
  ("scenario_evidence" vs optional "background_context").
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import networkx as nx
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Path configuration
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR.parent
PROJECT_ROOT = DATA_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(DATA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_DIR))

GRAPH_DIR = DATA_DIR / "graph"
INTEL_DIR = DATA_DIR / "graph_intel"
ENTITIES_DIR = DATA_DIR / "entities"
HR_DIR = DATA_DIR / "synthetic_hr"

# Import Member 1 query utility
try:
    from data.graph.get_account_history import get_account_history
except ImportError:
    from graph.get_account_history import get_account_history

# Import Risk Fusion utility
try:
    from data.risk_fusion.fuse_signals import fuse_account_risk
except ImportError:
    from risk_fusion.fuse_signals import fuse_account_risk


def _load_graph_data():
    """Load structural features, clusters, anomaly scores, and graph tables."""
    scores_path = INTEL_DIR / "graph_anomaly_scores.csv"
    struct_path = INTEL_DIR / "account_structural_features.csv"
    clusters_path = INTEL_DIR / "account_clusters.csv"
    nodes_path = GRAPH_DIR / "nodes.csv"
    edges_path = GRAPH_DIR / "edges.csv"
    inj_path = HR_DIR / "injected_transactions.csv"

    scores_df = pd.read_csv(scores_path) if scores_path.exists() else pd.DataFrame()
    struct_df = pd.read_csv(struct_path) if struct_path.exists() else pd.DataFrame()
    clusters_df = pd.read_csv(clusters_path) if clusters_path.exists() else pd.DataFrame()
    nodes_df = pd.read_csv(nodes_path) if nodes_path.exists() else pd.DataFrame()
    edges_df = pd.read_csv(edges_path) if edges_path.exists() else pd.DataFrame()
    inj_df = pd.read_csv(inj_path) if inj_path.exists() else pd.DataFrame()

    return {
        "scores": scores_df,
        "struct": struct_df,
        "clusters": clusters_df,
        "nodes": nodes_df,
        "edges": edges_df,
        "injected_txns": inj_df
    }


def build_evidence_object(
    account_id: str,
    include_background_context: bool = False
) -> Dict[str, Any]:
    """
    Constructs a complete, evidence-backed alert object for the specified account.
    
    Populates:
    - alert_id: Unique alert identifier
    - account_ids: List of linked accounts in the suspicious flow/cycle
    - employee_id: Connected employee ID from get_account_history
    - risk_tier: Calibrated operational tier ("Low", "Medium", "High", "Critical")
    - risk_score: Calibrated composite multi-signal risk score [0, 1]
    - signals.rule_engine: Fired deterministic rules with supporting evidence
    - signals.ml_model: XGBoost probability, decision threshold, SHAP top drivers,
      and Isolation Forest anomaly scores
    - signals.graph_intelligence: Full topological metrics, anomaly score, and factors
    - evidence_subgraph: Local investigation subgraph with typed, collision-free node IDs
      ("ACCT_<id>", "CUST_<id>", "EMP_<id>", "SYN_<id>")
    - timeline: Chronological timeline of scenario evidence events (and optional background context)
    - explanation: Comprehensive human-readable narrative explaining all findings
    """
    acc_id = str(account_id).strip()
    graph_data = _load_graph_data()
    
    # 1. Unified account history from Member 1's utility
    history = get_account_history(acc_id)
    
    # 2. Extract employee_id
    employee_id: Optional[str] = None
    if history.get("employees"):
        employee_id = str(history["employees"][0].get("employee_id"))
    elif history.get("access_events"):
        employee_id = str(history["access_events"][0].get("employee_id"))
        
    # 3. Graph Intelligence Signals (Parts 1-3)
    scores_df = graph_data["scores"]
    struct_df = graph_data["struct"]
    clust_df = graph_data["clusters"]
    
    score_row = scores_df[scores_df["account_id"].astype(str) == acc_id]
    struct_row = struct_df[struct_df["account_id"].astype(str) == acc_id]
    clust_row = clust_df[clust_df["account_id"].astype(str) == acc_id]
    
    anomaly_score = float(score_row.iloc[0]["graph_anomaly_score"]) if not score_row.empty else 0.0
    factors = str(score_row.iloc[0]["contributing_factors"]) if not score_row.empty else "No graph anomalies detected"
    
    struct_dict = {}
    if not struct_row.empty:
        r = struct_row.iloc[0]
        struct_dict = {
            "degree": int(r["degree"]),
            "in_degree": int(r["in_degree"]),
            "out_degree": int(r["out_degree"]),
            "betweenness_centrality": float(r["betweenness_centrality"]),
            "clustering_coefficient": float(r["clustering_coefficient"]),
            "is_on_any_cycle": bool(r["is_on_any_cycle"]),
            "num_connected_employees": int(r["num_connected_employees"])
        }
        
    clust_dict = {}
    if not clust_row.empty:
        r = clust_row.iloc[0]
        clust_dict = {
            "cluster_label": int(r["cluster_label"]),
            "cluster_size": int(r["cluster_size"]),
            "is_outlier": bool(r["is_outlier"])
        }
        
    graph_intel_signal = {
        "graph_anomaly_score": anomaly_score,
        "contributing_factors": factors,
        "structural_metrics": struct_dict,
        "clustering_metrics": clust_dict
    }
    
    # 4. Determine involved account_ids and cycle transaction IDs
    involved_accounts = [acc_id]
    edges_df = graph_data["edges"]
    nodes_df = graph_data["nodes"]
    inj_df = graph_data["injected_txns"]
    
    synth_tx_ids: Set[str] = set()
    
    # If participating in a cycle, find all cycle counterparties and cycle transactions
    if struct_dict.get("is_on_any_cycle"):
        sent_edges = edges_df[edges_df["edge_type"] == "SENT_TO"]
        G_sent = nx.DiGraph()
        for _, r in sent_edges.iterrows():
            G_sent.add_edge(str(r["source_id"]), str(r["target_id"]))
            
        for cycle in nx.simple_cycles(G_sent, length_bound=6):
            if len(cycle) >= 2 and acc_id in cycle:
                for c_acc in cycle:
                    if c_acc not in involved_accounts:
                        involved_accounts.append(c_acc)
                # Capture all transactions along the cycle ring
                for i in range(len(cycle)):
                    u = cycle[i]
                    v = cycle[(i + 1) % len(cycle)]
                    cycle_step_edges = sent_edges[
                        (sent_edges["source_id"].astype(str) == u) &
                        (sent_edges["target_id"].astype(str) == v)
                    ]
                    for _, c_row in cycle_step_edges.iterrows():
                        try:
                            meta = json.loads(c_row["metadata"]) if pd.notna(c_row["metadata"]) else {}
                            t_id = meta.get("transaction_id")
                            if t_id:
                                synth_tx_ids.add(str(t_id))
                        except Exception:
                            pass
                break
                
    # Also add transactions from history
    for tx in history.get("transactions", []):
        if tx.get("is_synthetic"):
            t_id = str(tx.get("transaction_id", ""))
            if t_id:
                synth_tx_ids.add(t_id)
            fa = str(tx.get("from_account", ""))
            ta = str(tx.get("to_account", ""))
            if fa and fa not in involved_accounts:
                involved_accounts.append(fa)
            if ta and ta not in involved_accounts:
                involved_accounts.append(ta)
                
    # 5. Build Evidence Subgraph with Typed, Collision-Free Node IDs
    # Prefixes:
    # "ACCT_<id>" for Account nodes
    # "CUST_<id>" for Customer nodes
    # "EMP_<id>"  for Employee nodes
    # "SYN_<id>" / "TXN_<id>" for Transaction nodes
    
    sub_nodes = []
    
    # 5a. Account nodes
    for a_id in involved_accounts:
        acc_label = f"Account {a_id}"
        if not nodes_df.empty:
            match = nodes_df[(nodes_df["node_id"].astype(str) == a_id) & (nodes_df["node_type"] == "Account")]
            if not match.empty:
                acc_label = str(match.iloc[0]["label"])
        sub_nodes.append({
            "id": f"ACCT_{a_id}",
            "type": "Account",
            "label": acc_label,
            "raw_id": a_id
        })
        
    # 5b. Customer nodes
    for a_id in involved_accounts:
        cust_match = nodes_df[(nodes_df["node_id"].astype(str) == a_id) & (nodes_df["node_type"] == "Customer")] if not nodes_df.empty else pd.DataFrame()
        if not cust_match.empty:
            sub_nodes.append({
                "id": f"CUST_{a_id}",
                "type": "Customer",
                "label": str(cust_match.iloc[0]["label"]),
                "raw_id": a_id
            })
            
    # 5c. Employee node
    if employee_id:
        emp_label = f"Employee {employee_id}"
        if not nodes_df.empty:
            match = nodes_df[nodes_df["node_id"].astype(str) == employee_id]
            if not match.empty:
                emp_label = str(match.iloc[0]["label"])
        sub_nodes.append({
            "id": employee_id,
            "type": "Employee",
            "label": emp_label,
            "raw_id": employee_id
        })
        
    # 5d. Transaction nodes
    for tx_id in sorted(synth_tx_ids):
        tx_label = f"Transaction {tx_id}"
        if not nodes_df.empty:
            match = nodes_df[nodes_df["node_id"].astype(str) == tx_id]
            if not match.empty:
                tx_label = str(match.iloc[0]["label"])
        sub_nodes.append({
            "id": tx_id,
            "type": "Transaction",
            "label": tx_label,
            "raw_id": tx_id
        })

    # 5e. Subgraph Edges with Prefixed Source/Target Remapping
    raw_node_ids = set(involved_accounts) | {employee_id} | synth_tx_ids
    sub_edges = []
    
    if not edges_df.empty:
        matched_edges = edges_df[
            edges_df["source_id"].astype(str).isin(raw_node_ids) &
            edges_df["target_id"].astype(str).isin(raw_node_ids)
        ]
        
        for _, er in matched_edges.iterrows():
            etype = str(er["edge_type"])
            src = str(er["source_id"])
            tgt = str(er["target_id"])
            ts = str(er["timestamp"]) if pd.notna(er["timestamp"]) else None
            meta_raw = er["metadata"]
            try:
                meta = json.loads(meta_raw) if pd.notna(meta_raw) and meta_raw else {}
            except Exception:
                meta = {"raw": str(meta_raw)}
                
            # Determine mapped source and target IDs
            if etype == "OWNS":
                # Customer -> Account
                mapped_src = f"CUST_{src}"
                mapped_tgt = f"ACCT_{tgt}"
            elif etype == "MANAGES":
                # Employee -> Customer
                mapped_src = src
                mapped_tgt = f"CUST_{tgt}"
            elif etype == "CHANGED_ACCESS":
                # Employee -> Account
                mapped_src = src
                mapped_tgt = f"ACCT_{tgt}"
            elif etype == "EDITED_PROFILE":
                # Employee -> Customer
                mapped_src = src
                mapped_tgt = f"CUST_{tgt}"
            elif etype == "SENT_TO":
                # Account -> Account
                mapped_src = f"ACCT_{src}"
                mapped_tgt = f"ACCT_{tgt}"
                is_synth = meta.get("is_synthetic", False)
                if not is_synth and src == tgt:
                    continue  # skip self-transfers
                if not is_synth and not (src in involved_accounts and tgt in involved_accounts):
                    continue
            elif etype == "INVOLVED_IN":
                # Account -> Transaction
                mapped_src = f"ACCT_{src}"
                mapped_tgt = tgt
                if tgt not in synth_tx_ids and src not in synth_tx_ids:
                    continue
            else:
                mapped_src = src
                mapped_tgt = tgt
                
            sub_edges.append({
                "source": mapped_src,
                "target": mapped_tgt,
                "type": etype,
                "timestamp": ts,
                "metadata": meta
            })
            
    # Deduplicate edges
    unique_sub_edges = []
    seen_edge_signatures = set()
    for e in sub_edges:
        tx_id = e["metadata"].get("transaction_id", "")
        sig = (e["source"], e["target"], e["type"], tx_id)
        if sig not in seen_edge_signatures:
            seen_edge_signatures.add(sig)
            unique_sub_edges.append(e)

    evidence_subgraph = {
        "nodes": sub_nodes,
        "edges": unique_sub_edges
    }
    
    # 6. Build Clean, Chronological Timeline
    # Pull all relevant transactions for the scenario / cycle (including intermediate hops)
    timeline = []
    
    # Access events genuinely tied to scenario or connected employee
    for ev in history.get("access_events", []):
        ev_emp = str(ev.get("employee_id", ""))
        is_scenario_tied = (ev_emp == employee_id) or bool(ev.get("scenario_id"))
        
        if is_scenario_tied:
            timeline.append({
                "timestamp": str(ev.get("timestamp")),
                "event_type": "access_event",
                "category": "scenario_evidence",
                "summary": f"Access modification by {ev_emp}: {ev.get('action')} ({ev.get('old_value')} -> {ev.get('new_value')})",
                "details": ev
            })
        elif include_background_context:
            timeline.append({
                "timestamp": str(ev.get("timestamp")),
                "event_type": "access_event",
                "category": "background_context",
                "summary": f"[Background] Access event by {ev_emp}: {ev.get('action')}",
                "details": ev
            })

    # Profile changes: filter to employee_id or scenario, or tag as background_context
    for pr in history.get("profile_changes", []):
        pr_emp = str(pr.get("changed_by_employee_id", ""))
        is_scenario_tied = (pr_emp == employee_id)
        
        if is_scenario_tied:
            timeline.append({
                "timestamp": str(pr.get("timestamp")),
                "event_type": "profile_change",
                "category": "scenario_evidence",
                "summary": f"Customer profile change by employee {pr_emp}: {pr.get('field_changed')} ({pr.get('old_value')} -> {pr.get('new_value')})",
                "details": pr
            })
        elif include_background_context:
            timeline.append({
                "timestamp": str(pr.get("timestamp")),
                "event_type": "profile_change",
                "category": "background_context",
                "summary": f"[Background] Customer profile change by employee {pr_emp}: {pr.get('field_changed')}",
                "details": pr
            })

    # All transactions in synth_tx_ids (ensures all 3 hops appear in timeline)
    # Check both history transactions and injected_transactions.csv
    seen_tx_ids = set()
    
    # Check injected transactions table for full metadata across all involved accounts
    if not inj_df.empty:
        matched_txs = inj_df[inj_df["transaction_id"].astype(str).isin(synth_tx_ids)]
        for _, tx_row in matched_txs.iterrows():
            t_id = str(tx_row["transaction_id"])
            seen_tx_ids.add(t_id)
            amt = float(tx_row.get("amount_paid", 0.0))
            curr = str(tx_row.get("payment_currency", "USD"))
            fmt = str(tx_row.get("payment_format", "Transfer"))
            fa = str(tx_row.get("from_account", ""))
            ta = str(tx_row.get("to_account", ""))
            ts = str(tx_row.get("timestamp", ""))
            
            timeline.append({
                "timestamp": ts,
                "event_type": "transaction",
                "category": "scenario_evidence",
                "summary": f"Scenario transaction {t_id}: {fa} -> {ta} ({amt:,.2f} {curr} via {fmt})",
                "details": {
                    "transaction_id": t_id,
                    "timestamp": ts,
                    "from_account": fa,
                    "to_account": ta,
                    "amount_paid": amt,
                    "payment_currency": curr,
                    "payment_format": fmt,
                    "is_synthetic": True,
                    "is_laundering": int(tx_row.get("is_laundering", 1))
                }
            })
            
    # Also check if any remaining in history transactions
    for tx in history.get("transactions", []):
        t_id = str(tx.get("transaction_id", ""))
        if tx.get("is_synthetic") and t_id in synth_tx_ids and t_id not in seen_tx_ids:
            seen_tx_ids.add(t_id)
            amt = float(tx.get("amount_paid", 0.0))
            curr = str(tx.get("payment_currency", "USD"))
            fmt = str(tx.get("payment_format", "Transfer"))
            timeline.append({
                "timestamp": str(tx.get("timestamp")),
                "event_type": "transaction",
                "category": "scenario_evidence",
                "summary": f"Scenario transaction {t_id}: {tx.get('from_account')} -> {tx.get('to_account')} ({amt:,.2f} {curr} via {fmt})",
                "details": tx
            })
            
    # Sort timeline strictly chronologically
    timeline.sort(key=lambda x: str(x.get("timestamp", "")))
    
    # 7. Evaluate Multi-Signal Risk Fusion (Part 1 Integration)
    risk_score: Optional[float] = None
    risk_tier: Optional[str] = None
    rule_engine_signal: Dict[str, Any] = {}
    ml_model_signal: Dict[str, Any] = {}
    
    try:
        fusion = fuse_account_risk(acc_id)
        risk_score = fusion.get("risk_score")
        risk_tier = fusion.get("risk_tier")
        comps = fusion.get("components", {})
        rule_engine_signal = comps.get("rule_engine", {})
        ml_model_signal = {
            "xgboost": comps.get("xgboost", {}),
            "isolation_forest": comps.get("isolation_forest", {})
        }
    except Exception as e:
        risk_score = 0.0
        risk_tier = "Low"
        rule_engine_signal = {"triggered": False, "fired_rules": [], "error": str(e)}
        ml_model_signal = {"xgboost": {}, "isolation_forest": {}}

    # 8. Compose Explainable Evidence Narrative
    explanation_parts = [
        f"Alert ALT-{acc_id} for Account {acc_id} assigned {risk_tier} Risk Tier with composite Risk Score of {risk_score:.4f}."
    ]
    if rule_engine_signal.get("fired_rules"):
        rules_str = ", ".join(rule_engine_signal["fired_rules"])
        explanation_parts.append(f"Deterministic rules triggered: {rules_str}.")
        
    xgb_info = ml_model_signal.get("xgboost", {})
    if xgb_info:
        xgb_p = xgb_info.get("probability", 0.0)
        explanation_parts.append(f"Supervised XGBoost AML probability: {xgb_p:.4f} (threshold: {xgb_info.get('decision_threshold', 0.5)}).")
        
    if factors:
        explanation_parts.append(f"Graph intelligence: {factors} (Graph Anomaly Score: {anomaly_score:.4f}).")
        
    if struct_dict.get("is_on_any_cycle"):
        explanation_parts.append(
            f"Network analysis confirms account {acc_id} participates in a closed circular layering cycle "
            f"within the transaction network, returning funds back to the originating flow."
        )
    if employee_id:
        explanation_parts.append(
            f"Corroborating insider context: Linked to employee {employee_id} via internal access administration records."
        )
    if synth_tx_ids:
        explanation_parts.append(
            f"Detected {len(synth_tx_ids)} high-priority scenario transactions in close temporal proximity."
        )
        
    explanation = " ".join(explanation_parts)

    # 9. Assemble Full Evidence Object Matching Data Contract
    evidence_object: Dict[str, Any] = {
        "alert_id": f"ALT-{acc_id}",
        "account_ids": involved_accounts,
        "employee_id": employee_id,
        "risk_tier": risk_tier,
        "risk_score": risk_score,
        "signals": {
            "rule_engine": rule_engine_signal,
            "ml_model": ml_model_signal,
            "graph_intelligence": graph_intel_signal
        },
        "evidence_subgraph": evidence_subgraph,
        "timeline": timeline,
        "explanation": explanation
    }

    return evidence_object


# Backward-compatibility alias
build_partial_evidence_object = build_evidence_object


def demonstrate_evidence_objects():
    """Build and display the complete evidence objects for S19 and L19."""
    s19_account_id = "800085BF0"
    l19_account_id = "80026A5A0"
    
    # ─── 1. S19 Evidence Demonstration ───
    print("=" * 80)
    print(f"1. BUILDING COMPLETE EVIDENCE OBJECT FOR S19 ACCOUNT: {s19_account_id}")
    print("=" * 80)
    s19_evidence = build_evidence_object(s19_account_id)
    print(json.dumps(s19_evidence, indent=2, ensure_ascii=False))
    
    assert s19_evidence["alert_id"] == f"ALT-{s19_account_id}", "Alert ID mismatch"
    assert s19_account_id in s19_evidence["account_ids"], "Account ID not in account_ids"
    assert s19_evidence["employee_id"] == "EMP_0047", f"Expected EMP_0047, got {s19_evidence['employee_id']}"
    assert s19_evidence["risk_tier"] in ["High", "Critical"], f"S19 tier expected High/Critical, got {s19_evidence['risk_tier']}"
    assert s19_evidence["risk_score"] >= 0.55, f"Expected S19 risk_score >= 0.55, got {s19_evidence['risk_score']}"
    assert s19_evidence["signals"]["rule_engine"]["triggered"] is True, "Expected rule_engine triggered for S19"
    assert "AML.CIRCULAR_TRANSFER" in s19_evidence["signals"]["rule_engine"]["fired_rules"], "Missing circular transfer rule in S19"
    assert s19_evidence["signals"]["ml_model"]["xgboost"]["is_suspicious"] is True, "XGBoost expected suspicious for S19"
    assert s19_evidence["signals"]["graph_intelligence"]["graph_anomaly_score"] > 0.5, "Expected high graph anomaly score for S19"
    
    # Check node ID collision fix
    s19_node_ids = [n["id"] for n in s19_evidence["evidence_subgraph"]["nodes"]]
    assert len(s19_node_ids) == len(set(s19_node_ids)), "Duplicate node IDs in S19 subgraph!"
    assert "ACCT_800085BF0" in s19_node_ids and "CUST_800085BF0" in s19_node_ids
    
    # Check intermediate hop in timeline
    tl_txs = [i["details"]["transaction_id"] for i in s19_evidence["timeline"] if i["event_type"] == "transaction"]
    assert "SYN_S19_001" in tl_txs and "SYN_S19_002" in tl_txs and "SYN_S19_003" in tl_txs
    
    print("\n" + "=" * 80)
    print(f"S19 VERIFICATION PASSED: Risk Tier = {s19_evidence['risk_tier']}, Risk Score = {s19_evidence['risk_score']} ✅")
    print("=" * 80)
    
    # ─── 2. L19 Evidence Demonstration ───
    print("\n" + "=" * 80)
    print(f"2. BUILDING COMPLETE EVIDENCE OBJECT FOR L19 ACCOUNT: {l19_account_id}")
    print("=" * 80)
    l19_evidence = build_evidence_object(l19_account_id)
    print(json.dumps(l19_evidence, indent=2, ensure_ascii=False))
    
    assert l19_evidence["risk_tier"] in ["Low", "Medium"], f"L19 tier expected Low/Medium, got {l19_evidence['risk_tier']}"
    assert l19_evidence["risk_score"] < 0.55, f"Expected L19 risk_score < 0.55, got {l19_evidence['risk_score']}"
    assert l19_evidence["signals"]["graph_intelligence"]["structural_metrics"]["is_on_any_cycle"] is False, "L19 must NOT be on any cycle"
    
    print("\n" + "=" * 80)
    print(f"L19 VERIFICATION PASSED: Risk Tier = {l19_evidence['risk_tier']}, Risk Score = {l19_evidence['risk_score']} ✅")
    print("=" * 80)
    
    return s19_evidence, l19_evidence


if __name__ == "__main__":
    demonstrate_evidence_objects()

