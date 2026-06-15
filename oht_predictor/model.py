"""
OHT / Storage 회귀 모델 적합 (학습)
======================================
수식:
  ① move_qty   = k · (prod / lot_size)                    [절편 없는 OLS]
  ② move_time  = t0 + v_load·load_dist + b·cong/(1−cong)  [표준화 OLS → 역변환]
  ③ storage_prod = α·wip + β·wip·cong/(1−cong)            [절편 없는 OLS]
  ④ storage_npw  = γ + δ·move_qty                          [절편 있는 OLS]

설계 원칙:
  - 혼잡도(cong)는 move_time을 포함하지 않음 → 순환 의존 차단
  - load_dist의 mm 단위 크기 때문에 반드시 표준화 후 회귀 → 역변환
  - β 개선효과가 R² 기준 2% 미만이면 단순 모델(β=0)로 축소
  - LOOCV MAPE로 과적합 없는 예측 정확도 평가
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from constants import LOWLOAD_N, LOAD_CONST_MODE, LOAD_CONST_WIN


# ── 데이터 클래스 ─────────────────────────────────────────────────────────────

@dataclass
class ModelParams:
    # 반송량
    k: float = 0.0

    # 반송시간
    t0: float = 0.0
    v_load: float = 0.0
    b: float = 0.0
    se_b: float = 0.0
    T0_ref: float = 0.0
    load_const: float = 0.0
    load_const_std: float = 0.0

    # 저장량
    alpha: float = 0.0
    beta: float = 0.0
    use_beta: bool = True
    gamma: float = 0.0
    delta: float = 0.0

    # 고정값
    OHT_FIXED: int = 0

    # 표준화 스케일러 (역변환 재현용, 저장만)
    scaler: dict = field(default_factory=dict)


@dataclass
class ModelMetrics:
    move_qty_r2: float = 0.0
    move_qty_mape_cv: float = 0.0
    move_time_r2: float = 0.0
    move_time_mape_cv: float = 0.0
    storage_prod_r2: float = 0.0
    storage_prod_mape_cv: float = 0.0
    storage_npw_r2: float = 0.0
    storage_npw_mape_cv: float = 0.0


# ── 공개 API ──────────────────────────────────────────────────────────────────

def fit(df: pd.DataFrame) -> tuple[ModelParams, ModelMetrics]:
    """
    실적 DataFrame 전체를 학습하여 (ModelParams, ModelMetrics) 반환.
    df 는 data_loader.load_actuals() 결과를 그대로 넣으면 됩니다.
    """
    p, m = ModelParams(), ModelMetrics()
    _fit_move_qty(df, p, m)
    _compute_references(df, p)
    _fit_move_time(df, p, m)
    _fit_storage_prod(df, p, m)
    _fit_storage_npw(df, p, m)
    p.OHT_FIXED = int(df["oht_count"].iloc[-1])
    return p, m


def calc_congestion(
    move_qty: np.ndarray | float,
    T0_ref: float,
    oht_count: np.ndarray | float,
) -> np.ndarray:
    """
    혼잡도 = move_qty·T0_ref / (oht_count·3600)

    순환 차단: cong 계산에 move_time 을 포함하지 않습니다.
    cong ≥ 1.0 → 물리적 포화 (OHT 수용 초과)
    """
    return np.asarray(move_qty, dtype=float) * T0_ref / (
        np.asarray(oht_count, dtype=float) * 3600.0
    )


# ── 내부 학습 함수 ────────────────────────────────────────────────────────────

def _fit_move_qty(df: pd.DataFrame, p: ModelParams, m: ModelMetrics) -> None:
    """① 반송량: move_qty = k·(prod/lot_size)  — 절편 없는 최소제곱"""
    x = (df["prod"] / df["lot_size"]).values.astype(float)
    y = df["move_qty"].values.astype(float)
    k = float((x @ y) / (x @ x))
    p.k = k
    y_hat = k * x
    m.move_qty_r2 = _r2(y, y_hat)
    m.move_qty_mape_cv = _loocv_no_intercept(x, y)


def _compute_references(df: pd.DataFrame, p: ModelParams) -> None:
    """T0_ref (저부하 move_time 평균) 및 load_const 계산"""
    low_idx = df["move_time"].nsmallest(LOWLOAD_N).index
    p.T0_ref = float(df.loc[low_idx, "move_time"].mean())

    if LOAD_CONST_MODE == "recent":
        win = min(LOAD_CONST_WIN, len(df))
        vals = df["load_dist"].iloc[-win:].astype(float)
    else:
        vals = df["load_dist"].astype(float)
    p.load_const = float(vals.mean())
    p.load_const_std = float(vals.std(ddof=1))


def _fit_move_time(df: pd.DataFrame, p: ModelParams, m: ModelMetrics) -> None:
    """② 반송시간: 표준화 OLS → 원단위 역변환"""
    cong = calc_congestion(df["move_qty"].values, p.T0_ref, df["oht_count"].values)
    valid = cong < 1.0
    X1 = df.loc[valid, "load_dist"].values.astype(float)
    X2 = (cong[valid] / (1.0 - cong[valid]))
    y  = df.loc[valid, "move_time"].values.astype(float)

    # 표준화
    mX1, sX1 = X1.mean(), X1.std(ddof=1)
    mX2, sX2 = X2.mean(), X2.std(ddof=1)
    my,  sy  = y.mean(),  y.std(ddof=1)

    X1n = (X1 - mX1) / sX1
    X2n = (X2 - mX2) / sX2
    yn  = (y  - my)  / sy

    Xn = np.column_stack([X1n, X2n])
    # 표준화 공간 OLS (절편 없음)
    coef_n, _, _, _ = np.linalg.lstsq(Xn, yn, rcond=None)
    b1n, b2n = coef_n

    # 원단위 역변환
    v_load = b1n * sy / sX1
    b      = b2n * sy / sX2
    t0     = my - v_load * mX1 - b * mX2

    p.t0, p.v_load, p.b = float(t0), float(v_load), float(b)
    p.scaler = dict(mX1=mX1, sX1=sX1, mX2=mX2, sX2=sX2, my=my, sy=sy)

    # b의 표준오차 (불확실성 밴드용)
    y_hat_n = Xn @ coef_n
    resid   = yn - y_hat_n
    n = len(yn)
    s2 = float((resid @ resid) / max(n - 2, 1))
    XtX_inv = np.linalg.inv(Xn.T @ Xn)
    p.se_b  = float(np.sqrt(XtX_inv[1, 1] * s2) * sy / sX2)

    y_hat = t0 + v_load * X1 + b * X2
    m.move_time_r2 = _r2(y, y_hat)
    m.move_time_mape_cv = _loocv_move_time(X1, X2, y, mX1, sX1, mX2, sX2, my, sy)


def _fit_storage_prod(df: pd.DataFrame, p: ModelParams, m: ModelMetrics) -> None:
    """③ 생산 FOUP: α·wip + β·wip·cong/(1−cong)  (β 유의성 검사 포함)"""
    cong  = calc_congestion(df["move_qty"].values, p.T0_ref, df["oht_count"].values)
    valid = cong < 1.0
    wip   = df.loc[valid, "wip"].values.astype(float)
    ct    = cong[valid] / (1.0 - cong[valid])
    y     = df.loc[valid, "storage_prod"].values.astype(float)

    # 2항 모델 (α, β)
    X2   = np.column_stack([wip, wip * ct])
    c2   = np.linalg.lstsq(X2, y, rcond=None)[0]
    r2_2 = _r2(y, X2 @ c2)

    # 1항 모델 (α만)
    c1   = float((wip @ y) / (wip @ wip))
    r2_1 = _r2(y, c1 * wip)

    if r2_2 - r2_1 > 0.02:   # β가 R² 2% 이상 기여 → 채택
        p.alpha, p.beta, p.use_beta = float(c2[0]), float(c2[1]), True
        m.storage_prod_r2 = r2_2
        m.storage_prod_mape_cv = _loocv_lstsq(X2, y)
    else:
        p.alpha, p.beta, p.use_beta = c1, 0.0, False
        m.storage_prod_r2 = r2_1
        m.storage_prod_mape_cv = _loocv_no_intercept(wip, y)


def _fit_storage_npw(df: pd.DataFrame, p: ModelParams, m: ModelMetrics) -> None:
    """④ 비생산 FOUP: γ + δ·move_qty  (절편 있는 OLS)"""
    x = df["move_qty"].values.astype(float)
    y = df["storage_npw"].values.astype(float)
    n = len(x)
    X = np.column_stack([np.ones(n), x])
    coef = np.linalg.lstsq(X, y, rcond=None)[0]
    p.gamma, p.delta = float(coef[0]), float(coef[1])
    m.storage_npw_r2 = _r2(y, X @ coef)
    m.storage_npw_mape_cv = _loocv_lstsq(X, y)


# ── 통계 유틸 ─────────────────────────────────────────────────────────────────

def _r2(y: np.ndarray, y_hat: np.ndarray) -> float:
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0


def _mape(y: np.ndarray, y_hat: np.ndarray) -> float:
    denom = np.where(np.abs(y) < 1e-9, 1e-9, np.abs(y))
    return float(np.mean(np.abs(y - y_hat) / denom))


def _loocv_no_intercept(x: np.ndarray, y: np.ndarray) -> float:
    preds = []
    for i in range(len(x)):
        mask = np.arange(len(x)) != i
        k = float((x[mask] @ y[mask]) / (x[mask] @ x[mask]))
        preds.append(k * x[i])
    return _mape(y, np.array(preds))


def _loocv_lstsq(X: np.ndarray, y: np.ndarray) -> float:
    preds = []
    for i in range(len(y)):
        mask = np.arange(len(y)) != i
        coef = np.linalg.lstsq(X[mask], y[mask], rcond=None)[0]
        preds.append(float(X[i] @ coef))
    return _mape(y, np.array(preds))


def _loocv_move_time(
    X1: np.ndarray, X2: np.ndarray, y: np.ndarray,
    mX1: float, sX1: float, mX2: float, sX2: float, my: float, sy: float,
) -> float:
    """move_time LOOCV: 각 fold에서 표준화→OLS→역변환 순서 유지"""
    preds = []
    for i in range(len(y)):
        mask = np.arange(len(y)) != i
        X1t, X2t, yt = X1[mask], X2[mask], y[mask]
        X1n = (X1t - mX1) / sX1
        X2n = (X2t - mX2) / sX2
        yn  = (yt  - my)  / sy
        Xn  = np.column_stack([X1n, X2n])
        coef = np.linalg.lstsq(Xn, yn, rcond=None)[0]
        v_load = coef[0] * sy / sX1
        b      = coef[1] * sy / sX2
        t0     = my - v_load * mX1 - b * mX2
        preds.append(t0 + v_load * X1[i] + b * X2[i])
    return _mape(y, np.array(preds))
