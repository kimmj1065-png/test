"""
OHT capacity calculation chain:
  생산계획 → movement → 반송량 → 반송시간 → 필요 OHT 시간 → OHT 과부족
Aggregated at (site, floor) level.
"""
import pandas as pd
import numpy as np
from .model_trainer import predict_movement, predict_transport_count, predict_transport_time


def calculate_oht_demand(
    plan_df: pd.DataFrame,
    floor_config: pd.DataFrame,
    dr_steps: dict,
) -> pd.DataFrame:
    """
    plan_df: site, line, floor, dr_type, plan_month, movement_plan, wip_plan, lot_size
    floor_config: site, floor, line, oht_count, oht_monthly_hours
    dr_steps: {dr_type: step_count}
    Returns row per (site, line, floor, dr_type, plan_month) with:
      movement_pred, transport_count_pred, transport_time_pred,
      required_oht_hours, rho
    """
    rows = []
    for _, row in plan_df.iterrows():
        site = row["site"]
        line = row["line"]
        floor = row["floor"]
        dr_type = row["dr_type"]
        month = row["plan_month"]
        steps = dr_steps.get(dr_type, 1)

        # Step 1
        movement = predict_movement(row["movement_plan"], site, line, dr_type)

        # Step 2
        tc = predict_transport_count(movement, site, line, dr_type, steps)

        # Step 3 (queuing corrected)
        tt_result = predict_transport_time(tc, site, line, floor, dr_type)
        transport_time = tt_result["transport_time"]
        rho = tt_result.get("rho")

        # Required OHT seconds → hours
        required_oht_hours = (tc * transport_time) / 3600

        rows.append({
            "site": site, "line": line, "floor": floor,
            "dr_type": dr_type, "plan_month": month,
            "movement_pred": movement,
            "transport_count_pred": tc,
            "transport_time_pred": transport_time,
            "required_oht_hours": required_oht_hours,
            "rho_estimated": rho,
            "queuing_model_used": not tt_result.get("fallback", True),
        })

    result = pd.DataFrame(rows)
    return result


def aggregate_oht_by_floor(
    demand_df: pd.DataFrame,
    floor_config: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate required OHT hours at (site, floor, plan_month) level.
    Compare against floor-level OHT capacity.
    Returns shortage/surplus in hours and unit count.
    """
    # Floor OHT capacity: one entry per (site, floor) — take first (shared by all lines)
    oht_cap = (
        floor_config.groupby(["site", "floor"])
        .agg(oht_count=("oht_count", "first"), oht_monthly_hours=("oht_monthly_hours", "first"))
        .reset_index()
    )
    oht_cap["available_oht_hours"] = oht_cap["oht_count"] * oht_cap["oht_monthly_hours"]

    # Sum demand across lines sharing the same floor
    floor_demand = (
        demand_df.groupby(["site", "floor", "plan_month"])
        .agg(
            required_oht_hours=("required_oht_hours", "sum"),
            lines=("line", lambda x: list(x.unique())),
        )
        .reset_index()
    )

    merged = floor_demand.merge(oht_cap, on=["site", "floor"], how="left")
    merged["oht_surplus_hours"] = merged["available_oht_hours"] - merged["required_oht_hours"]
    merged["oht_surplus_units"] = merged["oht_surplus_hours"] / merged["oht_monthly_hours"]
    merged["utilization_rate"] = merged["required_oht_hours"] / merged["available_oht_hours"]

    return merged.sort_values(["site", "floor", "plan_month"])


def line_contribution(demand_df: pd.DataFrame) -> pd.DataFrame:
    """Per-line share of OHT demand within each floor (for drill-down chart)."""
    floor_total = (
        demand_df.groupby(["site", "floor", "plan_month"])["required_oht_hours"]
        .sum()
        .rename("floor_total_hours")
    )
    merged = demand_df.merge(floor_total, on=["site", "floor", "plan_month"])
    merged["line_share"] = merged["required_oht_hours"] / merged["floor_total_hours"]
    return merged
