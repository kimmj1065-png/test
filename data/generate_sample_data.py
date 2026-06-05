"""
합성 샘플 데이터 생성 스크립트
실제 반도체 팹 OHT 시스템의 물리 관계를 반영한 52행 데이터를 생성한다.

사용법:
  python data/generate_sample_data.py

출력:
  data/actuals.csv   (52행, 2022-01 ~ 2026-04)
  data/plan.csv      (18행, 2026-05 ~ 2027-10)

생성 파라미터 (실제 팹과 유사한 값):
  - k    = 0.28      (생산/lot_size → 반송량 계수)
  - T0   = 55        (기본 반송시간, 초)
  - b    = 120       (혼잡 계수)
  - alpha = 0.55     (WIP → 생산저장 계수)
  - beta  = 0.003    (혼잡 × WIP → 생산저장 비선형 계수)
  - gamma = 500      (비생산저장 절편)
  - delta = 1.8      (반송량 → 비생산저장 계수)
"""

import numpy as np
import pandas as pd
from datetime import datetime

# ── 난수 시드 고정 (재현 가능) ────────────────────────────────────────────
np.random.seed(42)

# ── 진실 파라미터 (True parameters) ──────────────────────────────────────
TRUE_K     = 0.28
TRUE_T0    = 55.0
TRUE_B     = 120.0
TRUE_ALPHA = 0.55
TRUE_BETA  = 0.003
TRUE_GAMMA = 500.0
TRUE_DELTA = 1.8

# ── 기간 설정 ──────────────────────────────────────────────────────────────
months_actuals = pd.period_range('2022-01', '2026-04', freq='M')  # 52개월
months_plan    = pd.period_range('2026-05', '2027-10', freq='M')  # 18개월
N_ACT = len(months_actuals)
N_PLAN = len(months_plan)


def seasonal_factor(t: int, period: int = 12, depth: float = 0.05) -> float:
    """계절성 인자: 2월에 ~0.95, 연중 평균 ~1.0"""
    return 1.0 - depth * np.cos(2 * np.pi * (t - 6) / period)


# ── actuals 생성 ──────────────────────────────────────────────────────────

def generate_actuals() -> pd.DataFrame:
    t = np.arange(N_ACT)

    # 1. 생산량: 70000에서 월 1.5% 성장 + 계절성 + 노이즈
    prod = 70_000 * (1.015 ** t) * np.array([seasonal_factor(i) for i in t])
    prod *= 1 + np.random.normal(0, 0.015, N_ACT)

    # 2. Lot size: 대부분 25, 5개월은 24
    lot_size = np.full(N_ACT, 25.0)
    lot_size[np.random.choice(N_ACT, 5, replace=False)] = 24.0

    # 3. OHT 대수: 조달 주기 반영 (단계적 증가)
    oht_count = np.full(N_ACT, 160.0)
    oht_count[12:] = 200.0   # 2023-01부터
    oht_count[24:] = 240.0   # 2024-01부터
    oht_count[36:] = 270.0   # 2025-01부터
    oht_count[48:] = 290.0   # 2026-01부터

    # 4. 반송량: 물리식 + 노이즈
    move_qty = TRUE_K * (prod / lot_size) * (1 + np.random.normal(0, 0.03, N_ACT))

    # 5. 혼잡도 (진실값, 노이즈 없음)
    cong = move_qty * TRUE_T0 / (oht_count * 3600)

    # 6. 반송시간: 물리식 + 노이즈
    move_time = TRUE_T0 + TRUE_B * cong / (1 - np.clip(cong, 0, 0.98))
    move_time *= 1 + np.random.normal(0, 0.04, N_ACT)

    # 7. 재공: 생산량 × 0.155 + 완만한 트렌드 + 노이즈
    wip = prod * 0.155 * (1 + 0.003 * t)
    wip *= 1 + np.random.normal(0, 0.02, N_ACT)

    # 8. 생산 FOUP 저장량: 물리식 + 노이즈
    storage_prod = (TRUE_ALPHA * wip
                    + TRUE_BETA * wip * cong / (1 - np.clip(cong, 0, 0.98)))
    storage_prod *= 1 + np.random.normal(0, 0.03, N_ACT)

    # 9. 비생산 FOUP 저장량: 물리식 + 노이즈
    storage_npw = TRUE_GAMMA + TRUE_DELTA * move_qty
    storage_npw *= 1 + np.random.normal(0, 0.04, N_ACT)

    df = pd.DataFrame({
        'month': [str(m) for m in months_actuals],
        'prod': np.round(prod).astype(int),
        'wip': np.round(wip).astype(int),
        'lot_size': lot_size,
        'move_qty': np.round(move_qty, 2),
        'move_time': np.round(move_time, 1),
        'oht_count': oht_count.astype(int),
        'storage_prod': np.round(storage_prod).astype(int),
        'storage_npw': np.round(storage_npw).astype(int),
    })
    return df


# ── plan 생성 ─────────────────────────────────────────────────────────────

def generate_plan() -> pd.DataFrame:
    n = N_PLAN
    t = np.arange(n)

    # 2026-04 실적 기준 연장
    last_prod = 70_000 * (1.015 ** (N_ACT - 1)) * seasonal_factor(N_ACT - 1)

    # 구간별 성장률
    prod_plan = np.zeros(n)
    for i in range(n):
        global_t = N_ACT + i
        if i < 8:     # 2026-05~12: 월 1.5%
            prod_plan[i] = 70_000 * (1.015 ** (global_t - 1)) * seasonal_factor(global_t)
        elif i < 14:  # 2027-01~06: 월 2.5% (가속)
            prod_plan[i] = 70_000 * (1.025 ** (global_t - 1)) * seasonal_factor(global_t)
        else:         # 2027-07~10: 정체
            prod_plan[i] = prod_plan[13]

    lot_size_plan = np.full(n, 25.0)
    wip_plan = prod_plan * 0.155 * (1 + 0.003 * (N_ACT + t))

    df = pd.DataFrame({
        'month': [str(m) for m in months_plan],
        'prod_plan': np.round(prod_plan).astype(int),
        'lot_size_plan': lot_size_plan,
        'wip_plan': np.round(wip_plan).astype(int),
    })
    return df


if __name__ == '__main__':
    import os
    os.makedirs('data', exist_ok=True)

    actuals = generate_actuals()
    actuals.to_csv('data/actuals.csv', index=False)
    print(f"actuals.csv 저장: {len(actuals)}행")
    print(actuals.describe().round(1))

    plan = generate_plan()
    plan.to_csv('data/plan.csv', index=False)
    print(f"\nplan.csv 저장: {len(plan)}행")
    print(plan.head())

    # 생성된 데이터의 물리 일관성 확인
    cong = actuals['move_qty'] * TRUE_T0 / (actuals['oht_count'] * 3600)
    util = actuals['move_qty'] * actuals['move_time'] / 3600 / actuals['oht_count']
    print(f"\n[검증] cong 범위: {cong.min():.3f} ~ {cong.max():.3f}")
    print(f"[검증] 부하율 범위: {util.min():.3f} ~ {util.max():.3f}")
    print("[검증] 부하율 > 0.85 행:", (util > 0.85).sum(), "개")
