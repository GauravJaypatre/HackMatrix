# Member 3 Handoff Notes: Graph Intelligence, Risk Fusion & Backend Platform

## 1. Summary of What Was Built

Member 3 built the graph analysis, multi-signal risk fusion, and investigation backend components for HackMatrix:

1. **Structural Feature Extraction (`data/graph_intel/structural_features.py`)**:
   - Parses the transaction graph into a directed NetworkX graph.
   - Computes in-degree, out-degree, total degree, betweenness centrality, and local clustering coefficient per account.
   - Implements bounded cycle detection (lengths 2 to 6) to detect circular layering rings.
   - Connects internal HR/access records to identify insider employee ties per account.
   - Output: `data/graph_intel/account_structural_features.csv` (1,884 accounts).

2. **Node2Vec Topological Embeddings & Clustering (`data/graph_intel/embeddings.py`)**:
   - Trains 64-dimensional Node2Vec embeddings on the transaction graph (`walk_length=20`, `num_walks=10`, `p=1.0`, `q=0.5`).
   - Performs density-based spatial clustering (DBSCAN) on normalized embeddings to uncover cohesive transaction syndicates and isolated micro-communities.
   - Computes outlier status and cluster size metrics.
   - Outputs: `data/graph_intel/account_embeddings.csv`, `data/graph_intel/account_clusters.csv`.

3. **Graph Anomaly Scoring Engine (`data/graph_intel/graph_anomaly_score.py`)**:
   - Computes an account-level composite graph risk score in $[0, 1]$ combining:
     - Cycle membership (35% weight)
     - Betweenness centrality quantile rank (25% weight)
     - Cluster anomaly status: outlier / micro-cluster (20% weight)
     - Employee connections: multiple insider access (20% weight)
   - Generates human-readable contributing factor narratives for investigators.
   - Output: `data/graph_intel/graph_anomaly_scores.csv`.

4. **Evidence Object Schema & Graph Traversal (`data/backend/evidence_schema.py`)**:
   - Assembles full evidence objects conforming to the system data contract.
   - Subgraph builder with collision-free, typed node IDs (`ACCT_<id>`, `CUST_<id>`, `EMP_<id>`, `SYN_<id>`).
   - Multi-hop BFS graph traversal along connected transfer edges to capture entire laundering chains.
   - Chronological timeline integrating access modifications and scenario transactions while filtering background noise.

5. **Multi-Signal Risk Fusion Engine (`data/risk_fusion/fuse_signals.py`)**:
   - Synthesizes all four pillars into an operational score:
     $$\text{risk\_score} = 0.16 \cdot \text{rule\_score} + 0.50 \cdot \text{xgb\_probability} + 0.14 \cdot \text{iforest\_score} + 0.20 \cdot \text{graph\_anomaly\_score}$$
   - Maps scores into operational risk tiers: Low $[0.00, 0.29]$, Medium $[0.30, 0.54]$, High $[0.55, 0.74]$, Critical $[0.75, 1.00]$.
   - Output: `data/risk_fusion/scenario_risk_scores.csv` (all 38 labeled prototypes scored).

6. **FastAPI Investigation API (`data/backend/api.py`)**:
   - REST endpoints for triage dashboard and case investigation:
     - `GET /alerts`: Filtered list of accounts with `risk_tier >= Medium`, sorted descending by `risk_score`.
     - `GET /alerts/{account_id}`: Complete explainable evidence object.
     - `GET /alerts/{account_id}/evidence`: Subgraph and chronological timeline payload.
     - `POST /cases`, `POST /cases/{case_id}/assign`, `GET /cases/{case_id}/export`: Investigation lifecycle & export.
   - CORS middleware enabled for Member 4's frontend UI dashboard.

---

## 2. Critical Fix History

### A. Feature Leakage Resolution in XGBoost Model
- **Vulnerability**: The previous model included Group X features (`injected_txn_count`, `injected_mean_amount`, `injected_sub_threshold_fraction`, `injected_wire_fraction`) computed exclusively from `injected_transactions.csv`. Since background accounts had 0 injected transactions by definition, the classifier learned a trivial shortcut distinguishing whether an account was part of an injected scenario file rather than detecting real laundering behavior.
- **Correction**: Completely removed `injected_*` features. Replaced them with equivalents computed over ALL transactions (real + synthetic unified into a single ledger) without synthetic indicators: `mean_amount`, `wire_fraction`, `sub_threshold_fraction`, and `total_transaction_count`. Retrained XGBoost on the corrected 10-feature set (documented in `data/models/RESULTS.md`).
- **Honest Metrics (LOSO-CV)**: ROC-AUC: `0.7452 ± 0.0816`, PR-AUC: `0.7620`, Precision: `0.6471`, Recall: `0.5789`, F1: `0.6111`.

### B. L19 Multi-Hop Evidence Traversal Bug Fix
- **Vulnerability**: In scenario L19, three accounts form a linear chain (`80026A5A0 -> 80035F420 -> 8001E34C0`). Previously, traversal only looked for closed cycles, causing `build_evidence_object` to omit the 3rd hop account (`8001E34C0`) and transaction `SYN_L19_002`.
- **Correction**: Implemented multi-hop BFS graph traversal across connected synthetic `SENT_TO` edges combined with scenario transaction cross-referencing. L19's evidence object now includes all 3 chain accounts, both synthetic transactions, full typed subgraph edges, and complete chronological timeline.

---

## 3. Reporting Honesty: Calibration vs. Validation

> [!IMPORTANT]
> The tier separation metrics (e.g. 100% of suspicious scenarios landing in High/Critical and 0% false positives on the 38 prototypes) were achieved by **calibrating (tuning) fusion weights directly against the 38 labeled scenarios**.
> 
> **This is calibration, NOT out-of-sample validation.**
> 
> When pitching or presenting to judges, do NOT present these numbers as out-of-sample accuracy or generalization metrics on unseen bank data. Refer to `data/models/RESULTS.md` for the honest, generalizing LOSO-CV metrics.

---

## 4. Extraction Instructions

To integrate this package into the shared repository:
1. Extract this zip file into the **root** of the `HackMatrix` repository:
   ```bash
   # Extract preserving folder hierarchy (data/graph_intel, data/backend, data/risk_fusion, requirements.txt)
   unzip graph-intel.zip -d /path/to/HackMatrix/
   ```
2. Verify that files are placed into their respective directories:
   - `data/graph_intel/`
   - `data/backend/`
   - `data/risk_fusion/`
   - `requirements.txt`
   - `HANDOFF_NOTES.md` (root)
3. Ensure no files in `data/detection/`, `data/models/`, `data/entities/`, or `data/synthetic_hr/` are overwritten.

---

## 5. Recommended Git Branch & Commit Details

- **Branch Name**: `feature/graph-intelligence-final`
- **Commit Message**:
  ```text
  feat(graph-intel,backend,fusion): implement graph intelligence, risk fusion, and investigation API with un-leaked XGBoost and multi-hop traversal fixes
  ```
