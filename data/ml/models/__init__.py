"""ML model definitions and interfaces."""

from data.ml.models.isolation_forest import IsolationForestDetector
from data.ml.models.xgboost_classifier import (
    XGBoostDetector,
    load_xgboost_model,
    train_and_save_final_model,
)

__all__ = [
    "IsolationForestDetector",
    "XGBoostDetector",
    "load_xgboost_model",
    "train_and_save_final_model",
]
