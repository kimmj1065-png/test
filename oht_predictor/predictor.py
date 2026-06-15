"""
월별 예측 실행
==============
Step 1 → 반송량    : move_qty = k·(prod_plan / lot_size_plan)
Step 2 → 혼잡도    : cong = move_qty·T0_ref / (OHT_FIXED·3600)
       → 반송시간  : move_time = t0 + v_load·load_const + b·cong/(1−cong)
       → 부하율    : util = move_qty·move_time / 3600 / OHT_FIXED
Step 3 → 저장량    : storage_prod, storage_npw, storage_total, occupancy
Step 4 → 불확실성  : move_time_lo/hi, util_lo/hi  (SENS_Z σ 범위)
Step 5 → 경보 플래그

반환 컬럼:
  month, move_qty, move_time, move_time_lo, move_time_hi,
  util, util_lo, util_hi, cong,
  storage_prod, storage_npw, storage_total, occupancy,
  포화경보, 부하율경보, 외삽여부, 점유경보
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from constants import TOTAL_SLOT, UTIL_WARN, OCC_WARN, SENS_Z
from model import ModelParams, calc_congestion

# 과거 실측 최대 cong 이상이면 외삽 구간으로 표시
_EXTRAP_THRESHOLD = 0.78


def predict(plan: pd.DataFrame, p: ModelParams) -> pd.DataFrame:
    """plan 각 행에 대해 예측 → DataFrame 반환."""
    return pd.DataFrame([_predict_row(row, p) for _, row in plan.iterrows()])


def _predict_row(row: pd.Series, p: ModelParams) -> dict:
    prod     = float(row["prod_plan"])
    lot_size = float(row["lot_size_plan"])
    wip      = float(row["wip_plan"])

    # Step 1: 반송량
    mq = p.k * (prod / lot_size)

    # Step 2: 혼잡도 → 반송시간 → 부하율
    cong = float(calc_congestion(mq, p.T0_ref, p.OHT_FIXED))
    sat  = cong >= 1.0
    ct   = cong / (1.0 - cong) if not sat else 1e6   # 포화 시 매우 큰 값

    def _mt(lc: float, b_val: float) -> float:
        return p.t0 + p.v_load * lc + b_val * ct

    lc     = p.load_const
    lc_std = p.load_const_std
    b_std  = p.se_b

    mt    = _mt(lc,              p.b)
    mt_lo = _mt(lc - SENS_Z * lc_std, p.b - SENS_Z * b_std)
    mt_hi = _mt(lc + SENS_Z * lc_std, p.b + SENS_Z * b_std)

    def _util(mt_val: float) -> float:
        return mq * mt_val / 3600.0 / p.OHT_FIXED

    util    = _util(mt)
    util_lo = _util(mt_lo)
    util_hi = _util(mt_hi)

    # Step 3: 저장량
    if p.use_beta and not sat:
        sp = p.alpha * wip + p.beta * wip * ct
    else:
        sp = p.alpha * wip
    snpw   = p.gamma + p.delta * mq
    stotal = sp + snpw
    occ    = stotal / TOTAL_SLOT

    return {
        "month":         row["month"],
        "move_qty":      round(mq,     2),
        "move_time":     round(mt,     1),
        "move_time_lo":  round(mt_lo,  1),
        "move_time_hi":  round(mt_hi,  1),
        "util":          round(util,   4),
        "util_lo":       round(util_lo, 4),
        "util_hi":       round(util_hi, 4),
        "cong":          round(cong,   4),
        "storage_prod":  round(sp,     0),
        "storage_npw":   round(snpw,   0),
        "storage_total": round(stotal, 0),
        "occupancy":     round(occ,    4),
        "포화경보":       sat,
        "부하율경보":     bool(util >= UTIL_WARN),
        "외삽여부":       bool(cong > _EXTRAP_THRESHOLD),
        "점유경보":       bool(occ  >= OCC_WARN),
    }
