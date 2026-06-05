"""
예측 모듈 — OHT 대수 역산 및 월별 예측 산출

핵심: 목표 부하율 85%를 만족하는 OHT 대수를 반복수렴으로 역산한다.
반송시간이 대수(OHT count)에 의존하므로 단순 대수해가 없다.

수렴 알고리즘 개요:
  1) move_qty 계산 (OHT 무관)
  2) OHT 초기 추정 (cong→0 극한: oht0 = move_qty*T0/3600/TARGET_UTIL)
  3) cong, move_time, 새 OHT 계산 반복 → |oht_new - oht| < CONVERGE_TOL 에서 종료
"""

import math
import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List
from oht_forecast.constants import (
    TARGET_UTIL, TOTAL_SLOT, OCC_WARN,
    CONVERGE_TOL, CONVERGE_MAXIT,
)
from oht_forecast.fitting import (
    MoveQtyParams, MoveTimeParams, StorageProdParams, StorageNPWParams,
)

logger = logging.getLogger(__name__)


# ── 결과 데이터클래스 ─────────────────────────────────────────────────────

@dataclass
class MonthForecast:
    """단일 미래 월의 예측 결과 (point estimate)"""
    month: str                  # "YYYY-MM"
    move_qty: float             # 시간당 반송량 (회/hr)
    oht_required: int           # 필요 OHT 대수 (ceil of oht_float)
    oht_float: float            # 수렴된 실수 OHT
    move_time: float            # 평균 반송시간 (초)
    cong: float                 # 혼잡도 (부하율)
    converged: bool             # True: CONVERGE_TOL 이내 수렴
    iterations: int             # 실제 반복 횟수
    storage_prod: float         # 생산 FOUP 저장량
    storage_npw: float          # 비생산 FOUP 저장량
    storage_total: float        # 합계
    occupancy: float            # storage_total / TOTAL_SLOT
    # 경보 플래그
    warn_saturation: bool = False    # 수렴 중 cong >= 1 발생
    warn_occupancy: bool  = False    # occupancy >= OCC_WARN
    warn_convergence: bool = False   # CONVERGE_MAXIT 초과
    extrapolation: bool   = False    # 수렴 cong > 0.85 (외삽 영역)


@dataclass
class OHTBand:
    """OHT 대수 불확실성 밴드 (b의 표준오차 전파)"""
    month: str
    oht_central: int     # b (point)
    oht_lo1: int         # b - 1*se_b
    oht_hi1: int         # b + 1*se_b
    oht_lo2: int         # b - 2*se_b
    oht_hi2: int         # b + 2*se_b


# ── 핵심 역산 함수 ────────────────────────────────────────────────────────

def solve_oht(move_qty: float,
              T0: float,
              b: float,
              target_util: float = TARGET_UTIL) -> dict:
    """
    단일 월의 OHT 대수 역산 반복수렴

    물리 모델:
      cong = move_qty * T0 / (oht * 3600)        ← move_time 미포함
      move_time = T0 + b * cong / (1 - cong)
      oht_required = move_qty * move_time / 3600 / target_util

    이 세 식이 순환적(oht → cong → move_time → oht)이므로 반복법으로 해결.

    Args:
        move_qty:    시간당 반송량 (회/hr)
        T0:          기본 반송시간 (초)
        b:           혼잡 계수 (>0)
        target_util: 목표 부하율 (기본 TARGET_UTIL=0.85)

    Returns:
        {
          'oht_float':         float,   # 수렴된 실수 OHT
          'cong':              float,   # 최종 혼잡도
          'move_time':         float,   # 최종 반송시간 (초)
          'converged':         bool,
          'iterations':        int,
          'warn_saturation':   bool,    # cong >= 1 발생 여부
        }

    Note:
        cong >= 1이 발생하면 oht를 10% 증가시켜 재시도한다.
        b가 0 이하이면 clamping하여 경고 없이 처리. 호출 전에 검증할 것.
    """
    # TODO: 구현
    # b = max(b, 1e-9)  # 수치 안전
    # oht = move_qty * T0 / 3600 / target_util  # 초기값 (cong=0 가정)
    # warn_saturation = False
    # for i in range(CONVERGE_MAXIT):
    #     cong = move_qty * T0 / (oht * 3600)
    #     if cong >= 1.0:
    #         oht *= 1.1
    #         warn_saturation = True
    #         continue
    #     mt = T0 + b * cong / (1 - cong)
    #     oht_new = move_qty * mt / 3600 / target_util
    #     if abs(oht_new - oht) < CONVERGE_TOL:
    #         return {'oht_float': oht_new, 'cong': cong, 'move_time': mt,
    #                 'converged': True, 'iterations': i+1,
    #                 'warn_saturation': warn_saturation}
    #     oht = oht_new
    # return {'oht_float': oht, 'cong': cong, 'move_time': mt,
    #         'converged': False, 'iterations': CONVERGE_MAXIT,
    #         'warn_saturation': warn_saturation}
    raise NotImplementedError


