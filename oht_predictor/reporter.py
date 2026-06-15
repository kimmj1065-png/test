"""
산출물 생성 모듈
=================
A) param_report.txt   — 파라미터 및 정확도 리포트
B) forecast.csv       — 월별 예측 테이블
C) 그래프 5종 (PNG)
   plot_move_qty.png  — 반송량 시계열
   plot_move_time.png — 반송시간 시계열 + 불확실성 밴드
   plot_scatter.png   — move_time 실측 vs 예측 산점도
   plot_util.png      — 부하율 시계열
   plot_occupancy.png — Storage 점유율 시계열
D) warnings.txt       — 경고 로그
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates

from constants import TOTAL_SLOT, UTIL_WARN, OCC_WARN
from model import ModelParams, ModelMetrics, calc_congestion

OUTPUT_DIR = Path(__file__).parent / "output"

# 한글 폰트 설정 (NanumGothic 우선, 없으면 시스템 기본)
_NANUM = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
if Path(_NANUM).exists():
    fm.fontManager.addfont(_NANUM)
    plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams.update({
    "font.size": 10,
    "axes.grid": True,
    "grid.alpha": 0.4,
    "axes.unicode_minus": False,
})


def save_all(
    actuals: pd.DataFrame,
    forecast: pd.DataFrame,
    p: ModelParams,
    m: ModelMetrics,
) -> None:
    """모든 산출물을 OUTPUT_DIR에 저장."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    _param_report(p, m)
    _forecast_csv(forecast)
    _warning_log(forecast)
    _plot_move_qty(actuals, forecast)
    _plot_move_time(actuals, forecast)
    _plot_scatter(actuals, p)
    _plot_util(actuals, forecast)
    _plot_occupancy(actuals, forecast)
    print(f"\n[완료] 산출물 경로 → {OUTPUT_DIR.resolve()}")


# ── A) 파라미터 리포트 ────────────────────────────────────────────────────────

def _param_report(p: ModelParams, m: ModelMetrics) -> None:
    lines = [
        "=" * 65,
        "  OHT/Storage 예측 모델 — 파라미터 리포트",
        "=" * 65,
        "",
        "■ 반송량  move_qty = k · (prod / lot_size)",
        f"    k            = {p.k:.6f}",
        f"    R²           = {m.move_qty_r2:.4f}",
        f"    MAPE(LOOCV)  = {m.move_qty_mape_cv*100:.2f}%",
        "",
        "■ 반송시간  move_time = t0 + v_load·load_dist + b·cong/(1−cong)",
        f"    t0           = {p.t0:.4f} 초",
        f"    v_load       = {p.v_load:.8f} 초/mm",
        f"    b            = {p.b:.4f} 초  (±se = {p.se_b:.4f})",
        f"    T0_ref       = {p.T0_ref:.2f} 초  (저부하 평균)",
        f"    load_const   = {p.load_const:.1f} mm  (σ = {p.load_const_std:.1f} mm)",
        f"    R²           = {m.move_time_r2:.4f}",
        f"    MAPE(LOOCV)  = {m.move_time_mape_cv*100:.2f}%",
        "",
        "■ 저장량 — 생산 FOUP  storage_prod = α·wip + β·wip·cong/(1−cong)",
        f"    α (alpha)    = {p.alpha:.6f}  [β 사용: {p.use_beta}]",
        f"    β (beta)     = {p.beta:.6f}",
        f"    R²           = {m.storage_prod_r2:.4f}",
        f"    MAPE(LOOCV)  = {m.storage_prod_mape_cv*100:.2f}%",
        "",
        "■ 저장량 — 비생산 FOUP  storage_npw = γ + δ·move_qty",
        f"    γ (gamma)    = {p.gamma:.4f}",
        f"    δ (delta)    = {p.delta:.6f}",
        f"    R²           = {m.storage_npw_r2:.4f}",
        f"    MAPE(LOOCV)  = {m.storage_npw_mape_cv*100:.2f}%",
        "",
        "■ 고정 상수",
        f"    OHT_FIXED    = {p.OHT_FIXED} 대  (학습 데이터 마지막 월)",
        f"    TOTAL_SLOT   = {TOTAL_SLOT:,} 슬롯",
        "=" * 65,
    ]
    text = "\n".join(lines)
    (OUTPUT_DIR / "param_report.txt").write_text(text, encoding="utf-8")
    print(text)


# ── B) 예측 CSV ───────────────────────────────────────────────────────────────

def _forecast_csv(forecast: pd.DataFrame) -> None:
    forecast.to_csv(OUTPUT_DIR / "forecast.csv", index=False, encoding="utf-8-sig")


# ── D) 경고 로그 ──────────────────────────────────────────────────────────────

