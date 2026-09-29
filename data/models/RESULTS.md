# XGBoost AML Detection Model Evaluation & Un-leaked Results

## 1. Feature Leakage Vulnerability & Resolution

### The Vulnerability
In previous iterations, the XGBoost supervised model feature set included experimental Group X features:
- `injected_txn_count`
- `injected_mean_amount`
- `injected_sub_threshold_fraction`
- `injected_wire_fraction`

These features were computed exclusively from `injected_transactions.csv` (the synthetic scenario injection ledger). Because all 1,846 real background accounts had 0 injected transactions by definition, the classifier learned a trivial shortcut distinguishing whether an account was part of an injected scenario file rather than detecting genuine financial crime patterns. This produced artificially inflated validation scores but rendered the model ineffective on unseen accounts.

### The Fix
1. **Complete Removal of Leaked Features**: Removed `compute_group_x_features()` and all `injected_*` feature columns from the feature store and model contract.
2. **Unified Transaction Ledger**: Replaced transaction-level indicators with equivalents computed over ALL transactions (real + synthetic unified into a single ledger with no indicators of origin):
   - `injected_mean_amount` $\rightarrow$ `mean_amount` (across all transactions)
   - `injected_wire_fraction` $\rightarrow$ `wire_fraction` (across all transactions)
   - `injected_sub_threshold_fraction` $\rightarrow$ `sub_threshold_fraction` (across all transactions)
   - `injected_txn_count` $\rightarrow$ `total_transaction_count` (across all transactions)
3. **Core Behavioral Signal Contract**: The final 10-feature contract focuses on operational risk indicators across Groups A, B, C, and D:
   - Group A: `txn_density`, `total_transaction_count`
   - Group B: `max_amount_zscore`, `cross_currency_fraction`, `unique_counterparties_out`, `sub_threshold_fraction`, `mean_amount`, `wire_fraction`
   - Group C: `access_event_rate` (top SHAP driver for insider threat)
   - Group D: `profile_change_rate`
4. **Deterministic Rule Independence**: Group G rule flags (`privilege_change_triggered`, `circular_transfer_triggered`, `transaction_splitting_triggered`) are excluded from XGBoost inputs to maintain strict statistical independence for downstream risk fusion.

---

## 2. Honest Generalization Performance (Leave-One-Scenario-Out Cross-Validation)

Evaluated under strict Leave-One-Scenario-Out cross-validation (LOSO-CV) across all 38 labeled accounts (19 suspicious, 19 legitimate):

| Metric | Selected Signal Model (10 Un-leaked Features) | Historical Baseline (41 Features) | Historical Approved (44 Features) |
|---|---|---|---|
| **ROC-AUC** | **0.7424 ± 0.0829** | 0.8089 ± 0.0707 | 0.7922 ± 0.0743 |
| **PR-AUC** | **0.7160** | 0.7340 | 0.7510 |
| **Precision @ Cutoff (0.50)** | **0.6875 ± 0.1220** | 0.6842 ± 0.1111 | 0.7222 ± 0.1103 |
| **Recall @ Cutoff (0.50)** | **0.5789 ± 0.1180** | 0.6842 ± 0.1111 | 0.6842 ± 0.1111 |
| **F1-Score** | **0.6286 ± 0.0988** | 0.6842 ± 0.0888 | 0.7027 ± 0.0879 |
| **Accuracy** | **0.6579** | 0.6842 | 0.7105 |

### Scenario Prototype Predictions (OOF Holdout)
- **S19 (Circular Transfer Ring)**:
  - True Label: `1` (Suspicious)
  - LOSO Predicted Probability: `0.8050`
  - Fixed Holdout Probability (trained on 36 accounts): `0.8082`
  - Classification: **CORRECT**
- **L19 (Multi-hop Sweep Benchmark)**:
  - True Label: `0` (Legitimate)
  - LOSO Predicted Probability: `0.2257`
  - Fixed Holdout Probability (trained on 36 accounts): `0.2409`
  - Classification: **CORRECT**

### Top SHAP Feature Drivers
1. `access_event_rate`: **0.8575** (Primary insider access frequency driver)
2. `max_amount_zscore`: **0.4860** (High-value transaction anomaly)
3. `unique_counterparties_out`: **0.2923** (Breadth of counterparties)
4. `mean_amount`: **0.1682** (Average transaction size)
5. `txn_density`: **0.0669** (Transaction velocity)

---

## 3. Critical Methodological Notice: In-Sample Calibration Warning

> [!WARNING]
> **EXPLICIT WARNING FOR PRESENTATION TO JUDGES AND STAKEHOLDERS:**
> 
> **Any multi-signal risk fusion tier separation or performance metrics (e.g., 100% detection rate on the 38 labeled prototypes, or 0% false positives on calibration benchmarks) achieved in `data/risk_fusion/scenario_risk_scores.csv` represent IN-SAMPLE CALIBRATION, NOT out-of-sample validation.**
> 
> The fusion weights ($0.16 \cdot \text{Rule} + 0.50 \cdot \text{XGB} + 0.14 \cdot \text{IForest} + 0.20 \cdot \text{Graph}$) were calibrated directly on the 38 labeled scenario accounts. **Do NOT present calibration separation numbers as an out-of-sample generalization or model accuracy metric.**
> 
> Only the LOSO-CV metrics reported in Section 2 above (ROC-AUC 0.7424, PR-AUC 0.7160) reflect true out-of-sample generalization on unseen account activity.
