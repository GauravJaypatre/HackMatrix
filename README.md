# HackMatrix — Financial Crime & Insider Risk Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15.0%2B-black.svg)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-blue.svg)](https://www.typescriptlang.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-1.7.6-orange.svg)](https://xgboost.readthedocs.io/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v3-38bdf8.svg)](https://tailwindcss.com/)
[![Tests](https://img.shields.io/badge/Pytest-73%20Passed-brightgreen.svg)](#step-4-verification--test-suite-execution)

> **Next-Generation Multi-Signal Anti-Money Laundering (AML) & Insider Threat Detection Platform**  
> Fusing deterministic audit rules, un-leaked supervised machine learning (XGBoost + SHAP), unsupervised behavioral anomaly detection (Isolation Forest), and graph topological intelligence (NetworkX + Node2Vec + DBSCAN) into an explainable investigation workbench.

---

## Table of Contents
- [Executive Overview](#executive-overview)
- [System Architecture](#system-architecture)
- [The Four Detection Pillars](#the-four-detection-pillars)
  - [1. Deterministic Rule Engine](#1-deterministic-rule-engine)
  - [2. Supervised Machine Learning (XGBoost + SHAP)](#2-supervised-machine-learning-xgboost--shap)
  - [3. Unsupervised Behavioral Anomaly (Isolation Forest)](#3-unsupervised-behavioral-anomaly-isolation-forest)
  - [4. Graph Intelligence & Network Analysis](#4-graph-intelligence--network-analysis)
- [Multi-Signal Risk Fusion Engine](#multi-signal-risk-fusion-engine)
- [Data Layer & Entity Resolution](#data-layer--entity-resolution)
- [FastAPI Investigation Backend](#fastapi-investigation-backend)
- [Next.js Investigation Workbench](#nextjs-investigation-workbench)
- [Model Evaluation & Reporting Honesty](#model-evaluation--reporting-honesty)
- [🚀 How to Run the Project (Step-by-Step Guide)](#-how-to-run-the-project-step-by-step-guide)
  - [System Prerequisites](#system-prerequisites)
  - [Quick Start (2-Minute Summary)](#quick-start-2-minute-summary)
  - [Step 1: Backend Setup & API Launch](#step-1-backend-setup--api-launch)
  - [Step 2: Frontend Setup & Dashboard Launch](#step-2-frontend-setup--dashboard-launch)
  - [Step 3: Interactive Demo Walkthrough (S19 & L19 Benchmarks)](#step-3-interactive-demo-walkthrough-s19--l19-benchmarks)
  - [Step 4: Verification & Test Suite Execution](#step-4-verification--test-suite-execution)
  - [Step 5: Data Validation & Pipeline Regeneration (Optional)](#step-5-data-validation--pipeline-regeneration-optional)
  - [Troubleshooting & FAQs](#troubleshooting--faqs)
- [Repository Structure](#repository-structure)
- [License & Acknowledgments](#license--acknowledgments)

---

## Executive Overview

Traditional AML and fraud monitoring systems evaluate financial transactions in isolation. Consequently, they remain blind to **insider collusion**, where rogue employees leverage administrative privileges to raise transfer limits, override KYC flags, disable dual authorization, or modify account profiles ahead of illicit layering or fund exfiltration.

**HackMatrix** eliminates this blind spot. By creating 100% joinable linkages across core banking transaction streams, internal IT/HR access logs, customer profiles, and counterparty transfer graphs, HackMatrix correlates administrative actions directly with financial fund movements in real time.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                 HACKMATRIX ARCHITECTURE                                  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
                                                                                            
  ┌───────────────────┐    ┌─────────────────────┐    ┌──────────────────────────────────┐  
  │ IBM AML (5M Txns) │    │ AMLSim Simulations │    │ Synthetic HR / Access Audit Logs │  
  └─────────┬─────────┘    └──────────┬──────────┘    └────────────────┬─────────────────┘  
            └──────────────────────┐  │  ┌─────────────────────────────┘                    
                                   ▼  ▼  ▼                                                  
                       ┌───────────────────────────────┐                                    
                       │ Canonical Entity Master Layer │                                    
                       │ (Accounts, Customers, Graph)  │                                    
                       └──────────────┬────────────────┘                                    
                                      │                                                     
               ┌──────────────────────┼──────────────────────┬──────────────────────┐       
               ▼                      ▼                      ▼                      ▼       
      ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
      │   Pillar 1:     │    │   Pillar 2:     │    │   Pillar 3:     │    │   Pillar 4:     │
      │  Deterministic  │    │  XGBoost + SHAP │    │ Isolation Forest│    │ Graph & Network │
      │   Rule Engine   │    │  (Un-leaked ML) │    │(Unsupervised OD)│    │  Intelligence   │
      └────────┬────────┘    └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
               │                      │                      │                      │       
               └──────────────────────┼──────────────────────┴──────────────────────┘       
                                      ▼                                                     
                        ┌───────────────────────────┐                                       
                        │ Multi-Signal Risk Fusion  │                                       
                        │ (Low / Med / High / Crit) │                                       
                        └─────────────┬─────────────┘                                       
                                      │                                                     
                                      ▼                                                     
                        ┌───────────────────────────┐                                       
                        │  FastAPI Backend Platform │                                       
                        │   (/alerts, /cases, etc.) │                                       
                        └─────────────┬─────────────┘                                       
                                      │ REST API / CORS                                     
                                      ▼                                                     
                        ┌───────────────────────────┐                                       
                        │ Next.js 15 Dark Dashboard │                                       
                        │ (Workbench, Graph, Cases) │                                       
                        └───────────────────────────┘                                       
```

---

## The Four Detection Pillars

### 1. Deterministic Rule Engine
Located in [`data/detection/`](file:///data/detection/), the rule engine evaluates operational boundary conditions and banking compliance patterns:
- **`PrivilegeChangeRule`**: Detects administrative elevation (transfer limits increased, permissions granted, KYC overrides, dual-authorization disablement, dormant activation) prior to illicit transfers. Automatically collapses dual IT audit records (`access_events` + `profile_changes`) sharing identical timestamps into a single signal.
- **`TransactionSplittingRule`**: Detects structuring/smurfing behavior (multiple transactions concentrated just below reporting thresholds like $10,000 within tight temporal windows).
- **`CircularTransferRule`**: Detects closed-loop fund transfers where capital loops through intermediate accounts and returns to the originator ($A \to B \to \dots \to A$).

### 2. Supervised Machine Learning (XGBoost + SHAP)
Located in [`data/ml/models/xgboost_classifier.py`](file:///data/ml/models/xgboost_classifier.py):
- **Feature Leakage Elimination**: Fully removed synthetic `injected_*` indicators that caused models in prior versions to learn whether an account belonged to an injected file rather than detecting real crime.
- **Clean 10-Feature Contract**: Computed over a unified transaction ledger across all account transactions:
  - `txn_density`: Transaction velocity per day of account lifespan.
  - `total_transaction_count`: Cumulative transaction count across history.
  - `max_amount_zscore`: Standardized outlier measure for maximum transaction amount.
  - `cross_currency_fraction`: Ratio of foreign currency transfers.
  - `unique_counterparties_out`: Number of distinct outbound recipient accounts.
  - `sub_threshold_fraction`: Ratio of transfers under statutory reporting thresholds ($10,000).
  - `mean_amount`: Average transaction amount across all activities.
  - `wire_fraction`: Fraction of transactions conducted via wire transfer.
  - `access_event_rate`: Internal HR/IT credential and permission modification frequency (primary SHAP driver).
  - `profile_change_rate`: Customer profile attribute modifications per day.
- **Explainability**: Tree SHAP values computed on-the-fly to show investigators exactly how much each feature contributed to the risk score.

### 3. Unsupervised Behavioral Anomaly (Isolation Forest)
Located in [`data/ml/models/isolation_forest.py`](file:///data/ml/models/isolation_forest.py):
- Unsupervised tree ensemble fitted on normalized transaction volume, velocity, and access characteristics.
- Isolates zero-day laundering and novel anomaly topologies without requiring ground truth labels.
- Outputs continuous anomaly scores $[0, 1]$ alongside dynamic threshold comparison (`is_anomaly`).

### 4. Graph Intelligence & Network Analysis
Located in [`data/graph_intel/`](file:///data/graph_intel/):
- **Structural Feature Extraction (`structural_features.py`)**: Computes in-degree, out-degree, total degree, betweenness centrality, local clustering coefficients, and bounded cycle detection (lengths 2–6) on the 25,467-node transaction graph.
- **Node2Vec Embeddings & Clustering (`embeddings.py`)**: Trains 64-dimensional topological embeddings (`walk_length=20`, `num_walks=10`, `p=1.0`, `q=0.5`) and applies DBSCAN density clustering to uncover syndicates, micro-clusters, and isolated anomalous nodes.
- **Graph Anomaly Score (`graph_anomaly_score.py`)**: Composite topological risk metric combining cycle membership (35%), betweenness rank (25%), cluster anomaly/outlier status (20%), and insider employee links (20%).
- **Multi-Hop BFS Traversal (`evidence_schema.py`)**: Recovers complete linear layering chains (e.g. 3-hop sweep scenarios like `L19`: $A \to B \to C$) using bi-directional BFS graph traversal.

---

## Multi-Signal Risk Fusion Engine

The fusion engine ([`data/risk_fusion/fuse_signals.py`](file:///data/risk_fusion/fuse_signals.py)) synthesizes the four pillars into an operational composite score:

$$\mathrm{RiskScore} = 0.16 \cdot \mathrm{RuleScore} + 0.50 \cdot P(\mathrm{XGBoost}) + 0.14 \cdot \mathrm{IForestScore} + 0.20 \cdot \mathrm{GraphAnomalyScore}$$

```python
# Exact Operational Formula in Python:
risk_score = (
    0.16 * rule_score
    + 0.50 * xgb_probability
    + 0.14 * iforest_score
    + 0.20 * graph_anomaly_score
)
```

### Operational Risk Tiers
| Tier | Score Range | Operational Action |
|:---:|:---:|:---|
| **Critical** | `[0.75, 1.00]` | Immediate account freeze, SAR filing preparation, and forensic escalation |
| **High** | `[0.55, 0.74]` | Priority investigator triage, enhanced due diligence (EDD) |
| **Medium** | `[0.30, 0.54]` | Scheduled compliance review, automated transaction monitoring alert |
| **Low** | `[0.00, 0.29]` | Baseline monitoring, no investigator action required |

### Benchmark Separation
- **S19 (Circular Transfer + Insider Threat)**: Composite $\mathrm{RiskScore} = 0.7929 \to$ **Critical Tier** ✅
- **L19 (Legitimate Multi-Hop Sweep Benchmark)**: Composite $\mathrm{RiskScore} = 0.2296 \to$ **Low Tier** ✅

---

## Data Layer & Entity Resolution

The platform operates on a multi-tiered data foundation with **100% validated join connectivity**:

| Component | Dataset Source | Size / Rows | Primary Keys & Join Links |
|---|---|---|---|
| **Transactions** | IBM AML (`HI-Small`) | 5,078,345 txns | `from_account`, `to_account` |
| **Simulations** | AMLSim | 8,297 txns, 2,000 accts | `alert_patterns.csv`, `alert_members.csv` |
| **HR & Access** | Synthetic HR Engine | 200 employees, 839 access logs | `target_account_id` $\leftrightarrow$ `from_account`/`to_account` |
| **Scenarios** | Ground Truth Benchmarks | 38 labeled prototypes (19 S, 19 L) | `account_id` $\leftrightarrow$ `from_account`/`to_account` |
| **Canonical Accounts** | `data/entities/accounts.csv` | 1,884 accounts | Master account table with pre-computed stats |
| **Canonical Customers** | `data/entities/customers.csv` | 939 customers | Master customer profile & risk rating table |
| **Unified Graph** | `data/graph/nodes.csv`, `edges.csv` | 25,467 nodes, 63,225 edges | Typed nodes (`Transaction`, `Account`, `Customer`, `Employee`) |

---

## FastAPI Investigation Backend

The backend ([`data/backend/api.py`](file:///data/backend/api.py)) provides RESTful endpoints designed for sub-second investigation latency:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/alerts` | Returns priority queue of accounts (`risk_tier >= Medium`) sorted by `risk_score` descending |
| `GET` | `/alerts/{account_id}` | Complete explainable evidence object (signals, metrics, SHAP values, risk breakdown) |
| `GET` | `/alerts/{account_id}/evidence` | Subgraph node/edge structure and chronologically correlated timeline |
| `POST` | `/cases` | Create and persist a new investigation case |
| `POST` | `/cases/{case_id}/assign` | Assign an open case to a compliance officer or investigator |
| `GET` | `/cases/{case_id}/export` | Export case file and complete evidence dossier as downloadable JSON |

---

## Next.js Investigation Workbench

The frontend (`frontend/`) is a Next.js 15 application styled with Tailwind CSS in a dark cyberpunk / fintech security theme:

- **Executive Dashboard (`/` & `/dashboard`)**: High-level risk telemetry, active priority queues, risk tier distributions, and instant jump-to-account search.
- **Alert Triage Queue (`/alerts`)**: Comprehensive filtering by risk tier, scenario type, and search queries.
- **Deep-Dive Investigation Workbench (`/investigation/[accountId]`)**:
  - **Risk Fusion Meter**: Visual gauge displaying composite score and operational tier.
  - **4-Pillar Signal Cards**: Direct inspectability into Rule flags, XGBoost SHAP waterfall drivers, Isolation Forest density, and Graph centrality.
  - **Interactive Network Subgraph**: Visual graph with color-coded nodes (`ACCT_`, `CUST_`, `EMP_`, `SYN_`) and bidirectional edge inspection.
  - **Correlated Audit Timeline**: Chronological event stream correlating employee IT access events with subsequent financial movements.
  - **One-Click Escalation**: Quick case creation with assigned reviewer tracking.
- **Case Management (`/cases`)**: Kanban/table case tracker with status progression (`New`, `In Review`, `Escalated`, `Closed`).
- **Global Network Graph (`/graph`)**: Interactive exploration of high-centrality subgraphs.

---

## Model Evaluation & Reporting Honesty

> [!IMPORTANT]
> ### Rigorous Reporting Disclosure: Calibration vs. Generalization
> The tier separation metrics (e.g. 100% of suspicious scenarios landing in High/Critical on the 38 prototypes) were achieved by **calibrating fusion weights against the 38 labeled scenarios**.
> 
> **This is operational calibration, NOT out-of-sample validation.**
> 
> To measure true generalization on unseen accounts, we evaluate the clean supervised model using **Leave-One-Scenario-Out Cross-Validation (LOSO-CV)** across all 38 folds:

### Leave-One-Scenario-Out Cross-Validation (LOSO-CV) Results

| Metric | Clean Un-Leaked Model | Description |
|---|:---:|---|
| **Features** | **10** | Clean operational features across all transactions (Zero Group X) |
| **ROC-AUC** | **0.7424 ± 0.0829** | True generalizing discriminatory performance |
| **PR-AUC** | **0.7160** | Balanced precision-recall curve area |
| **Precision @ 0.50** | **0.6875 ± 0.1220** | Out-of-sample precision |
| **Recall @ 0.50** | **0.5789 ± 0.1180** | Pre-fusion independent ML capture |
| **F1-Score** | **0.6286 ± 0.0988** | Balanced F-measure |
| **Top SHAP Driver** | `access_event_rate` (0.8575) | Correlates internal privilege abuse with financial risk |

*Full evaluation reports and methodology details are documented in [`data/models/RESULTS.md`](file:///data/models/RESULTS.md).*

---

## 🚀 How to Run the Project (Step-by-Step Guide)

Follow this walkthrough to run both the FastAPI backend and Next.js frontend on your local machine.

### System Prerequisites
Ensure you have the following installed on your machine:
- **Python**: `3.10` or higher (tested on Python 3.10, 3.11, and 3.12)
- **Node.js**: `18.17` or higher (Recommended: Node 20 LTS)
- **Git**

---

### Quick Start (2-Minute Summary)

Open two terminal windows:

```bash
# Terminal 1 — Backend API
pip install -r requirements.txt
uvicorn data.backend.api:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — Frontend UI
cd frontend
npm install
npm run dev
```

Open **`http://localhost:3000`** in your browser!

---

### Step 1: Backend Setup & API Launch

1. **Clone the repository** (if not already local):
   ```bash
   git clone https://github.com/GauravJaypatre/HackMatrix.git
   cd HackMatrix
   ```

2. **Create and activate a Python virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (Command Prompt)**:
     ```cmd
     python -m venv venv
     .\venv\Scripts\activate.bat
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Python backend dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the FastAPI backend server**:
   ```bash
   uvicorn data.backend.api:app --reload --host 127.0.0.1 --port 8000
   ```

5. **Verify Backend Health**:
   - Open your browser to **`http://127.0.0.1:8000/docs`** to view the interactive OpenAPI / Swagger UI.
   - Test the alerts endpoint:
     ```bash
     curl http://127.0.0.1:8000/alerts
     ```

---

### Step 2: Frontend Setup & Dashboard Launch

1. **Open a new terminal** and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. **Install Node dependencies**:
   ```bash
   npm install
   ```

3. **Start the Next.js development server**:
   ```bash
   npm run dev
   ```

4. **Open the Application**:
   Navigate to **`http://localhost:3000`** in your web browser. You will see the HackMatrix investigation dashboard.

---

### Step 3: Interactive Demo Walkthrough (S19 & L19 Benchmarks)

Once both servers are running, test these critical scenarios to experience the multi-signal detection engine live:

#### 1. Executive Dashboard
- **URL**: `http://localhost:3000`
- **What to observe**: Active risk metrics, priority queue of high-risk accounts, risk tier distribution bar chart, and quick-search launcher.

#### 2. Suspicious Circular Ring & Insider Scenario (`S19`)
- **Direct Link**: **`http://localhost:3000/investigation/800085BF0`**
- **What to observe**:
  - **Risk Score**: `0.7929` $\to$ **Critical Tier** (highlighted in red/rose).
  - **Rule Signal**: Flagged for `INSIDER.PRIVILEGE_CHANGE` and `AML.CIRCULAR_TRANSFER`.
  - **XGBoost ML**: Probability `84.78%`, with Tree SHAP showing `access_event_rate` as the dominant fraud driver.
  - **Graph Intelligence**: `Cycle Member: YES`, Degree: `431`, DBSCAN cluster: `45` (13 accounts).
  - **Interactive Subgraph**: Zoom and inspect the circular flow topology linking accounts and employee `EMP_0047`.
  - **Correlated Timeline**: Note the administrative privilege escalation occurring immediately before the circular transactions.

#### 3. Legitimate Multi-Hop Sweep Scenario (`L19`)
- **Direct Link**: **`http://localhost:3000/investigation/80026A5A0`**
- **What to observe**:
  - **Risk Score**: `0.2296` $\to$ **Low Tier** (classified legitimate).
  - **Cycle Member**: `NO` (correctly distinguishes a linear sweep from a closed ring).
  - **XGBoost ML**: Probability `14.54%` (unflagged).
  - **Multi-Hop Traversal**: Discovers all 3 linear accounts in the chain (`80026A5A0 -> 80035F420 -> 8001E34C0`).

#### 4. Case Management & Dossier Export
- **URL**: `http://localhost:3000/cases`
- Click **"Create Case"** from any investigation page to escalate an account.
- Assign an investigator and export the complete evidence dossier as structured JSON.

---

### Step 4: Verification & Test Suite Execution

Run the complete backend test suite to verify all rules, machine learning components, feature pipelines, and API schemas:

```bash
# Run pytest with concise summary
pytest -q
```

Expected output:
```text
.............................................................. [ 84%]
...........                                                    [100%]
73 passed, 10 subtests passed in ~23s
```

To run individual test modules:
```bash
# Deterministic rule tests
pytest data/detection/tests/

# Machine learning & XGBoost un-leaked feature tests
pytest data/ml/tests/
```

---

### Step 5: Data Validation & Pipeline Regeneration (Optional)

#### 1. Validate All Cross-Dataset Join Keys
Run the join validator anytime to verify 100% integrity across IBM AML, HR records, and scenarios:
```bash
python data/validate_joins.py
```

#### 2. Re-compute Risk Fusion Scores
If you adjust formula weights in `data/risk_fusion/fuse_signals.py`:
```bash
python data/risk_fusion/fuse_signals.py
```

#### 3. Re-train XGBoost Model (Un-leaked 10-Feature Contract)
```bash
python data/ml/models/xgboost_classifier.py
```

---

### Troubleshooting & FAQs

- **Port 8000 already in use**:
  Run uvicorn on another port:
  ```bash
  uvicorn data.backend.api:app --reload --port 8080
  ```
  *(Remember to update `frontend/src/lib/api.ts` if changing backend port)*.
- **Port 3000 already in use**:
  Next.js will automatically prompt to run on port 3001, or run:
  ```bash
  npm run dev -- -p 3001
  ```
- **CORS Errors**:
  The FastAPI backend is pre-configured with open CORS middleware (`allow_origins=["*"]`) so frontend requests from `localhost:3000` work seamlessly out of the box.

---

## Repository Structure

```text
HackMatrix/
├── data/
│   ├── amlsim/                     # Synthetic AML simulation dataset & patterns
│   ├── backend/                    # FastAPI server & evidence schema builder
│   │   ├── api.py                  # REST API implementation
│   │   ├── evidence_schema.py      # Multi-hop BFS traversal & evidence assembler
│   │   └── cases_store.json        # Persistent investigation cases store
│   ├── detection/                  # Deterministic compliance rule engine
│   │   ├── engine.py               # Rule orchestration engine
│   │   ├── rules/                  # PrivilegeChange, TransactionSplitting, CircularTransfer
│   │   └── tests/                  # Unit tests for detection rules
│   ├── entities/                   # Canonical master accounts & customers records
│   ├── graph/                      # Unified transaction graph (nodes.csv, edges.csv)
│   ├── graph_intel/                # Graph intelligence & network embeddings
│   │   ├── structural_features.py  # Centrality, cycle detection, degree metrics
│   │   ├── embeddings.py           # Node2Vec 64D embeddings & DBSCAN clustering
│   │   └── graph_anomaly_score.py  # Composite graph risk calculation
│   ├── ibm_aml/                    # Raw IBM AML dataset cleaning & schemas
│   ├── ml/                         # Machine learning models & feature store
│   │   ├── features/               # Account feature extraction & store
│   │   ├── models/                 # XGBoost classifier & Isolation Forest
│   │   └── tests/                  # ML test suite
│   ├── models/                     # Production model artifacts & RESULTS.md
│   ├── risk_fusion/                # Multi-signal risk fusion engine
│   │   ├── fuse_signals.py         # 4-pillar formula & risk tier mapper
│   │   └── scenario_risk_scores.csv# Calibrated scores for 38 prototypes
│   ├── synthetic_hr/               # HR roster, access logs, and 38 labeled scenarios
│   └── validate_joins.py           # Cross-dataset join validation script
├── frontend/                       # Next.js 15 Dark Cyberpunk Investigation Dashboard
│   ├── src/
│   │   ├── app/                    # Next.js App Router (dashboard, alerts, investigation)
│   │   ├── components/             # Reusable UI components (ScoreGauge, SignalCard, Graph)
│   │   ├── lib/                    # API client utilities
│   │   └── types/                  # TypeScript interface contracts matching backend
│   ├── package.json
│   └── tsconfig.json
├── HANDOFF_NOTES.md                # System integration and architecture notes
├── requirements.txt                # Python backend dependencies
└── README.md                       # Master project documentation
```

---

## License & Acknowledgments

- **IBM AML Data**: Derived from the [IBM Transactions for Anti-Money Laundering (AML)](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml) dataset.
- **AMLSim**: Synthetic transaction simulation patterns inspired by IBM Research AMLSim.
- **HackMatrix Team**: Built for the FIN04 Financial Crime & Insider Threat Challenge.
