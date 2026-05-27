"""
Bootstrap confidence intervals for OHT and Storage predictions.
"""
import numpy as np
import pandas as pd
from typing import Callable


def bootstrap_prediction_interval(
    predict_fn: Callable[[pd.DataFrame], pd.Series],
    plan_df: pd.DataFrame,
    actuals_df: pd.DataFrame,
    n_boot: int = 500,
    ci: float = 0.80,
) -> pd.DataFrame:
    """
    Resample actuals_df with replacement, retrain (or perturb) and predict.
    Returns lower/upper CI for each row of plan_df.

    For efficiency, we resample actuals and pass to predict_fn which
    should return a Series of predicted values aligned to plan_df index.
    """
    results = []
    n = len(actuals_df)
    rng = np.random.default_rng(42)

    for _ in range(n_boot):
        boot_idx = rng.integers(0, n, size=n)
        boot_actuals = actuals_df.iloc[boot_idx].reset_index(drop=True)
        try:
            preds = predict_fn(plan_df, boot_actuals)
            results.append(preds.values)
        except Exception:
            continue

    if not results:
        return pd.DataFrame(
            {"ci_lower": np.nan, "ci_upper": np.nan}, index=plan_df.index
        )

    arr = np.array(results)  # shape: (n_boot, n_plan_rows)
    alpha = (1 - ci) / 2
    lower = np.nanpercentile(arr, alpha * 100, axis=0)
    upper = np.nanpercentile(arr, (1 - alpha) * 100, axis=0)

    return pd.DataFrame({"ci_lower": lower, "ci_upper": upper}, index=plan_df.index)


def scenario_sensitivity(
    base_plan_df: pd.DataFrame,
    predict_fn: Callable,
    deltas: list[float] = [-0.2, -0.1, 0.0, 0.1, 0.2],
) -> pd.DataFrame:
    """
    Vary movement_plan by each delta factor and return predicted values.
    Returns DataFrame with columns: delta, <predicted columns>
    """
    rows = []
    for d in deltas:
        plan = base_plan_df.copy()
        plan["movement_plan"] = plan["movement_plan"] * (1 + d)
        preds = predict_fn(plan)
        if isinstance(preds, pd.DataFrame):
            preds["delta"] = d
            rows.append(preds)
        else:
            rows.append(pd.DataFrame({"delta": [d], "value": [preds]}))
    return pd.concat(rows, ignore_index=True)
