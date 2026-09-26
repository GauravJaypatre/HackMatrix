"""
embeddings.py — Node2Vec Graph Embeddings & DBSCAN Clustering for Account Nodes

Generates 64-dimensional structural embeddings using Node2Vec for all Account nodes
in the HackMatrix investigation graph, then applies DBSCAN density-based clustering
to identify anomalous/isolated accounts and topological clusters.

Requirements:
- Dimensions: 64
- Walk length: 30
- Number of walks: 200
- Seed: 42 (for full reproducibility)
- Evaluates DBSCAN eps grid and reports cluster distributions
- Labels scenario accounts from data/synthetic_hr/labeled_scenarios.csv
- Validates suspicious vs legitimate scenario outlier/small-cluster rates

Outputs:
- data/graph_intel/account_embeddings.csv
- data/graph_intel/account_clusters.csv
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections import Counter
import networkx as nx
import numpy as np
import pandas as pd
from node2vec import Node2Vec
from sklearn.cluster import DBSCAN

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Configure paths
BASE_DIR = Path(__file__).resolve().parent.parent
GRAPH_DIR = BASE_DIR / "graph"
HR_DIR = BASE_DIR / "synthetic_hr"
OUTPUT_DIR = BASE_DIR / "graph_intel"
NODES_FILE = GRAPH_DIR / "nodes.csv"
EDGES_FILE = GRAPH_DIR / "edges.csv"
SCENARIOS_FILE = HR_DIR / "labeled_scenarios.csv"
EMBEDDINGS_FILE = OUTPUT_DIR / "account_embeddings.csv"
CLUSTERS_FILE = OUTPUT_DIR / "account_clusters.csv"


def build_account_graph(nodes_path: Path = NODES_FILE, edges_path: Path = EDGES_FILE) -> Tuple[nx.Graph, List[str]]:
    """
    Builds the Account-level graph structure from nodes.csv and edges.csv.
    Includes all Account nodes and undirected transaction edges (SENT_TO)
    to capture topological connectivity across fund flows.
    """
    nodes_df = pd.read_csv(nodes_path)
    edges_df = pd.read_csv(edges_path)
    
    account_nodes = sorted(nodes_df[nodes_df['node_type'] == 'Account']['node_id'].astype(str).unique())
    
    G = nx.Graph()
    for acc in account_nodes:
        G.add_node(acc)
        
    sent_edges = edges_df[edges_df['edge_type'] == 'SENT_TO']
    for _, row in sent_edges.iterrows():
        G.add_edge(str(row['source_id']), str(row['target_id']))
        
    return G, account_nodes


def generate_node2vec_embeddings(
    G: nx.Graph,
    account_nodes: List[str],
    dimensions: int = 64,
    walk_length: int = 30,
    num_walks: int = 200,
    seed: int = 42,
    workers: int = 4
) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """
    Runs Node2Vec walk generation and Word2Vec fitting with fixed random seed.
    """
    print(f"\n[Node2Vec] Initializing walk generation (dims={dimensions}, walk_len={walk_length}, num_walks={num_walks}, seed={seed})...")
    t0 = time.time()
    n2v = Node2Vec(
        G,
        dimensions=dimensions,
        walk_length=walk_length,
        num_walks=num_walks,
        workers=workers,
        seed=seed,
        quiet=True
    )
    print(f"[Node2Vec] Random walks generated in {time.time() - t0:.2f}s")
    
    print("[Node2Vec] Fitting Skip-gram Word2Vec model...")
    t1 = time.time()
    model = n2v.fit(window=10, min_count=1, workers=workers, seed=seed)
    print(f"[Node2Vec] Model fitting completed in {time.time() - t1:.2f}s")
    
    emb_dict = {}
    emb_matrix = []
    for acc in account_nodes:
        vec = model.wv[acc]
        emb_dict[acc] = vec
        emb_matrix.append(vec)
        
    return np.array(emb_matrix), emb_dict


def run_dbscan_analysis(
    embeddings: np.ndarray,
    account_nodes: List[str],
    scenarios_path: Path = SCENARIOS_FILE,
    candidate_eps_list: List[float] = [0.8, 1.0, 1.5, 2.0, 2.5],
    min_samples: int = 5,
    selected_eps: float = 1.5,
    small_cluster_threshold: int = 15
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Evaluates DBSCAN clustering across eps grid, clusters accounts using selected_eps,
    and reports scenario accounts' cluster assignments and outlier status.
    """
    print("\n" + "=" * 70)
    print(f"DBSCAN PARAMETER GRID EVALUATION (min_samples={min_samples})")
    print("=" * 70)
    
    grid_results = []
    for eps in candidate_eps_list:
        db = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean').fit(embeddings)
        labels = db.labels_
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_outliers = (labels == -1).sum()
        pct_outliers = (n_outliers / len(labels)) * 100
        grid_results.append({
            "eps": eps,
            "clusters": n_clusters,
            "outliers": n_outliers,
            "outlier_pct": pct_outliers
        })
        print(f"  eps={eps:4.2f}  -->  {n_clusters:3d} clusters,  {n_outliers:4d} outliers ({pct_outliers:5.1f}%)")
        
    print(f"\n[DBSCAN Selection] Proceeding with selected eps={selected_eps:.2f} "
          f"(avoids single monolithic cluster while preserving distinct behavioral groupings)")
    
    # Run selected clustering
    selected_db = DBSCAN(eps=selected_eps, min_samples=min_samples, metric='euclidean').fit(embeddings)
    final_labels = selected_db.labels_
    label_counts = Counter(final_labels)
    
    # Build cluster assignments dataframe
    clusters_df = pd.DataFrame({
        "account_id": account_nodes,
        "cluster_label": final_labels,
        "cluster_size": [label_counts[lbl] if lbl != -1 else 1 for lbl in final_labels],
        "is_outlier": [lbl == -1 for lbl in final_labels]
    })
    
    # Evaluate scenario accounts
    print("\n" + "=" * 70)
    print("SCENARIO ACCOUNTS CLUSTERING EVALUATION (All 38 Scenarios)")
    print("=" * 70)
    
    scenarios_df = pd.read_csv(scenarios_path)
    acc_to_cluster = dict(zip(clusters_df['account_id'], clusters_df['cluster_label']))
    acc_to_size = dict(zip(clusters_df['account_id'], clusters_df['cluster_size']))
    acc_to_outlier = dict(zip(clusters_df['account_id'], clusters_df['is_outlier']))
    
    scenario_records = []
    for _, row in scenarios_df.iterrows():
        sid = str(row['scenario_id'])
        stype = str(row['scenario_type'])
        acc_str = str(row['account_id'])
        for acc in [a.strip() for a in acc_str.split(';') if a.strip()]:
            c_lbl = acc_to_cluster.get(acc, -1)
            c_sz = acc_to_size.get(acc, 1)
            is_out = acc_to_outlier.get(acc, True)
            is_small_or_out = bool(is_out or (c_sz <= small_cluster_threshold))
            
            scenario_records.append({
                "scenario_id": sid,
                "scenario_type": stype,
                "account_id": acc,
                "cluster_label": c_lbl,
                "cluster_size": c_sz,
                "is_outlier": is_out,
                "is_small_or_outlier": is_small_or_out
            })
            
    scen_results_df = pd.DataFrame(scenario_records)
    print(scen_results_df.to_string(index=False))
    
    # Compute Validation Fractions
    susp_df = scen_results_df[scen_results_df['scenario_type'] == 'suspicious']
    legit_df = scen_results_df[scen_results_df['scenario_type'] == 'legitimate']
    
    susp_outliers = susp_df['is_outlier'].sum()
    susp_small_or_out = susp_df['is_small_or_outlier'].sum()
    susp_total = len(susp_df)
    
    legit_outliers = legit_df['is_outlier'].sum()
    legit_small_or_out = legit_df['is_small_or_outlier'].sum()
    legit_total = len(legit_df)
    
    print("\n" + "=" * 70)
    print("PART 2 VALIDATION: SUSPICIOUS VS LEGITIMATE SCENARIO BEHAVIOR")
    print("=" * 70)
    print(f"SUSPICIOUS Scenario Accounts ({susp_total} total accounts):")
    print(f"  - Outliers (cluster_label = -1): {susp_outliers}/{susp_total} ({susp_outliers/susp_total*100:.1f}%)")
    print(f"  - In small clusters (size <= {small_cluster_threshold}) or outliers: {susp_small_or_out}/{susp_total} ({susp_small_or_out/susp_total*100:.1f}%)")
    
    print(f"\nLEGITIMATE Scenario Accounts ({legit_total} total accounts):")
    print(f"  - Outliers (cluster_label = -1): {legit_outliers}/{legit_total} ({legit_outliers/legit_total*100:.1f}%)")
    print(f"  - In small clusters (size <= {small_cluster_threshold}) or outliers: {legit_small_or_out}/{legit_total} ({legit_small_or_out/legit_total*100:.1f}%)")
    print("-" * 70)
    
    return clusters_df, scen_results_df


def run_pipeline() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Execute complete Part 2 pipeline and save output artifacts."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    G, account_nodes = build_account_graph()
    print(f"[Graph Setup] Account graph constructed: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # 1. Generate Embeddings
    embeddings, emb_dict = generate_node2vec_embeddings(G, account_nodes)
    
    # Save embeddings
    emb_cols = [f"emb_{i}" for i in range(embeddings.shape[1])]
    emb_df = pd.DataFrame(embeddings, columns=emb_cols)
    emb_df.insert(0, "account_id", account_nodes)
    emb_df.to_csv(EMBEDDINGS_FILE, index=False)
    print(f"\n[OUTPUT] Saved account embeddings matrix to {EMBEDDINGS_FILE}")
    
    # 2. Run DBSCAN Clustering & Scenario Validation
    clusters_df, scen_results_df = run_dbscan_analysis(embeddings, account_nodes)
    clusters_df.to_csv(CLUSTERS_FILE, index=False)
    print(f"[OUTPUT] Saved account cluster assignments to {CLUSTERS_FILE}")
    
    return emb_df, clusters_df


if __name__ == "__main__":
    run_pipeline()
