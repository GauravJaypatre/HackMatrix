"""Account-level feature store and dataset partitioner for HackMatrix ML models."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from data.ml.features.account_features import (
    FEATURE_GROUPS,
    LEAKAGE_EXCLUSIONS,
    extract_all_features,
)
from data.detection.validate_against_ground_truth import (
    build_engine,
    load_rule_configuration,
    load_runtime_context,
)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2]


class FeatureStore:
    """Manages raw dataset loading, leakage-safe feature matrix creation, and evaluation partitioning."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self._accounts_df: Optional[pd.DataFrame] = None
        self._customers_df: Optional[pd.DataFrame] = None
        self._real_tx_df: Optional[pd.DataFrame] = None
        self._access_events_df: Optional[pd.DataFrame] = None
        self._profile_changes_df: Optional[pd.DataFrame] = None
        self._employee_map_df: Optional[pd.DataFrame] = None
        self._injected_tx_df: Optional[pd.DataFrame] = None
        self._labeled_scenarios_df: Optional[pd.DataFrame] = None
        self._rule_results: Optional[List[Any]] = None

        self._cached_feature_matrix: Dict[Tuple[bool, bool, bool, bool], pd.DataFrame] = {}

    def load_raw_data(self) -> None:
        """Load all source data files required for feature computation."""
        entities_dir = self.data_dir / "entities"
        synthetic_dir = self.data_dir / "synthetic_hr"

        self._accounts_df = pd.read_csv(entities_dir / "accounts.csv", dtype={"account_id": str})
        self._customers_df = pd.read_csv(entities_dir / "customers.csv", dtype={"customer_id": str})
        self._real_tx_df = pd.read_csv(
            entities_dir / "in_scope_real_transactions.csv",
            dtype={"from_account": str, "to_account": str},
        )
        self._access_events_df = pd.read_csv(
            synthetic_dir / "access_events.csv",
            dtype={"target_account_id": str, "employee_id": str},
        )
        self._profile_changes_df = pd.read_csv(
            synthetic_dir / "profile_changes.csv",
            dtype={"customer_id": str, "changed_by_employee_id": str},
        )
        self._employee_map_df = pd.read_csv(
            synthetic_dir / "employee_customer_map.csv",
            dtype={"customer_id": str, "employee_id": str},
        )
        self._injected_tx_df = pd.read_csv(
            synthetic_dir / "injected_transactions.csv",
            dtype={"from_account": str, "to_account": str},
        )
        self._labeled_scenarios_df = pd.read_csv(
            synthetic_dir / "labeled_scenarios.csv",
            dtype=str,
        )

    def get_rule_results(self) -> List[Any]:
        """Run or return cached deterministic RuleEngine results."""
        if self._rule_results is None:
            engine = build_engine()
            context = load_runtime_context()
            cfg = load_rule_configuration()
            outcome = engine.run(context, cfg)
            self._rule_results = outcome.results
        return self._rule_results

    def get_feature_matrix(
        self,
        include_experimental_group_x: bool = False,
        include_group_f: bool = False,
        include_group_g: bool = False,
        for_xgboost: bool = False,
    ) -> pd.DataFrame:
        """Build or retrieve cached account-level feature matrix."""
        cache_key = (include_experimental_group_x, include_group_f, include_group_g, for_xgboost)
        if cache_key in self._cached_feature_matrix:
            return self._cached_feature_matrix[cache_key].copy()

        if self._accounts_df is None:
            self.load_raw_data()

        rule_results = self.get_rule_results() if include_group_g else None

        matrix = extract_all_features(
            accounts_df=self._accounts_df,
            real_tx_df=self._real_tx_df,
            access_events_df=self._access_events_df,
            profile_changes_df=self._profile_changes_df,
            employee_map_df=self._employee_map_df,
            injected_tx_df=self._injected_tx_df,
            customers_df=self._customers_df,
            rule_results=rule_results,
            include_experimental_group_x=include_experimental_group_x,
            include_group_f=include_group_f,
            include_group_g=include_group_g,
            for_xgboost=for_xgboost,
        )

        self._cached_feature_matrix[cache_key] = matrix
        return matrix.copy()

    def get_xgboost_dataset(
        self,
        include_group_g: bool = False,
        include_experimental_group_x: bool = False,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        """Return the 38 labeled scenario accounts for XGBoost supervised training and evaluation.

        Features: Groups A-E (excluding background_real_laundering_count),
        Group F (Customer features), Group G (optional), and Group X (optional).
        """
        features = self.get_feature_matrix(
            include_experimental_group_x=include_experimental_group_x,
            include_group_f=True,
            include_group_g=include_group_g,
            for_xgboost=True,
        )
        scenarios = self.get_labeled_scenarios()
        scenario_acc_ids = scenarios["primary_account_id"].tolist()

        X_labeled = features.loc[scenario_acc_ids].copy()
        scenario_meta = scenarios.set_index("primary_account_id").loc[scenario_acc_ids].copy()
        y_labeled = scenario_meta["label"].copy()
        return X_labeled, y_labeled, scenario_meta

    def get_labeled_scenarios(self) -> pd.DataFrame:
        """Return the standardized 38 labeled scenario mapping."""
        if self._labeled_scenarios_df is None:
            self.load_raw_data()

        df = self._labeled_scenarios_df.copy()
        # Each scenario maps to its primary account ID (19 suspicious S01-S19 + 19 legitimate L01-L19)
        df["primary_account_id"] = df["account_id"].apply(lambda x: str(x).split(";")[0].strip())
        df["label"] = df["scenario_type"].apply(lambda t: 1 if str(t).lower() == "suspicious" else 0)
        return df

    def get_dataset_splits(
        self,
        include_experimental_group_x: bool = False,
        for_xgboost: bool = False,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.DataFrame]:
        """Split feature matrix into training background accounts and evaluation scenario accounts.

        Returns:
            X_background: (1846, n_features) - Unlabeled background accounts for unsupervised training.
            X_evaluation: (38, n_features) - 38 labeled scenario accounts for evaluation.
            y_evaluation: (38,) - Binary ground truth (1=suspicious, 0=legitimate).
            scenario_meta: (38, cols) - Metadata for evaluation analysis only.
        """
        features = self.get_feature_matrix(
            include_experimental_group_x=include_experimental_group_x,
            for_xgboost=for_xgboost,
        )
        scenarios = self.get_labeled_scenarios()

        scenario_acc_ids = scenarios["primary_account_id"].tolist()
        if len(scenario_acc_ids) != 38:
            raise ValueError(f"Expected 38 scenario accounts, got {len(scenario_acc_ids)}")

        # Verification of exact account membership
        eval_mask = features.index.isin(scenario_acc_ids)
        X_evaluation = features.loc[scenario_acc_ids].copy()
        X_background = features.loc[~eval_mask].copy()

        scenario_meta = scenarios.set_index("primary_account_id").loc[scenario_acc_ids].copy()
        y_evaluation = scenario_meta["label"].copy()

        if len(X_background) != 1846:
            raise ValueError(
                f"Expected exactly 1,846 background accounts, got {len(X_background)}"
            )

        return X_background, X_evaluation, y_evaluation, scenario_meta

    def get_feature_names(
        self,
        include_experimental_group_x: bool = False,
        for_xgboost: bool = False,
    ) -> List[str]:
        """Return the ordered list of feature names for a given configuration."""
        matrix = self.get_feature_matrix(
            include_experimental_group_x=include_experimental_group_x,
            for_xgboost=for_xgboost,
        )
        return list(matrix.columns)
