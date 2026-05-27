"""
Excel parser for planning and actuals upload.
Normalizes Korean/English column names to internal schema.
"""
import pandas as pd
import numpy as np
from io import BytesIO

# Column aliases: Korean → internal name
PLAN_COL_MAP = {
    "사이트": "site", "site": "site",
    "라인": "line", "line": "line",
    "층": "floor", "floor": "floor",
    "DR타입": "dr_type", "dr_type": "dr_type", "DR": "dr_type",
    "계획월": "plan_month", "plan_month": "plan_month",
    "생산계획": "movement_plan", "movement_plan": "movement_plan",
    "재공계획": "wip_plan", "wip_plan": "wip_plan",
    "LOT크기": "lot_size", "lot_size": "lot_size", "lot size": "lot_size",
    "NPW계획": "npw_plan", "npw_plan": "npw_plan",
    "투입계획": "input_plan", "input_plan": "input_plan",
}

ACTUAL_COL_MAP = {
    "사이트": "site", "site": "site",
    "라인": "line", "line": "line",
    "층": "floor", "floor": "floor",
    "DR타입": "dr_type", "dr_type": "dr_type", "DR": "dr_type",
    "실적월": "actual_month", "actual_month": "actual_month",
    "생산실적": "movement_actual", "movement_actual": "movement_actual",
    "반송량실적": "transport_count_actual", "transport_count_actual": "transport_count_actual",
    "반송시간실적": "transport_time_actual", "transport_time_actual": "transport_time_actual",
    "저장량실적(product)": "storage_product_actual", "storage_product_actual": "storage_product_actual",
    "저장량실적(total)": "storage_total_actual", "storage_total_actual": "storage_total_actual",
    "투입계획": "input_plan", "input_plan": "input_plan",
}

REQUIRED_PLAN_COLS = {"site", "line", "floor", "dr_type", "plan_month", "movement_plan"}
REQUIRED_ACTUAL_COLS = {"site", "line", "floor", "dr_type", "actual_month"}


def _rename_cols(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        key = col.strip()
        if key in col_map:
            renamed[col] = col_map[key]
    return df.rename(columns=renamed)


def _parse_month(series: pd.Series) -> pd.Series:
    """Normalize month column to YYYY-MM string."""
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m")


def parse_plan_excel(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_excel(BytesIO(file_bytes))
    df = _rename_cols(df, PLAN_COL_MAP)

    missing = REQUIRED_PLAN_COLS - set(df.columns)
    if missing:
        raise ValueError(f"계획 파일 필수 컬럼 누락: {missing}")

    df["plan_month"] = _parse_month(df["plan_month"])
    for col in ["movement_plan", "wip_plan", "lot_size", "npw_plan", "input_plan"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["plan_month"])
    return df


def parse_actual_excel(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_excel(BytesIO(file_bytes))
    df = _rename_cols(df, ACTUAL_COL_MAP)

    missing = REQUIRED_ACTUAL_COLS - set(df.columns)
    if missing:
        raise ValueError(f"실적 파일 필수 컬럼 누락: {missing}")

    df["actual_month"] = _parse_month(df["actual_month"])
    for col in [
        "movement_actual", "transport_count_actual", "transport_time_actual",
        "storage_product_actual", "storage_total_actual", "input_plan",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["actual_month"])
    return df


def generate_sample_plan_excel() -> bytes:
    rows = [
        {
            "사이트": "Fab1", "라인": "L1", "층": "F1", "DR타입": "DRAM",
            "계획월": "2026-01", "생산계획": 10000, "재공계획": 5000,
            "LOT크기": 25, "NPW계획": 500, "투입계획": 9800,
        }
    ]
    df = pd.DataFrame(rows)
    buf = BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def generate_sample_actual_excel() -> bytes:
    rows = [
        {
            "사이트": "Fab1", "라인": "L1", "층": "F1", "DR타입": "DRAM",
            "실적월": "2025-12",
            "생산실적": 9800, "반송량실적": 120000, "반송시간실적": 45.0,
            "저장량실적(product)": 4800, "저장량실적(total)": 5500,
            "투입계획": 9800,
        }
    ]
    df = pd.DataFrame(rows)
    buf = BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()
