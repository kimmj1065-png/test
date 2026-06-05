"""
단계별 파라미터 적합 모듈

핵심 설계 원칙:
  - 4개 타깃(반송량/반송시간/생산저장/비생산저장)을 독립적으로 적합한다.
  - wip/wip_plan은 오직 ③ 저장량 함수에서만 사용한다.
    fit_move_qty, fit_move_time 에서 wip 변수를 절대 입력으로 쓰지 않는다.
  - cong(혼잡도) = move_qty * T0 / (oht_count * 3600) — move_time 미포함 (순환 방지)
  - 각 함수는 순수 함수(side-effect 없음): DataFrame을 변경하지 않는다.
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass
from scipy.optimize import curve_fit
from scipy import stats
from oht_forecast.constants import LOWLOAD_N

logger = logging.getLogger(__name__)


class FittingError(RuntimeError):
    """파라미터 적합 실패"""


# ── 결과 데이터클래스 ─────────────────────────────────────────────────────

@dataclass
class MoveQtyParams:
    """① 반송량 모델 파라미터: move_qty = k0 + k*(prod/lot_size)"""
    k: float
    k0: float               # 0.0 if origin-only fit chosen
    use_intercept: bool     # True면 절편 모델 채택
    r2_origin: float
    r2_intercept: float
    r2: float               # 채택된 모델의 R²


@dataclass
class MoveTimeParams:
    """② 반송시간 모델 파라미터: move_time = T0 + b*cong/(1-cong)"""
    T0: float               # 자유 주행 반송시간 (초), 저부하 LOWLOAD_N개월 평균
    b: float                # M/M/1 대기행렬 스케일 계수
    se_b: float             # b의 표준오차 (curve_fit pcov에서)
    r2: float               # T_wait 적합 R²
    n_valid: int            # cong < 1 인 유효 행 수


@dataclass
class StorageProdParams:
    """③a 생산저장 모델 파라미터: storage_prod = α*wip + β*wip*(cong/(1-cong))"""
    alpha: float
    beta: float             # 유의하지 않으면 0.0
    beta_significant: bool  # p < 0.05
    r2: float


@dataclass
class StorageNPWParams:
    """③b 비생산저장 모델 파라미터: storage_npw = γ + δ*move_qty"""
    gamma: float            # 절편
    delta: float            # 반송량 계수
    r2: float


# ── 내부 유틸 ─────────────────────────────────────────────────────────────

def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """결정계수 R² 계산 (중심화 SS 기준)"""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    if ss_tot == 0:
        return 1.0
    return float(1.0 - ss_res / ss_tot)


def compute_congestion(move_qty: np.ndarray,
                       oht_count: np.ndarray,
                       T0: float) -> np.ndarray:
    """
    혼잡도 계산 (학습용 — 실적 oht_count 기반)

    cong = move_qty * T0 / (oht_count * 3600)

    중요: move_time이 이 식에 들어가지 않아야 순환 의존이 없다.
          T0를 먼저 estimate_T0()로 구한 다음 이 함수를 호출해야 한다.

    Args:
        move_qty:  시간당 반송량 (회/hr), shape (N,)
        oht_count: 가동 OHT 대수, shape (N,)
        T0:        기본 반송시간 (초)

    Returns:
        cong array, shape (N,).  이론상 0~1 사이이지만 실적 노이즈로 >=1 가능.
    """
    # TODO: return move_qty * T0 / (oht_count * 3600)
    raise NotImplementedError


# ── 공개 적합 함수 ────────────────────────────────────────────────────────

def fit_move_qty(df: pd.DataFrame) -> MoveQtyParams:
    """
    ① 반송량 적합: move_qty = k*(prod/lot_size)  [원점 통과] 또는
                             k*(prod/lot_size) + k0 [절편 포함]

    두 모델 모두 계산 후 R² 기준으로 채택한다.
    R² 차이 < 0.005 이면 원점 통과 우선 (물리적으로 더 자연스러움).

    ⚠ wip 변수를 절대 사용하지 않는다.

    Args:
        df: load_actuals()가 반환한 DataFrame

    Returns:
        MoveQtyParams

    Raises:
        FittingError: prod/lot_size 변동이 전혀 없는 경우
    """
    # TODO: 구현
    # Step 1: x = df['prod'].values / df['lot_size'].values  → shape (N,)
    # Step 2: y = df['move_qty'].values
    # Step 3: 원점 통과: k = (x @ y) / (x @ x)   (해석해)
    #         r2_origin = _r2(y, k * x)
    # Step 4: 절편 포함: np.polyfit(x, y, 1) 또는 sklearn LinearRegression
    #         r2_intercept = _r2(y, k1*x + k0)
    # Step 5: 채택 기준: abs(r2_intercept - r2_origin) < 0.005 → origin 선택
    # Step 6: MoveQtyParams 반환
    raise NotImplementedError


def estimate_T0(df: pd.DataFrame) -> float:
    """
    기본 반송시간 T0 추정 — 혼잡 없는 상태에서의 순수 이동 시간

    부하율 하위 LOWLOAD_N개월의 move_time 평균으로 추정한다.
    부하율 = move_qty * move_time / 3600 / oht_count

    ⚠ T0 추정에 사용하는 부하율 계산은 move_time을 포함하지만,
      이후 cong 계산(compute_congestion)에서는 T0만 쓰고 move_time을 쓰지 않는다.
      → 순환 의존 없음.

    LOOCV 각 fold에서 반드시 train_df 기준으로 재계산해야 한다.

    Args:
        df: load_actuals()가 반환한 DataFrame

    Returns:
        T0 (초, float)

    Raises:
        FittingError: T0 <= 0
    """
    # TODO: 구현
    # Step 1: util = df['move_qty'] * df['move_time'] / 3600 / df['oht_count']
    # Step 2: idx = util.nsmallest(LOWLOAD_N).index
    #         실제 행이 LOWLOAD_N 미만이면 모든 행 사용 + WARNING
    # Step 3: T0 = df.loc[idx, 'move_time'].mean()
    # Step 4: T0 <= 0 이면 FittingError
    raise NotImplementedError


def fit_move_time(df: pd.DataFrame) -> MoveTimeParams:
    """
    ② 반송시간 적합: T_wait = b * cong / (1 - cong)
                    move_time = T0 + T_wait

    M/M/1 대기행렬 이론에서 대기시간 형태를 고정하고
    스케일 계수 b만 곡선적합(curve_fit)으로 추정한다.

    ⚠ cong 계산에 move_time을 사용하지 않는다 (compute_congestion 참고).

    Args:
        df: load_actuals()가 반환한 DataFrame

    Returns:
        MoveTimeParams (T0, b, se_b 포함)

    Raises:
        FittingError: curve_fit 수렴 실패, 또는 유효 행 < 3
    """
    # TODO: 구현
    # Step 1: T0 = estimate_T0(df)
    # Step 2: cong = compute_congestion(df['move_qty'].values, df['oht_count'].values, T0)
    # Step 3: valid_mask = cong < 1.0
    #         cong_valid, move_time_valid = cong[valid_mask], df['move_time'].values[valid_mask]
    #         cong >= 1 행이 있으면 WARNING 로그
    #         len(cong_valid) < 3 → FittingError
    # Step 4: T_wait_obs = move_time_valid - T0
    # Step 5: def queuing_curve(c, b): return b * c / (1 - c)
    #         popt, pcov = curve_fit(queuing_curve, cong_valid, T_wait_obs,
    #                                p0=[1.0], bounds=(0, np.inf), maxfev=5000)
    #         실패 시 p0=[0.1], p0=[10.0] 재시도 후 FittingError
    # Step 6: b = popt[0], se_b = sqrt(pcov[0, 0])
    # Step 7: y_hat = queuing_curve(cong_valid, b)
    #         r2 = _r2(T_wait_obs, y_hat)
    # Step 8: MoveTimeParams(T0=T0, b=b, se_b=se_b, r2=r2, n_valid=...) 반환
    raise NotImplementedError


def fit_storage_prod(df: pd.DataFrame,
                     mt_params: MoveTimeParams) -> StorageProdParams:
    """
    ③a 생산 FOUP 저장량 적합
    storage_prod = α*wip + β*wip*(cong/(1-cong))

    혼잡이 높을수록 재공이 더 많이 Storage에 쌓이는 비선형 효과를 포착한다.
    β가 통계적으로 유의하지 않으면(p > 0.05) β=0으로 축소한다.

    ⚠ wip은 이 함수에만 사용된다. ①② 함수에서 wip을 사용하지 않는다.

    Args:
        df:         load_actuals()가 반환한 DataFrame
        mt_params:  fit_move_time() 결과 (T0 사용)

    Returns:
        StorageProdParams

    Raises:
        FittingError: 설계행렬이 특이(singular)한 경우
    """
    # TODO: 구현
    # Step 1: cong = compute_congestion(df['move_qty'].values, df['oht_count'].values, mt_params.T0)
    #         cong >= 1 행은 0.99로 클램프 (fit 목적으로만, 예측에는 별도 처리)
    # Step 2: nonlinear_term = df['wip'].values * cong / (1 - cong)
    # Step 3: X = np.column_stack([df['wip'].values, nonlinear_term])  # (N, 2)
    #         y = df['storage_prod'].values
    # Step 4: coeffs, residuals, rank, sv = np.linalg.lstsq(X, y, rcond=None)
    #         rank < 2 → FittingError("singular design matrix")
    # Step 5: β 유의성 t-검정
    #         n, p_params = len(y), 2
    #         RSS = np.sum((y - X @ coeffs) ** 2)
    #         s2 = RSS / (n - p_params)
    #         XtX_inv = np.linalg.inv(X.T @ X)
    #         se = np.sqrt(s2 * np.diag(XtX_inv))
    #         t_stat = coeffs / se
    #         p_val = 2 * scipy.stats.t.sf(np.abs(t_stat), df=n - p_params)
    #         beta_sig = p_val[1] < 0.05
    # Step 6: beta_sig=False → beta=0.0, alpha = 단순 OLS (wip만)
    # Step 7: r2 = _r2(y, X @ coeffs)
    # Step 8: StorageProdParams 반환
    raise NotImplementedError


def fit_storage_npw(df: pd.DataFrame) -> StorageNPWParams:
    """
    ③b 비생산 FOUP 저장량 적합
    storage_npw = γ + δ*move_qty

    NPW/Empty FOUP은 사용 후 return 흐름에서 발생하므로 반송량이 주 동인.

    Args:
        df: load_actuals()가 반환한 DataFrame

    Returns:
        StorageNPWParams
    """
    # TODO: 구현
    # x = df['move_qty'].values, y = df['storage_npw'].values
    # 절편 포함 OLS: np.polyfit(x, y, 1) → [delta, gamma]
    # r2 = _r2(y, delta*x + gamma)
    raise NotImplementedError


def fit_all(df: pd.DataFrame) -> dict:
    """
    전체 파라미터 적합 — 단계 순서대로 호출하는 편의 함수

    Returns:
        {
          'mq':   MoveQtyParams,
          'mt':   MoveTimeParams,   # T0, b, se_b 포함
          'sp':   StorageProdParams,
          'snpw': StorageNPWParams,
        }
    """
    # TODO: 구현
    # mq = fit_move_qty(df)
    # mt = fit_move_time(df)    ← T0 추정 포함
    # sp = fit_storage_prod(df, mt)
    # snpw = fit_storage_npw(df)
    # return {'mq': mq, 'mt': mt, 'sp': sp, 'snpw': snpw}
    raise NotImplementedError
