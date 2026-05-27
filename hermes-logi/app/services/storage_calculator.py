"""
Storage capacity calculation:
  total_storage = product_storage + non_product_storage
  product: LightGBM prediction from WIP
  non_product: 3-month rolling average of (total_actual - product_actual)
"""
import pandas as pd
import numpy as np
from .model_trainer import predict_storage_product


def _rolling_non_product(
    actuals_df: pd.DataFrame, site: str, line: str, floor: str, dr_type: str, window: int = 3
) -> float:
    """Return rolling average of non_product from recent actuals."""
    mask = (
        (actuals_df["site"] == site)
        & (actuals_df["line"] == line)
        & (actuals_df["floor"] == floor)
        & (actuals_df["dr_type"] == dr_type)
    )
    grp = actuals_df[mask].sort_values("actual_month").tail(window)

    if grp.empty:
        return 0.0

    non_product = grp["storage_total_actual"] - grp["storage_product_actual"]
    non_product = non_product.clip(lower=0)
    return float(non_product.mean())


def calculate_storage_demand(
    plan_df: pd.DataFrame,
    actuals_df: pd.DataFrame,
    storage_config: pd.DataFrame,
    dr_steps: dict,
) -> pd.DataFrame:
    """
    Returns per-(site, line, floor, dr_type, plan_month):
      product_storage_pred, non_product_storage_pred, total_storage_pred
      storage_capacity, storage_surplus, storage_utilization
    """
    rows = []
    for _, row in plan_df.iterrows():
        site = row["site"]
        line = row["line"]
        floor = row["floor"]
        dr_type = row["dr_type"]
        month = row["plan_month"]
        steps = dr_steps.get(dr_type, 1)

        import datetime
        try:
            month_of_year = int(month.split("-")[1])
        except Exception:
            month_of_year = 1

        wip = row.get("wip_plan", 0) or 0
        lot_size = row.get("lot_size", 25) or 25

        product_pred = predict_storage_product(wip, lot_size, dr_type, steps, month_of_year, site, line)
        non_product_pred = _rolling_non_product(actuals_df, site, line, floor, dr_type)

        total_pred = product_pred + non_product_pred

        # Storage capacity for this line
        cap_mask = (
            (storage_config["site"] == site)
            & (storage_config["line"] == line)
            & (storage_config["floor"] == floor)
        )
        cap_row = storage_config[cap_mask]
        capacity = float(cap_row["storage_capacity"].iloc[0]) if not cap_row.empty else np.nan

        rows.append({
            "site": site, "line": line, "floor": floor,
            "dr_type": dr_type, "plan_month": month,
            "product_storage_pred": product_pred,
            "non_product_storage_pred": non_product_pred,
            "total_storage_pred": total_pred,
            "storage_capacity": capacity,
            "storage_surplus": capacity - total_pred if not np.isnan(capacity) else np.nan,
            "storage_utilization": total_pred / capacity if (not np.isnan(capacity) and capacity > 0) else np.nan,
        })

    return pd.DataFrame(rows).sort_values(["site", "line", "floor", "plan_month"])