def _warning_log(forecast: pd.DataFrame) -> None:
    flags = {
        "포화경보":   "cong ≥ 1  [물리적 포화]",
        "부하율경보":  f"util ≥ {UTIL_WARN}  [OHT 증설 신호]",
        "외삽여부":   "cong > 0.78  [과거 최대 초과, 외삽 구간]",
        "점유경보":   f"occupancy ≥ {OCC_WARN}  [Storage 부족]",
    }
    lines = ["[경고 로그]", ""]
    any_warn = False
    for col, label in flags.items():
        rows = forecast.loc[forecast[col] == True, "month"].dt.strftime("%Y-%m").tolist()
        if rows:
            lines.append(f"  {label}")
            lines.append(f"    해당 월: {', '.join(rows)}")
            lines.append("")
            any_warn = True
    if not any_warn:
        lines.append("  경고 없음")
    (OUTPUT_DIR / "warnings.txt").write_text("\n".join(lines), encoding="utf-8")


# ── C) 그래프 ────────────────────────────────────────────────────────────────

def _fmt_date(ax: plt.Axes) -> None:
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")


def _plot_move_qty(act: pd.DataFrame, fc: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(act["month"], act["move_qty"], "o-", ms=4, lw=1.5,
            label="실적", color="#2176AE")
    ax.plot(fc["month"],  fc["move_qty"],  "s--", ms=5, lw=1.5,
            label="예측", color="#E84855")
    ax.set_title("반송량 (move_qty) 시계열")
    ax.set_ylabel("반송량 (회/hr)")
    ax.legend()
    _fmt_date(ax)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "plot_move_qty.png", dpi=150)
    plt.close(fig)


def _plot_move_time(act: pd.DataFrame, fc: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(act["month"], act["move_time"], "o-", ms=4, lw=1.5,
            label="실적", color="#2176AE")
    ax.plot(fc["month"],  fc["move_time"],  "s-",  ms=5, lw=1.5,
            label="예측", color="#E84855")
    ax.fill_between(fc["month"], fc["move_time_lo"], fc["move_time_hi"],
                    alpha=0.2, color="#E84855", label="불확실성 밴드 (±1σ)")
    extrap = fc["외삽여부"]
    if extrap.any():
        xs = fc.loc[extrap, "month"]
        ax.axvspan(xs.iloc[0], xs.iloc[-1], alpha=0.08, color="gray",
                   label="외삽 구간")
    ax.set_title("반송시간 (move_time) 시계열 + 불확실성 밴드")
    ax.set_ylabel("반송시간 (초)")
    ax.legend()
    _fmt_date(ax)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "plot_move_time.png", dpi=150)
    plt.close(fig)


def _plot_scatter(act: pd.DataFrame, p: ModelParams) -> None:
    cong  = calc_congestion(act["move_qty"].values, p.T0_ref, act["oht_count"].values)
    valid = cong < 1.0
    X1    = act.loc[valid, "load_dist"].values.astype(float)
    X2    = cong[valid] / (1.0 - cong[valid])
    y     = act.loc[valid, "move_time"].values.astype(float)
    y_hat = p.t0 + p.v_load * X1 + p.b * X2

    lo = min(y.min(), y_hat.min()) * 0.97
    hi = max(y.max(), y_hat.max()) * 1.03

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(y, y_hat, s=30, color="#2176AE", alpha=0.7, edgecolors="white", lw=0.5)
    ax.plot([lo, hi], [lo, hi], "r--", lw=1, label="y=x")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("실측 move_time (초)")
    ax.set_ylabel("예측 move_time (초)")
    ax.set_title("반송시간 실측 vs 예측")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "plot_scatter.png", dpi=150)
    plt.close(fig)


def _plot_util(act: pd.DataFrame, fc: pd.DataFrame) -> None:
    act_util = act["move_qty"] * act["move_time"] / 3600.0 / act["oht_count"]
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(act["month"], act_util,   "o-",  ms=4, lw=1.5,
            label="실적 부하율", color="#2176AE")
    ax.plot(fc["month"],  fc["util"], "s-",  ms=5, lw=1.5,
            label="예측 부하율", color="#E84855")
    ax.fill_between(fc["month"], fc["util_lo"], fc["util_hi"],
                    alpha=0.2, color="#E84855")
    ax.axhline(UTIL_WARN, color="red", ls=":", lw=1.5,
               label=f"경보선 ({UTIL_WARN})")
    extrap = fc["외삽여부"]
    if extrap.any():
        xs = fc.loc[extrap, "month"]
        ax.axvspan(xs.iloc[0], xs.iloc[-1], alpha=0.08, color="gray",
                   label="외삽 구간")
    ax.set_title("OHT 부하율 (util) 시계열")
    ax.set_ylabel("부하율")
    ax.legend()
    _fmt_date(ax)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "plot_util.png", dpi=150)
    plt.close(fig)


def _plot_occupancy(act: pd.DataFrame, fc: pd.DataFrame) -> None:
    act_occ = (act["storage_prod"] + act["storage_npw"]) / TOTAL_SLOT
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(act["month"], act_occ,        "o-",  ms=4, lw=1.5,
            label="실적 점유율", color="#2176AE")
    ax.plot(fc["month"],  fc["occupancy"], "s-",  ms=5, lw=1.5,
            label="예측 점유율", color="#E84855")
    ax.axhline(OCC_WARN, color="red", ls=":", lw=1.5,
               label=f"경보선 ({OCC_WARN})")
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.set_title("Storage 점유율 시계열")
    ax.set_ylabel("점유율")
    ax.legend()
    _fmt_date(ax)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "plot_occupancy.png", dpi=150)
    plt.close(fig)
