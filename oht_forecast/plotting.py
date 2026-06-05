"""
시각화 모듈 — 4개 matplotlib 그래프 생성

그래프 목록:
  1. move_qty_timeseries.png    — 시간당 반송량 실적+예측 시계열
  2. move_time_fit.png          — 혼잡도 vs 반송시간 적합 곡선 (외삽 구간 음영)
  3. oht_required.png           — 필요 OHT 대수 + 불확실성 밴드
  4. storage_occupancy.png      — Storage 점유율 + 경보선

make_plots() 호출 시 2×2 combined 그래프도 함께 저장한다.
"""

import os
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 서버 환경(GUI 없음) 대응
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import List
from oht_forecast.constants import OCC_WARN, TOTAL_SLOT
from oht_forecast.fitting import MoveTimeParams
from oht_forecast.prediction import MonthForecast, OHTBand

logger = logging.getLogger(__name__)


def _month_labels(periods) -> list:
    """Period 배열을 'YYYY-MM' 문자열 리스트로 변환"""
    return [str(p) for p in periods]


def plot_move_qty(ax: plt.Axes,
                  actuals_df: pd.DataFrame,
                  forecasts: List[MonthForecast],
                  loocv_mape: float = None) -> None:
    """
    [Plot 1] 시간당 반송량 시계열 (실적 + 예측)

    레이아웃:
      - 실적: 파란 실선 + 원형 마커
      - 예측 central: 주황 점선 + 다이아몬드 마커
      - 예측 ±MAPE 밴드 (loocv_mape 제공 시): 연주황 채움
      - 실적/예측 경계: 회색 세로 점선
      - x축 레이블 45° 회전

    Args:
        ax:           matplotlib Axes
        actuals_df:   학습 실적 DataFrame (move_qty 컬럼)
        forecasts:    예측 결과 리스트
        loocv_mape:   반송량 LOOCV MAPE(%) — None이면 밴드 생략
    """
    # TODO: 구현
    # hist_x = list(range(len(actuals_df)))
    # hist_y = actuals_df['move_qty'].values
    # fcast_x = list(range(len(actuals_df), len(actuals_df) + len(forecasts)))
    # fcast_y = [f.move_qty for f in forecasts]
    #
    # ax.plot(hist_x, hist_y, 'b-o', label='실적')
    # ax.plot(fcast_x, fcast_y, 'darkorange', linestyle='--', marker='D', label='예측')
    # if loocv_mape is not None:
    #     band = np.array(fcast_y) * (loocv_mape / 100)
    #     ax.fill_between(fcast_x, np.array(fcast_y)-band, np.array(fcast_y)+band,
    #                     alpha=0.25, color='orange', label=f'±{loocv_mape:.1f}% MAPE 밴드')
    # ax.axvline(len(actuals_df)-0.5, color='grey', linestyle=':')
    # all_labels = _month_labels(actuals_df['month']) + [f.month for f in forecasts]
    # ax.set_xticks(range(len(all_labels)))
    # ax.set_xticklabels(all_labels, rotation=45, ha='right', fontsize=7)
    # ax.set_ylabel('Move Qty (trips/hr)')
    # ax.set_title('시간당 반송량 (Move Qty): 실적 & 예측')
    # ax.legend()
    raise NotImplementedError


