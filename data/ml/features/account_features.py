"""Account-level feature extraction for ML anomaly detection.

Extracts feature groups A-E and experimental group X strictly from raw data tables,
with mandatory explicit leakage exclusion.
"""

from typing import Any, Dict, List, Optional, Set
import numpy as np
import pandas as pd

# Strict leakage exclusion list per ML pipeline design
LEAKAGE_EXCLUSIONS: Set[str] = {
    "expected_signals",
    "scenario_type",
    "scenario_id",
    "is_laundering",
    "is_sar",
    "alert_id",
    "source",
    "is_synthetic",
    "related_event_ids",
    "related_transaction_ids",
    "description",
    "has_transactional_consequence",
}

FEATURE_GROUPS: Dict[str, List[str]] = {
    "group_a": [
        "real_txn_count",
        "synthetic_txn_count",
        "total_transaction_count",
        "has_linked_customer",
        "bank_id_encoded",
        "account_age_days",
        "activity_span_days",
        "txn_density",
        "synthetic_fraction",
        "background_real_laundering_count",
    ],
    "group_b": [
        "mean_amount",
        "std_amount",
        "max_amount",
        "min_amount",
        "wire_fraction",
        "ach_fraction",
        "cross_currency_fraction",
        "cross_bank_ratio",
        "unique_counterparties_out",
        "unique_counterparties_in",
        "total_sent_amount",
        "total_received_amount",
        "sub_threshold_fraction",
        "amount_cv",
        "counterparty_diversity",
        "max_amount_zscore",
    ],
    "group_c": [
        "access_event_count",
        "modify_count",
        "revoke_count",
        "grant_count",
        "unique_employee_accessors",
        "access_event_rate",
    ],
    "group_d": [
        "profile_change_count",
        "high_risk_field_change_count",
        "limit_field_change_count",
        "unique_profile_change_employees",
        "profile_change_rate",
    ],
    "group_e": [
        "managing_employee_count",
        "has_approver",
        "has_account_manager",
    ],
    "group_f": [
        "risk_rating_encoded",
        "country_encoded",
    ],
    "group_g": [
        "privilege_change_triggered",
        "circular_transfer_triggered",
        "transaction_splitting_triggered",
    ],
    "group_x": [
        "injected_txn_count",
        "injected_mean_amount",
        "injected_sub_threshold_fraction",
        "injected_wire_fraction",
    ],
}


