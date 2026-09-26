"""
structural_features.py — Graph-Structural Features Extraction for Account Nodes

Computes graph-topological metrics for all Account nodes in HackMatrix:
- degree: total edges incident to this account across all edge types
- in_degree: incoming SENT_TO edges (transactions received)
- out_degree: outgoing SENT_TO edges (transactions sent)
- betweenness_centrality: shortest-path flow centrality in the SENT_TO transaction network
- clustering_coefficient: clustering coefficient in the SENT_TO transaction network
- is_on_any_cycle: boolean indicator for participation in simple cycles (length 2-6) in SENT_TO subgraph
- num_connected_employees: count of unique employees linked via CHANGED_ACCESS or MANAGES edges

Output:
- data/graph_intel/account_structural_features.csv
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import networkx as nx
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Configure path constants
BASE_DIR = Path(__file__).resolve().parent.parent
GRAPH_DIR = BASE_DIR / "graph"
ENTITIES_DIR = BASE_DIR / "entities"
OUTPUT_DIR = BASE_DIR / "graph_intel"
OUTPUT_FILE = OUTPUT_DIR / "account_structural_features.csv"


def compute_structural_features(
    nodes_path: Path = GRAPH_DIR / "nodes.csv",
    edges_path: Path = GRAPH_DIR / "edges.csv",
    accounts_path: Path = ENTITIES_DIR / "accounts.csv",
    max_cycle_length: int = 6
) -> pd.DataFrame:
    """
    Extracts graph structural features for all Account nodes.
    
    Args:
        nodes_path: Path to data/graph/nodes.csv
        edges_path: Path to data/graph/edges.csv
        accounts_path: Path to data/entities/accounts.csv
        max_cycle_length: Maximum simple cycle length to detect (default 6)
        
    Returns:
        DataFrame with columns:
        [account_id, degree, in_degree, out_degree, betweenness_centrality,
         clustering_coefficient, is_on_any_cycle, num_connected_employees]
    """
    t0 = time.time()
    print("=" * 70)
    print("STEP 1: Loading graph nodes and edges...")
    nodes_df = pd.read_csv(nodes_path)
    edges_df = pd.read_csv(edges_path)
    
    # 1. Identify all Account nodes
    account_nodes_df = nodes_df[nodes_df['node_type'] == 'Account']
    all_account_ids = sorted(account_nodes_df['node_id'].astype(str).unique())
    print(f"Loaded {len(nodes_df):,} total nodes ({len(all_account_ids):,} Account nodes)")
    print(f"Loaded {len(edges_df):,} total edges")

    # 2. Build full multi-graph for total degree
    print("\nSTEP 2: Building full graph for incident degree computation...")
    G_full = nx.MultiGraph()
    for acc in all_account_ids:
        G_full.add_node(acc)
        
    for _, row in edges_df.iterrows():
        src = str(row['source_id'])
        tgt = str(row['target_id'])
        G_full.add_edge(src, tgt, edge_type=row['edge_type'])

    # 3. Extract SENT_TO subgraph
    print("\nSTEP 3: Constructing SENT_TO transaction graph...")
    sent_edges_df = edges_df[edges_df['edge_type'] == 'SENT_TO']
    print(f"Total SENT_TO edges: {len(sent_edges_df):,}")

    # Directed multigraph for exact transaction in/out counts
    G_sent_multi = nx.MultiDiGraph()
    # Simple directed graph for centrality, clustering, and cycle detection
    G_sent_simple = nx.DiGraph()

    for acc in all_account_ids:
        G_sent_multi.add_node(acc)
        G_sent_simple.add_node(acc)

    for _, row in sent_edges_df.iterrows():
        src = str(row['source_id'])
        tgt = str(row['target_id'])
        G_sent_multi.add_edge(src, tgt)
        G_sent_simple.add_edge(src, tgt)

    # 4. Cycle Detection (length 2 to max_cycle_length)
    print(f"\nSTEP 4: Detecting simple cycles (length 2 to {max_cycle_length}) in SENT_TO subgraph...")
    cycle_time_start = time.time()
    raw_cycles = list(nx.simple_cycles(G_sent_simple, length_bound=max_cycle_length))
    # Exclude 1-node self-loops (internal transfers / reinvestments)
    multi_hop_cycles = [c for c in raw_cycles if len(c) >= 2]
    cycle_accounts = set()
    for cycle in multi_hop_cycles:
        for node in cycle:
            cycle_accounts.add(node)

    print(f"Cycle detection completed in {time.time() - cycle_time_start:.2f}s")
    print(f"Found {len(multi_hop_cycles)} multi-hop cycles (lengths: {[len(c) for c in multi_hop_cycles]})")
    print(f"Total accounts participating in cycles: {len(cycle_accounts)}")

    # 5. Centrality and Clustering
    print("\nSTEP 5: Computing betweenness centrality and clustering coefficient...")
    t_bc = time.time()
    betweenness_dict = nx.betweenness_centrality(G_sent_simple)
    print(f"Betweenness centrality computed in {time.time() - t_bc:.2f}s")

    t_cc = time.time()
    clustering_dict = nx.clustering(G_sent_simple)
    print(f"Clustering coefficient computed in {time.time() - t_cc:.2f}s")

    # 6. Connected Employees via CHANGED_ACCESS and MANAGES
    print("\nSTEP 6: Mapping connected employees (CHANGED_ACCESS + MANAGES)...")
    # CHANGED_ACCESS: Employee -> Account (target_id is account)
    access_edges = edges_df[edges_df['edge_type'] == 'CHANGED_ACCESS']
    emp_by_access: Dict[str, Set[str]] = {}
    for _, row in access_edges.iterrows():
        emp = str(row['source_id'])
        acc = str(row['target_id'])
        emp_by_access.setdefault(acc, set()).add(emp)

    # MANAGES: Employee -> Customer (target_id is customer)
    # In this dataset, customer_id == account_id (1:1 mapping)
    manages_edges = edges_df[edges_df['edge_type'] == 'MANAGES']
    emp_by_manages: Dict[str, Set[str]] = {}
    for _, row in manages_edges.iterrows():
        emp = str(row['source_id'])
        cust = str(row['target_id'])
        emp_by_manages.setdefault(cust, set()).add(emp)

    # Accounts table for linked_customer_id resolution if needed
    linked_cust_map: Dict[str, str] = {}
    if accounts_path.exists():
        acc_master = pd.read_csv(accounts_path)
        for _, row in acc_master.iterrows():
            aid = str(row['account_id'])
            cid = str(row['linked_customer_id']) if pd.notna(row['linked_customer_id']) else aid
            linked_cust_map[aid] = cid

    # 7. Assemble feature records
    print("\nSTEP 7: Assembling feature records for all accounts...")
    records = []
    for acc in all_account_ids:
        # Total incident edges
        deg = G_full.degree(acc) if acc in G_full else 0
        
        # SENT_TO in/out degrees
        in_deg = G_sent_multi.in_degree(acc) if acc in G_sent_multi else 0
        out_deg = G_sent_multi.out_degree(acc) if acc in G_sent_multi else 0
        
        # Centrality & Clustering
        bc = float(betweenness_dict.get(acc, 0.0))
        cc = float(clustering_dict.get(acc, 0.0))
        
        # Cycle flag
        on_cycle = bool(acc in cycle_accounts)
        
        # Connected employees
        cust_id = linked_cust_map.get(acc, acc)
        connected_emps = set(emp_by_access.get(acc, set())) | set(emp_by_manages.get(cust_id, set()))
        num_emps = len(connected_emps)
        
        records.append({
            "account_id": acc,
            "degree": deg,
            "in_degree": in_deg,
            "out_degree": out_deg,
            "betweenness_centrality": bc,
            "clustering_coefficient": cc,
            "is_on_any_cycle": on_cycle,
            "num_connected_employees": num_emps
        })

    features_df = pd.DataFrame(records)
    print(f"Features computation finished in {time.time() - t0:.2f}s total.")
    return features_df


def save_and_validate(output_file: Path = OUTPUT_FILE) -> pd.DataFrame:
    """
    Computes structural features, saves to CSV, and performs strict validation
    on S19 and L19 pairs.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df = compute_structural_features()
    df.to_csv(output_file, index=False)
    print(f"\n[OUTPUT] Saved {len(df):,} account structural feature records to {output_file}")
    
    # Validation
    print("\n" + "=" * 70)
    print("VALIDATION: S19 (Suspicious Circular Transfer) vs L19 (Legitimate Multi-Hop)")
    print("=" * 70)
    
    s19_accounts = ["800085BF0", "800093C80", "8001C3570"]
    l19_accounts = ["80026A5A0", "80035F420", "8001E34C0"]
    
    print("\n--- S19 Scenario Accounts (Expected is_on_any_cycle=True) ---")
    s19_subset = df[df['account_id'].isin(s19_accounts)].copy()
    print(s19_subset.to_string(index=False))
    
    print("\n--- L19 Scenario Accounts (Expected is_on_any_cycle=False) ---")
    l19_subset = df[df['account_id'].isin(l19_accounts)].copy()
    print(l19_subset.to_string(index=False))
    
    # Assertions
    s19_cycles = s19_subset['is_on_any_cycle'].tolist()
    l19_cycles = l19_subset['is_on_any_cycle'].tolist()
    
    s19_pass = len(s19_cycles) == 3 and all(s19_cycles)
    l19_pass = len(l19_cycles) == 3 and not any(l19_cycles)
    
    print("\n" + "-" * 70)
    print(f"Validation Check 1 (S19 all on cycle): {'PASSED ✅' if s19_pass else 'FAILED ❌'}")
    print(f"Validation Check 2 (L19 none on cycle): {'PASSED ✅' if l19_pass else 'FAILED ❌'}")
    print("-" * 70)
    
    if not (s19_pass and l19_pass):
        raise ValueError("VALIDATION FAILED: Cycle detection did not match expected ground truth!")
        
    print("\nALL PART 1 VALIDATION CHECKS PASSED SUCCESSFULLY.")
    return df


if __name__ == "__main__":
    save_and_validate()
