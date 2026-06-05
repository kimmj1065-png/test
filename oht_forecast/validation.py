"""
검증 모듈 — LOOCV 및 민감도 분석

LOOCV 설계 원칙 (데이터 누수 방지):
  - 각 fold i에서 train_df = df.drop(i)로 완전 재적합
  - T0도 반드시 train_df 기준으로 재계산 (estimate_T0(train_df))
  - move_time 예측 시: predict_mq(test)로 구한 move_qty와 test의 실제 oht_count 사용
    (역산 모드 아님 — 검증에서는 실제 oht_count 활용)

민감도 분석:
  b ±1σ/2σ, move_qty ±MAPE, T0 ±5%, β=0 강제
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict
from oht_forecast.constants import LOWLOAD_N, CONVERGE_TOL, CONVERGE_MAXIT
from oht_forecast.fitting import (
    fit_all, fit_move_qty, fit_move_time, fit_storage_prod, fit_storage_npw,
    compute_congestion, estimate_T0, MoveTimeParams,
    StorageProdParams,
)

logger = logging.getLogger(__name__)


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    MAPE 계산. y_true == 0인 항목은 제외하고 계산.
    """
    mask = y_true != 0
    if mask.sum() == 0:
        return float('nan')
    return float(np.mean(np.abs(y_pred[mask] - y_true[mask]) / np.abs(y_true[mask])) * 100)


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def loocv_report(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    52행 Leave-One-Out Cross Validation

    각 fold i (0..N-1):
      train_df = df.drop(index=i).reset_index(drop=True)  # N-1 행
      test_row  = df.iloc[i]
      → train_df로 전체 재적합 (fit_all)
      → test_row 입력으로 4가지 타깃 예측
      → 오차 누적

    Returns:
        {
          'move_qty':    {'mape': float, 'rmse': float},
          'move_time':   {'mape': float, 'rmse': float},
          'storage_prod':{'mape': float, 'rmse': float},
          'storage_npw': {'mape': float, 'rmse': float},
        }

    ⚠ LOOCV 내부에서 fit_all이 wip을 ①②에 사용하지 않는지 확인
       (fitting.py의 구현 제약이 여기서도 그대로 적용됨)
    """
    # TODO: 구현
    # N = len(df)
    # preds = {'move_qty': [], 'move_time': [], 'storage_prod': [], 'storage_npw': []}
    # actuals = {k: [] for k in preds}
    #
    # for i in range(N):
    #     train = df.drop(index=i).reset_index(drop=True)
    #     test  = df.iloc[i]
    #     try:
    #         params = fit_all(train)
    #     except Exception as e:
    #         logger.warning("LOOCV fold %d fit 실패: %s", i, e)
    #         continue
    #
    #     mq, mt, sp, snpw = params['mq'], params['mt'], params['sp'], params['snpw']
    #
    #     # ① move_qty 예측
    #     pred_mq = mq.k0 + mq.k * (test['prod'] / test['lot_size'])
    #
    #     # ② move_time 예측 (test의 실제 oht_count 사용, 역산 아님)
    #     cong_test = pred_mq * mt.T0 / (test['oht_count'] * 3600)
    #     cong_test = min(cong_test, 0.99)  # 수치 클램프
    #     pred_mt = mt.T0 + mt.b * cong_test / (1 - cong_test)
    #
    #     # ③a storage_prod (test의 실제 wip, oht_count 사용)
    #     nonlin = cong_test / (1 - cong_test)
    #     pred_sp = sp.alpha * test['wip'] + sp.beta * test['wip'] * nonlin
    #
    #     # ③b storage_npw
    #     pred_snpw = snpw.gamma + snpw.delta * pred_mq
    #
    #     # 누적
    #     preds['move_qty'].append(pred_mq)
    #     preds['move_time'].append(pred_mt)
    #     preds['storage_prod'].append(pred_sp)
    #     preds['storage_npw'].append(pred_snpw)
    #     for k in actuals:
    #         actuals[k].append(test[k])
    #
    # result = {}
    # for k in preds:
    #     y_true = np.array(actuals[k])
    #     y_pred = np.array(preds[k])
    #     result[k] = {'mape': _mape(y_true, y_pred), 'rmse': _rmse(y_true, y_pred)}
    # return result
    raise NotImplementedError


def sensitivity_analysis(df: pd.DataFrame,
                          mt: MoveTimeParams,
                          sp: StorageProdParams,
                          mq_loocv_mape: float = 5.0) -> pd.DataFrame:
    """
    파라미터 변동이 필요 OHT 대수 및 저장량에 주는 영향 분석

    시나리오:
      S1: b + 1*se_b (낙관적 대기)
      S2: b - 1*se_b (비관적 대기)
      S3: b + 2*se_b
      S4: b - 2*se_b
      S5: move_qty × (1 + mq_loocv_mape/100)
      S6: move_qty × (1 - mq_loocv_mape/100)
      S7: T0 × 1.05
      S8: T0 × 0.95
      S9: beta = 0 강제 (비선형 저장 항 제거)

    각 시나리오에서 학습 실적 최근 12개월에 대해 필요 OHT를 재계산하여
    기준(central)값 대비 최대 편차(%)를 반환한다.

    Args:
        df:              actuals DataFrame
        mt:              MoveTimeParams (b, se_b, T0)
        sp:              StorageProdParams (beta 포함)
        mq_loocv_mape:   move_qty LOOCV MAPE (%) — 반송량 오차 전파용

    Returns:
        DataFrame, index=scenario_name, columns=['max_oht_delta_pct', 'description']
    """
    # TODO: 구현
    # from oht_forecast.prediction import solve_oht
    # target_months = df.tail(12)
    # baseline_ohts = []
    # for _, row in target_months.iterrows():
    #     mq = row['move_qty']
    #     res = solve_oht(mq, mt.T0, mt.b)
    #     baseline_ohts.append(res['oht_float'])
    #
    # scenarios = {
    #     'b+1σ': (mt.b + mt.se_b,     mt.T0,      1.0,  'b 증가(+1σ) → 혼잡 증가'),
    #     'b-1σ': (max(mt.b-mt.se_b,1e-9), mt.T0,  1.0,  'b 감소(-1σ) → 혼잡 감소'),
    #     ... (각 시나리오)
    # }
    # → max |oht_scenario - oht_baseline| / oht_baseline * 100 계산
    raise NotImplementedError


def check_littles_law(plan_df: pd.DataFrame,
                      tat_months: float = 3.0,
                      threshold: float = 0.30) -> list:
    """
    Little's Law 정합성 검산 (경고 전용 — 모델 입력 변경 없음)

    WIP ≈ throughput × TAT
    월 단위: wip_plan ≈ prod_plan × tat_months

    |wip_plan - prod_plan*tat_months| / (prod_plan*tat_months) > threshold
    이면 경고 문자열 반환.

    Args:
        plan_df:    load_plan() 결과
        tat_months: 가정 TAT (개월), 기본 3.0
        threshold:  허용 편차 비율, 기본 0.30 (30%)

    Returns:
        list of warning strings (비어있으면 정합)
    """
    # TODO: 구현
    # warnings = []
    # for _, row in plan_df.iterrows():
    #     expected_wip = row['prod_plan'] * tat_months
    #     actual_wip   = row['wip_plan']
    #     deviation    = abs(actual_wip - expected_wip) / expected_wip
    #     if deviation > threshold:
    #         warnings.append(
    #             f"[계획검산] {row['month']}: wip_plan={actual_wip:.0f}, "
    #             f"Little's Law 기대치={expected_wip:.0f}, "
    #             f"편차={deviation*100:.1f}%"
    #         )
    # return warnings
    raise NotImplementedError