def plot_move_time_fit(ax: plt.Axes,
                       actuals_df: pd.DataFrame,
                       mt_params: MoveTimeParams) -> None:
    """
    [Plot 2] 혼잡도 vs 반송시간 — 적합 곡선 + 외삽 음영

    레이아웃:
      - 실적 scatter: 회색, utilisation 컬러맵(viridis)
      - 적합 곡선 cong 0~0.85: 파란 실선
      - 외삽 구간 cong 0.85~0.99: 빨간 점선 + 연빨간 배경 음영
      - 수직 점선 cong=0.85: "검증/외삽 경계"
      - 범례에 "cong≤0.85: 검증 / cong>0.85: 외삽(불확실)" 명시

    Args:
        ax:         matplotlib Axes
        actuals_df: 학습 실적 DataFrame (move_qty, move_time, oht_count)
        mt_params:  MoveTimeParams (T0, b)
    """
    # TODO: 구현
    # from oht_forecast.fitting import compute_congestion
    # cong = compute_congestion(actuals_df['move_qty'].values,
    #                           actuals_df['oht_count'].values,
    #                           mt_params.T0)
    # T_wait_obs = actuals_df['move_time'].values - mt_params.T0
    # util = (actuals_df['move_qty'] * actuals_df['move_time'] / 3600 / actuals_df['oht_count']).values
    #
    # sc = ax.scatter(cong, T_wait_obs, c=util, cmap='viridis', s=40, alpha=0.8, label='실적')
    # plt.colorbar(sc, ax=ax, label='부하율(util)')
    #
    # c_fit = np.linspace(0.01, 0.85, 300)
    # ax.plot(c_fit, mt_params.b * c_fit / (1 - c_fit), 'b-', lw=2, label='적합 곡선')
    #
    # c_extrap = np.linspace(0.85, 0.99, 200)
    # ax.plot(c_extrap, mt_params.b * c_extrap / (1 - c_extrap), 'r--', lw=1.5, label='외삽')
    # ax.fill_betweenx([0, ax.get_ylim()[1] * 1.2], 0.85, 0.99, alpha=0.1, color='red')
    # ax.axvline(0.85, color='grey', linestyle='--', label='검증/외삽 경계')
    #
    # ax.annotate(f'T0={mt_params.T0:.1f}s, b={mt_params.b:.2f}±{mt_params.se_b:.2f}',
    #             xy=(0.05, 0.85), xycoords='axes fraction')
    # ax.set_xlabel('혼잡도 (cong)'); ax.set_ylabel('대기시간 (s)')
    # ax.set_title('반송시간 적합 곡선 — M/M/1 대기행렬')
    # ax.legend()
    raise NotImplementedError


def plot_oht_required(ax: plt.Axes,
                      forecasts: List[MonthForecast],
                      bands: List[OHTBand],
                      actuals_df: pd.DataFrame = None) -> None:
    """
    [Plot 3] 필요 OHT 대수 + 불확실성 밴드

    레이아웃:
      - 파란 막대: oht_required (central, ceil)
      - 오차 막대 ±1σ: 짙은 파란 error bar
      - 오차 막대 ±2σ: 연한 파란 error bar
      - 경보 마커: warn_saturation 또는 warn_convergence → 빨간 'X'
      - 참조선: 실적 oht_count 최대값 (회색 수평 점선)
      - 외삽 월: x축 레이블에 '*' 표시

    Args:
        ax:          matplotlib Axes
        forecasts:   예측 결과 리스트 (MonthForecast)
        bands:       불확실성 밴드 (OHTBand)
        actuals_df:  참조선용 실적 DataFrame (optional)
    """
    # TODO: 구현
    # x = range(len(forecasts))
    # y_central = [b.oht_central for b in bands]
    # err_lo1 = [b.oht_central - b.oht_lo1 for b in bands]
    # err_hi1 = [b.oht_hi1 - b.oht_central for b in bands]
    # err_lo2 = [b.oht_central - b.oht_lo2 for b in bands]
    # err_hi2 = [b.oht_hi2 - b.oht_central for b in bands]
    #
    # ax.bar(x, y_central, color='steelblue', alpha=0.7, label='필요 OHT (central)')
    # ax.errorbar(x, y_central, yerr=[err_lo1, err_hi1], fmt='none',
    #             capsize=4, color='navy', label='±1σ')
    # ax.errorbar(x, y_central, yerr=[err_lo2, err_hi2], fmt='none',
    #             capsize=4, color='lightblue', label='±2σ')
    #
    # # 외삽/경보 표시
    # for i, (fc, band) in enumerate(zip(forecasts, bands)):
    #     if fc.warn_saturation or fc.warn_convergence:
    #         ax.annotate('✕', xy=(i, band.oht_hi2), color='red', ha='center')
    #     if fc.extrapolation:
    #         pass  # x축 레이블에 '*' 추가
    #
    # if actuals_df is not None:
    #     ax.axhline(actuals_df['oht_count'].max(), color='grey', linestyle=':',
    #                label=f'실적 최대: {actuals_df["oht_count"].max():.0f}대')
    #
    # labels = [('*'+f.month if f.extrapolation else f.month) for f in forecasts]
    # ax.set_xticks(x); ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=7)
    # ax.set_ylabel('필요 OHT 대수'); ax.set_title('필요 OHT 대수 (목표 부하율 85%)')
    # ax.legend()
    raise NotImplementedError


