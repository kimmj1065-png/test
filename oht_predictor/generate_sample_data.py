"""
샘플 데이터 생성기
===================
실제 데이터가 없을 때 검증용 합성 데이터를 만듭니다.
실행:  python generate_sample_data.py

생성 파일:
  sample_data/actuals.csv  (52행, 2020-01 ~ 2024-04)
  sample_data/plan.csv     (12행, 2024-05 ~ 2025-04)

사용된 참 파라미터 (역회귀 검증용):
  k=0.070, t0=50, v_load=0.0048, b=55,
  T0_ref=155(저부하 평균), alpha=0.32, beta=0.45, gamma=2100, delta=9.5
"""
from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

OUT = Path(__file__).parent / "sample_data"
OUT.mkdir(exist_ok=True)

# ── 참 파라미터 ──────────────────────────────────────────────────────────────
K       = 0.070
T0      = 50.0
V_LOAD  = 0.0048
B       = 55.0
ALPHA   = 0.32
BETA    = 0.45
GAMMA   = 2100.0
DELTA   = 9.5
T0_REF  = 155.0   # 저부하 기준 (코드가 자동 추정)

# ── 실적 52행 ────────────────────────────────────────────────────────────────
N_ACT = 52
months_act = pd.date_range("2020-01", periods=N_ACT, freq="MS")

i = np.arange(N_ACT)
prod      = (110_000 + i * 700 + 4_000 * np.sin(2 * np.pi * i / 12)
             + rng.normal(0, 1_500, N_ACT)).astype(int)
lot_size  = (25 + rng.normal(0, 0.3, N_ACT)).clip(24, 26).round(1)
wip       = (prod * 0.28 + rng.normal(0, 1_200, N_ACT)).clip(20_000).astype(int)

# OHT: 초반 55대, 24개월 이후 58대
oht_count = np.where(i < 24, 55, 58).astype(int)

# move_qty (참값 + 노이즈)
move_qty_true = K * (prod / lot_size)
move_qty      = (move_qty_true * (1 + rng.normal(0, 0.025, N_ACT))).round(1)

# load_dist (mm, 약 18~21 m)
load_dist = (19_500 + rng.normal(0, 800, N_ACT)).clip(17_000, 23_000).round(0).astype(int)

# cong (T0_REF 기준)
cong = move_qty * T0_REF / (oht_count * 3600.0)
ct   = np.where(cong < 1, cong / (1 - cong), 5.0)

# move_time (참값 + 노이즈)
move_time = (T0 + V_LOAD * load_dist + B * ct
             + rng.normal(0, 4, N_ACT)).clip(80).round(1)

# storage_prod
storage_prod = (ALPHA * wip + BETA * wip * ct
                + rng.normal(0, 500, N_ACT)).clip(0).round(0).astype(int)

# storage_npw
storage_npw = (GAMMA + DELTA * move_qty
               + rng.normal(0, 200, N_ACT)).clip(0).round(0).astype(int)

actuals = pd.DataFrame({
    "month":        months_act.strftime("%Y-%m"),
    "prod":         prod,
    "wip":          wip,
    "lot_size":     lot_size,
    "move_qty":     move_qty,
    "move_time":    move_time,
    "load_dist":    load_dist,
    "oht_count":    oht_count,
    "storage_prod": storage_prod,
    "storage_npw":  storage_npw,
})
actuals.to_csv(OUT / "actuals.csv", index=False)
print(f"[완료] actuals.csv ({N_ACT}행) → {OUT / 'actuals.csv'}")

# ── 계획 12행 ────────────────────────────────────────────────────────────────
N_PLAN = 12
months_plan = pd.date_range("2024-05", periods=N_PLAN, freq="MS")

j = np.arange(N_PLAN)
prod_plan     = (148_000 + j * 600 + 3_500 * np.sin(2 * np.pi * j / 12)).astype(int)
lot_size_plan = np.full(N_PLAN, 25.0)
wip_plan      = (prod_plan * 0.29).astype(int)

plan = pd.DataFrame({
    "month":         months_plan.strftime("%Y-%m"),
    "prod_plan":     prod_plan,
    "lot_size_plan": lot_size_plan,
    "wip_plan":      wip_plan,
})
plan.to_csv(OUT / "plan.csv", index=False)
print(f"[완료] plan.csv ({N_PLAN}행)    → {OUT / 'plan.csv'}")