# ── 월별 예측 ─────────────────────────────────────────────────────────────

def predict_month(row: pd.Series,
                  mq: MoveQtyParams,
                  mt: MoveTimeParams,
                  sp: StorageProdParams,
                  snpw: StorageNPWParams) -> tuple[MonthForecast, OHTBand]:
    """
    단일 미래 월에 대한 예측 수행

    Args:
        row:  plan_df의 단일 행 (prod_plan, lot_size_plan, wip_plan)
        mq, mt, sp, snpw: fit_all() 결과 파라미터

    Returns:
        (MonthForecast, OHTBand) 튜플

    주의:
        ① move_qty: prod_plan, lot_size_plan만 사용. wip_plan 사용 금지.
        ② OHT 역산: solve_oht 총 5회 호출 (central + ±1σ + ±2σ).
        ③ storage_prod: wip_plan과 수렴 후 cong 사용.
    """
    # TODO: 구현
    # 1. move_qty = mq.k0 + mq.k * (row['prod_plan'] / row['lot_size_plan'])
    # 2. central = solve_oht(move_qty, mt.T0, mt.b)
    #    b_variants = {
    #        'lo2': max(mt.b - 2*mt.se_b, 1e-9),
    #        'lo1': max(mt.b - 1*mt.se_b, 1e-9),
    #        'hi1': mt.b + 1*mt.se_b,
    #        'hi2': mt.b + 2*mt.se_b,
    #    }
    #    각 b에 대해 solve_oht 호출 → OHTBand 구성
    # 3. cong = central['cong']
    # 4. wip_plan = row['wip_plan']
    #    cong_term = cong / (1 - cong) if cong < 1 else np.nan
    #    storage_prod = sp.alpha * wip_plan + sp.beta * wip_plan * cong_term
    #    storage_npw  = snpw.gamma + snpw.delta * move_qty
    #    storage_total = storage_prod + storage_npw
    #    occupancy = storage_total / TOTAL_SLOT
    # 5. 경보 플래그 세팅, MonthForecast 반환
    raise NotImplementedError


def predict(plan_df: pd.DataFrame,
            mq: MoveQtyParams,
            mt: MoveTimeParams,
            sp: StorageProdParams,
            snpw: StorageNPWParams) -> tuple[List[MonthForecast], List[OHTBand]]:
    """
    전체 미래 월 예측 루프

    Args:
        plan_df: load_plan() 결과
        mq, mt, sp, snpw: fit_all() 결과

    Returns:
        (List[MonthForecast], List[OHTBand])

    Note:
        비수렴/포화 발생 시 WARNING 로그를 출력하고 계속 진행한다.
        호출자(main.py)가 warnings를 모아 warnings.log에 저장한다.
    """
    # TODO: 구현
    # forecasts, bands = [], []
    # for _, row in plan_df.iterrows():
    #     fc, band = predict_month(row, mq, mt, sp, snpw)
    #     if fc.warn_saturation or fc.warn_convergence:
    #         logger.warning("[%s] 수렴 경고: saturation=%s, convergence=%s",
    #                        fc.month, fc.warn_saturation, fc.warn_convergence)
    #     forecasts.append(fc); bands.append(band)
    # return forecasts, bands
    raise NotImplementedError