def plot_storage_occupancy(ax: plt.Axes,
                           actuals_df: pd.DataFrame,
                           forecasts: List[MonthForecast]) -> None:
    """
    [Plot 4] Storage 점유율 + 경보선

    레이아웃:
      - 실적 occupancy: 녹색 실선
      - 예측 occupancy: 녹색 점선
      - 스택 막대 (배경): storage_prod(연파랑), storage_npw(연주황) (2차 y축)
      - 수평 점선 OCC_WARN: 빨간색 "경보 임계"
      - OCC_WARN 초과 예측 월: 배경 연빨간 음영
      - y축 우: 실제 storage 수량

    Args:
        ax:         matplotlib Axes
        actuals_df: 실적 DataFrame (storage_prod, storage_npw 컬럼)
        forecasts:  예측 결과 리스트
    """
    # TODO: 구현
    # hist_occ = (actuals_df['storage_prod'] + actuals_df['storage_npw']) / TOTAL_SLOT
    # fcast_occ = [f.occupancy for f in forecasts]
    #
    # n_hist = len(actuals_df)
    # n_fcast = len(forecasts)
    # x_hist = range(n_hist)
    # x_fcast = range(n_hist, n_hist + n_fcast)
    #
    # ax.plot(x_hist,  hist_occ,  'g-',  label='실적 점유율')
    # ax.plot(x_fcast, fcast_occ, 'g--', label='예측 점유율')
    # ax.axhline(OCC_WARN, color='red', linestyle='--', label=f'경보 임계 {OCC_WARN*100:.0f}%')
    #
    # # 경보 초과 구간 음영
    # for i, fc in enumerate(forecasts):
    #     if fc.warn_occupancy:
    #         ax.axvspan(n_hist+i-0.5, n_hist+i+0.5, alpha=0.15, color='red')
    #
    # ax.set_ylim(0, 1.05)
    # ax.set_ylabel('점유율 (occupancy)')
    # ax.set_title('Storage 점유율: 실적 & 예측')
    # ax.legend()
    raise NotImplementedError


def make_plots(actuals_df: pd.DataFrame,
               forecasts: List[MonthForecast],
               bands: List[OHTBand],
               mt_params: MoveTimeParams,
               loocv: dict,
               output_dir: str) -> None:
    """
    4개 그래프를 개별 PNG + 2×2 combined PNG로 저장

    Args:
        actuals_df:  학습 실적 DataFrame
        forecasts:   예측 결과 리스트
        bands:       OHT 불확실성 밴드
        mt_params:   반송시간 파라미터 (T0, b, se_b)
        loocv:       loocv_report() 결과 (move_qty MAPE 추출용)
        output_dir:  저장 디렉토리

    Output:
        {output_dir}/plots/move_qty_timeseries.png
        {output_dir}/plots/move_time_fit.png
        {output_dir}/plots/oht_required.png
        {output_dir}/plots/storage_occupancy.png
        {output_dir}/plots/combined.png
    """
    # TODO: 구현
    # plots_dir = os.path.join(output_dir, 'plots')
    # os.makedirs(plots_dir, exist_ok=True)
    #
    # mq_mape = loocv.get('move_qty', {}).get('mape') if loocv else None
    #
    # # 개별 그래프
    # fig, ax = plt.subplots(figsize=(12, 5))
    # plot_move_qty(ax, actuals_df, forecasts, mq_mape)
    # fig.savefig(os.path.join(plots_dir, 'move_qty_timeseries.png'), dpi=120, bbox_inches='tight')
    # plt.close(fig)
    #
    # ... (나머지 3개 동일 패턴)
    #
    # # 2×2 combined
    # fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    # plot_move_qty(axes[0,0], ...)
    # plot_move_time_fit(axes[0,1], ...)
    # plot_oht_required(axes[1,0], ...)
    # plot_storage_occupancy(axes[1,1], ...)
    # fig.tight_layout()
    # fig.savefig(os.path.join(plots_dir, 'combined.png'), dpi=120, bbox_inches='tight')
    # plt.close(fig)
    raise NotImplementedError