def sanitize_input_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Drop any leakage columns before any feature construction."""
    cols_to_drop = [c for c in df.columns if c in LEAKAGE_EXCLUSIONS]
    if cols_to_drop:
        return df.drop(columns=cols_to_drop).copy()
    return df.copy()


def compute_group_a_features(accounts_df: pd.DataFrame) -> pd.DataFrame:
    """Compute Group A: Entity / Account Base features.

    Source: data/entities/accounts.csv
    """
    clean_df = sanitize_input_dataframe(accounts_df)
    features = pd.DataFrame(index=clean_df["account_id"].astype(str))

    features["real_txn_count"] = pd.to_numeric(clean_df["real_txn_count"], errors="coerce").fillna(0.0).values
    features["synthetic_txn_count"] = pd.to_numeric(clean_df["synthetic_txn_count"], errors="coerce").fillna(0.0).values
    features["total_transaction_count"] = pd.to_numeric(clean_df["total_transaction_count"], errors="coerce").fillna(0.0).values

    features["has_linked_customer"] = clean_df["linked_customer_id"].notna().astype(float).values
    features["bank_id_encoded"] = pd.to_numeric(clean_df["bank_id"], errors="coerce").fillna(0.0).values

    first_ts = pd.to_datetime(clean_df["first_seen_timestamp"], errors="coerce")
    last_ts = pd.to_datetime(clean_df["last_seen_timestamp"], errors="coerce")
    age_days = (last_ts - first_ts).dt.total_seconds() / 86400.0
    age_days = age_days.clip(lower=0.0).fillna(0.0)
    features["account_age_days"] = age_days.values
    features["activity_span_days"] = age_days.values

    # Density = total_transaction_count / (account_age_days + 1.0)
    features["txn_density"] = features["total_transaction_count"] / (features["account_age_days"] + 1.0)

    # Synthetic fraction = synthetic_txn_count / max(1, total_transaction_count)
    denom = np.maximum(features["total_transaction_count"].values, 1.0)
    features["synthetic_fraction"] = features["synthetic_txn_count"].values / denom

    # Permitted for Isolation Forest unsupervised normality modeling
    features["background_real_laundering_count"] = pd.to_numeric(
        clean_df.get("background_real_laundering_count", 0.0), errors="coerce"
    ).fillna(0.0).values

    return features


def compute_group_b_features(
    real_tx_df: pd.DataFrame,
    accounts_index: pd.Index,
    total_tx_counts: pd.Series,
) -> pd.DataFrame:
    """Compute Group B: Real Transaction Aggregates.

    Source: data/entities/in_scope_real_transactions.csv
    Aggregates per account (sender and receiver views).
    """
    clean_tx = sanitize_input_dataframe(real_tx_df)
    clean_tx["from_account"] = clean_tx["from_account"].astype(str)
    clean_tx["to_account"] = clean_tx["to_account"].astype(str)
    clean_tx["amount_paid"] = pd.to_numeric(clean_tx["amount_paid"], errors="coerce").fillna(0.0)

    # Dataset level statistics for zscore
    dataset_mean_amt = float(clean_tx["amount_paid"].mean()) if len(clean_tx) > 0 else 0.0
    dataset_std_amt = float(clean_tx["amount_paid"].std()) if len(clean_tx) > 1 else 1.0
    if dataset_std_amt <= 0.0:
        dataset_std_amt = 1.0

    # Sender-side calculations
    grouped_from = clean_tx.groupby("from_account")

    mean_amt = grouped_from["amount_paid"].mean()
    std_amt = grouped_from["amount_paid"].std().fillna(0.0)
    max_amt = grouped_from["amount_paid"].max()
    min_amt = grouped_from["amount_paid"].min()
    total_sent = grouped_from["amount_paid"].sum()
    unique_counterparties_out = grouped_from["to_account"].nunique()

    wire_mask = clean_tx["payment_format"].astype(str).str.lower() == "wire"
    wire_counts = clean_tx[wire_mask].groupby("from_account")["transaction_id"].count()

    ach_mask = clean_tx["payment_format"].astype(str).str.lower() == "ach"
    ach_counts = clean_tx[ach_mask].groupby("from_account")["transaction_id"].count()

    cross_curr_mask = clean_tx["payment_currency"].astype(str).str.lower() != "us dollar"
    cross_curr_counts = clean_tx[cross_curr_mask].groupby("from_account")["transaction_id"].count()

    cross_bank_mask = clean_tx["from_bank"].astype(str) != clean_tx["to_bank"].astype(str)
    cross_bank_counts = clean_tx[cross_bank_mask].groupby("from_account")["transaction_id"].count()

    sub_thresh_mask = clean_tx["amount_paid"] < 10000.0
    sub_thresh_counts = clean_tx[sub_thresh_mask].groupby("from_account")["transaction_id"].count()

    sender_tx_count = grouped_from["transaction_id"].count()

    # Receiver-side calculations
    grouped_to = clean_tx.groupby("to_account")
    total_received = grouped_to["amount_paid"].sum()
    unique_counterparties_in = grouped_to["from_account"].nunique()

    # Build DataFrame aligned to accounts_index
    features = pd.DataFrame(index=accounts_index)

    features["mean_amount"] = mean_amt.reindex(accounts_index).fillna(0.0)
    features["std_amount"] = std_amt.reindex(accounts_index).fillna(0.0)
    features["max_amount"] = max_amt.reindex(accounts_index).fillna(0.0)
    features["min_amount"] = min_amt.reindex(accounts_index).fillna(0.0)

    n_sender = sender_tx_count.reindex(accounts_index).fillna(0.0)
    safe_n_sender = np.maximum(n_sender.values, 1.0)

    features["wire_fraction"] = np.where(n_sender.values > 0, wire_counts.reindex(accounts_index).fillna(0.0).values / safe_n_sender, 0.0)
    features["ach_fraction"] = np.where(n_sender.values > 0, ach_counts.reindex(accounts_index).fillna(0.0).values / safe_n_sender, 0.0)
    features["cross_currency_fraction"] = np.where(n_sender.values > 0, cross_curr_counts.reindex(accounts_index).fillna(0.0).values / safe_n_sender, 0.0)
    features["cross_bank_ratio"] = np.where(n_sender.values > 0, cross_bank_counts.reindex(accounts_index).fillna(0.0).values / safe_n_sender, 0.0)
    features["unique_counterparties_out"] = unique_counterparties_out.reindex(accounts_index).fillna(0.0)
    features["unique_counterparties_in"] = unique_counterparties_in.reindex(accounts_index).fillna(0.0)
    features["total_sent_amount"] = total_sent.reindex(accounts_index).fillna(0.0)
    features["total_received_amount"] = total_received.reindex(accounts_index).fillna(0.0)
    features["sub_threshold_fraction"] = np.where(n_sender.values > 0, sub_thresh_counts.reindex(accounts_index).fillna(0.0).values / safe_n_sender, 0.0)

    # Coefficient of variation = std_amount / (mean_amount + 1e-6)
    features["amount_cv"] = features["std_amount"] / (features["mean_amount"] + 1e-6)

    # Counterparty diversity = unique_counterparties_out / (total_transaction_count + 1e-6)
    denom_tx = np.maximum(total_tx_counts.reindex(accounts_index).fillna(0.0).values, 1.0)
    features["counterparty_diversity"] = features["unique_counterparties_out"].values / denom_tx

    # Z-score of max amount relative to global transaction distribution
    features["max_amount_zscore"] = (features["max_amount"] - dataset_mean_amt) / dataset_std_amt

    return features


def compute_group_c_features(
    access_events_df: pd.DataFrame,
    accounts_index: pd.Index,
    account_age_series: pd.Series,
) -> pd.DataFrame:
    """Compute Group C: Access Event Aggregates.

    Source: data/synthetic_hr/access_events.csv
    Aggregates per target_account_id.
    """
    clean_ae = sanitize_input_dataframe(access_events_df)
    clean_ae["target_account_id"] = clean_ae["target_account_id"].astype(str)

    grouped = clean_ae.groupby("target_account_id")

    event_count = grouped["event_id"].count()

    action_lower = clean_ae["action"].astype(str).str.lower()
    modify_counts = clean_ae[action_lower == "modify"].groupby("target_account_id")["event_id"].count()
    revoke_counts = clean_ae[action_lower == "revoke"].groupby("target_account_id")["event_id"].count()
    grant_counts = clean_ae[action_lower == "grant"].groupby("target_account_id")["event_id"].count()
    unique_accessors = grouped["employee_id"].nunique()

    features = pd.DataFrame(index=accounts_index)
    features["access_event_count"] = event_count.reindex(accounts_index).fillna(0.0)
    features["modify_count"] = modify_counts.reindex(accounts_index).fillna(0.0)
    features["revoke_count"] = revoke_counts.reindex(accounts_index).fillna(0.0)
    features["grant_count"] = grant_counts.reindex(accounts_index).fillna(0.0)
    features["unique_employee_accessors"] = unique_accessors.reindex(accounts_index).fillna(0.0)

    # Rate per account age day
    age_days = account_age_series.reindex(accounts_index).fillna(0.0).values
    features["access_event_rate"] = features["access_event_count"].values / (age_days + 1.0)

    return features


def compute_group_d_features(
    profile_changes_df: pd.DataFrame,
    accounts_index: pd.Index,
    account_age_series: pd.Series,
) -> pd.DataFrame:
    """Compute Group D: Profile Change Aggregates.

    Source: data/synthetic_hr/profile_changes.csv
    Aggregates per customer_id (= account_id).
    """
    clean_pc = sanitize_input_dataframe(profile_changes_df)
    clean_pc["customer_id"] = clean_pc["customer_id"].astype(str)

    grouped = clean_pc.groupby("customer_id")
    change_count = grouped["change_id"].count()

    high_risk_fields = {
        "spending_limit",
        "wire_transfer_limit",
        "risk_rating",
        "beneficial_owner",
        "account_type",
    }
    field_lower = clean_pc["field_changed"].astype(str).str.lower()
    high_risk_mask = field_lower.isin(high_risk_fields)
    high_risk_counts = clean_pc[high_risk_mask].groupby("customer_id")["change_id"].count()

    limit_fields = {"spending_limit", "wire_transfer_limit"}
    limit_mask = field_lower.isin(limit_fields)
    limit_counts = clean_pc[limit_mask].groupby("customer_id")["change_id"].count()

    unique_employees = grouped["changed_by_employee_id"].nunique()

    features = pd.DataFrame(index=accounts_index)
    features["profile_change_count"] = change_count.reindex(accounts_index).fillna(0.0)
    features["high_risk_field_change_count"] = high_risk_counts.reindex(accounts_index).fillna(0.0)
    features["limit_field_change_count"] = limit_counts.reindex(accounts_index).fillna(0.0)
    features["unique_profile_change_employees"] = unique_employees.reindex(accounts_index).fillna(0.0)

    age_days = account_age_series.reindex(accounts_index).fillna(0.0).values
    features["profile_change_rate"] = features["profile_change_count"].values / (age_days + 1.0)

    return features


def compute_group_e_features(
    employee_map_df: pd.DataFrame,
    accounts_index: pd.Index,
) -> pd.DataFrame:
    """Compute Group E: Employee Relationship Features.

    Source: data/synthetic_hr/employee_customer_map.csv
    Aggregates per customer_id (= account_id).
    """
    clean_em = sanitize_input_dataframe(employee_map_df)
    clean_em["customer_id"] = clean_em["customer_id"].astype(str)

    grouped = clean_em.groupby("customer_id")
    managing_emp_count = grouped["employee_id"].nunique()

    rel_lower = clean_em["relationship_type"].astype(str).str.lower()
    approver_customers = set(clean_em[rel_lower == "approver"]["customer_id"])
    mgr_customers = set(clean_em[rel_lower == "account_manager"]["customer_id"])

    features = pd.DataFrame(index=accounts_index)
    features["managing_employee_count"] = managing_emp_count.reindex(accounts_index).fillna(0.0)
    features["has_approver"] = accounts_index.isin(approver_customers).astype(float)
    features["has_account_manager"] = accounts_index.isin(mgr_customers).astype(float)

    return features


def compute_group_x_features(
    injected_df: pd.DataFrame,
    accounts_index: pd.Index,
) -> pd.DataFrame:
    """Compute Group X: EXPERIMENTAL Injected Transaction Features.

    Source: data/synthetic_hr/injected_transactions.csv
    Aggregates per from_account.
    Explicitly drops scenario_id, source, is_laundering.
    """
    clean_inj = sanitize_input_dataframe(injected_df)
    clean_inj["from_account"] = clean_inj["from_account"].astype(str)
    clean_inj["amount_paid"] = pd.to_numeric(clean_inj["amount_paid"], errors="coerce").fillna(0.0)

    grouped = clean_inj.groupby("from_account")
    inj_count = grouped["transaction_id"].count()
    inj_mean = grouped["amount_paid"].mean()

    sub_thresh_mask = clean_inj["amount_paid"] < 10000.0
    sub_thresh_counts = clean_inj[sub_thresh_mask].groupby("from_account")["transaction_id"].count()

    wire_mask = clean_inj["payment_format"].astype(str).str.lower() == "wire"
    wire_counts = clean_inj[wire_mask].groupby("from_account")["transaction_id"].count()

    features = pd.DataFrame(index=accounts_index)
    features["injected_txn_count"] = inj_count.reindex(accounts_index).fillna(0.0)
    features["injected_mean_amount"] = inj_mean.reindex(accounts_index).fillna(0.0)

    counts = features["injected_txn_count"].values
    safe_counts = np.maximum(counts, 1.0)
    features["injected_sub_threshold_fraction"] = np.where(
        counts > 0,
        sub_thresh_counts.reindex(accounts_index).fillna(0.0).values / safe_counts,
        0.0,
    )
    features["injected_wire_fraction"] = np.where(
        counts > 0,
        wire_counts.reindex(accounts_index).fillna(0.0).values / safe_counts,
        0.0,
    )

    return features


def compute_group_f_features(
    customers_df: pd.DataFrame,
    accounts_df: pd.DataFrame,
    accounts_index: pd.Index,
) -> pd.DataFrame:
    """Compute Group F: Customer features (risk_rating, country).

    Source: data/entities/customers.csv mapped via accounts.csv linked_customer_id.
    """
    clean_cust = sanitize_input_dataframe(customers_df)
    clean_acc = sanitize_input_dataframe(accounts_df)

    clean_acc["account_id"] = clean_acc["account_id"].astype(str)
    clean_cust["customer_id"] = clean_cust["customer_id"].astype(str)

    merged = clean_acc[["account_id", "linked_customer_id"]].merge(
        clean_cust[["customer_id", "risk_rating", "country"]],
        left_on="linked_customer_id",
        right_on="customer_id",
        how="left",
    ).set_index("account_id")

    risk_map = {"low": 0.0, "medium": 1.0, "high": 2.0}
    all_countries = sorted(clean_cust["country"].dropna().unique())
    country_map = {c: float(i + 1) for i, c in enumerate(all_countries)}

    features = pd.DataFrame(index=accounts_index)
    risk_col = merged["risk_rating"].astype(str).str.lower().map(risk_map).reindex(accounts_index).fillna(0.0)
    country_col = merged["country"].map(country_map).reindex(accounts_index).fillna(0.0)

    features["risk_rating_encoded"] = risk_col.values
    features["country_encoded"] = country_col.values
    return features


def compute_group_g_features(
    rule_results: List[Any],
    accounts_index: pd.Index,
) -> pd.DataFrame:
    """Compute Group G: Deterministic Rule Engine signal flags.

    Source: Results from RuleEngine execution.
    """
    acc_priv: Set[str] = set()
    acc_circ: Set[str] = set()
    acc_split: Set[str] = set()

    for r in rule_results:
        if not getattr(r, "triggered", False):
            continue
        rule_id = getattr(r, "rule_id", "")
        acc_id = getattr(r, "account_id", None)
        if not acc_id:
            continue
        acc_str = str(acc_id)
        if rule_id == "INSIDER.PRIVILEGE_CHANGE":
            acc_priv.add(acc_str)
        elif rule_id == "AML.CIRCULAR_TRANSFER":
            acc_circ.add(acc_str)
        elif rule_id == "AML.TRANSACTION_SPLITTING":
            acc_split.add(acc_str)

    features = pd.DataFrame(index=accounts_index)
    features["privilege_change_triggered"] = accounts_index.isin(acc_priv).astype(float)
    features["circular_transfer_triggered"] = accounts_index.isin(acc_circ).astype(float)
    features["transaction_splitting_triggered"] = accounts_index.isin(acc_split).astype(float)
    return features


def extract_all_features(
    accounts_df: pd.DataFrame,
    real_tx_df: pd.DataFrame,
    access_events_df: pd.DataFrame,
    profile_changes_df: pd.DataFrame,
    employee_map_df: pd.DataFrame,
    injected_tx_df: pd.DataFrame,
    customers_df: Optional[pd.DataFrame] = None,
    rule_results: Optional[List[Any]] = None,
    include_experimental_group_x: bool = False,
    include_group_f: bool = False,
    include_group_g: bool = False,
    for_xgboost: bool = False,
) -> pd.DataFrame:
    """Extract and merge all feature groups for all accounts."""
    df_a = compute_group_a_features(accounts_df)
    accounts_idx = df_a.index
    total_tx_counts = df_a["total_transaction_count"]
    age_days = df_a["account_age_days"]

    df_b = compute_group_b_features(real_tx_df, accounts_idx, total_tx_counts)
    df_c = compute_group_c_features(access_events_df, accounts_idx, age_days)
    df_d = compute_group_d_features(profile_changes_df, accounts_idx, age_days)
    df_e = compute_group_e_features(employee_map_df, accounts_idx)

    frames = [df_a, df_b, df_c, df_d, df_e]

    if include_group_f and customers_df is not None:
        df_f = compute_group_f_features(customers_df, accounts_df, accounts_idx)
        frames.append(df_f)

    if include_group_g and rule_results is not None:
        df_g = compute_group_g_features(rule_results, accounts_idx)
        frames.append(df_g)

    if include_experimental_group_x:
        df_x = compute_group_x_features(injected_tx_df, accounts_idx)
        frames.append(df_x)

    feature_matrix = pd.concat(frames, axis=1)

    # For XGBoost: exclude background_real_laundering_count per design
    if for_xgboost and "background_real_laundering_count" in feature_matrix.columns:
        feature_matrix = feature_matrix.drop(columns=["background_real_laundering_count"])

    # Double check no leakage columns exist
    leakage_present = set(feature_matrix.columns).intersection(LEAKAGE_EXCLUSIONS)
    if leakage_present:
        raise ValueError(f"Leakage columns detected in feature matrix: {leakage_present}")

    # Fill any remaining NaNs with 0.0
    feature_matrix = feature_matrix.fillna(0.0)

    return feature_matrix
