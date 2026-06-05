"""
리포팅 모듈 — 파라미터 리포트, 예측 CSV, 경고 로그 저장

출력 파일:
  output/parameters.txt    — 파라미터 및 LOOCV 지표
  output/predictions.csv   — 월별 예측 테이블
  output/warnings.log      — 포화/외삽/점유/계획검산 경고
"""

import os
import csv
import logging
from typing import List, Dict
from oht_forecast.constants import LOWLOAD_N, TARGET_UTIL, TOTAL_SLOT, OCC_WARN
from oht_forecast.fitting import (
    MoveQtyParams, MoveTimeParams, StorageProdParams, StorageNPWParams,
)
from oht_forecast.prediction import MonthForecast, OHTBand

logger = logging.getLogger(__name__)


def parameter_report(mq: MoveQtyParams,
                     mt: MoveTimeParams,
                     sp: StorageProdParams,
                     snpw: StorageNPWParams,
                     loocv: Dict[str, Dict[str, float]]) -> str:
    """
    파라미터 및 검증 지표를 사람이 읽기 좋은 텍스트로 반환한다.

    물리 타당성 체크 목록 (PASS/FAIL 포함):
      - T0 > 0
      - b > 0
      - k > 0
      - alpha > 0
      - delta > 0
      - T0 < (move_time 최솟값) — 여기서는 비교 불가, 호출자가 확인

    Returns:
        str (multi-line text)

    Example output:
        ===== OHT Forecast Model Parameters =====
        학습 데이터: 52개월 (2022-01 ~ 2026-04)
        저부하 T0 추정: 하위 6개월 move_time 평균

        [① 반송량]  move_qty = k0 + k*(prod/lot_size)
          k0  = 0.0000  (미사용)
          k   = 0.2800
          R²  = 0.9650
          LOOCV MAPE = 3.20%   RMSE = 12.50

        [② 기본 반송시간]
          T0  = 55.00 s

        [② 반송시간 혼잡항]  move_time = T0 + b*(cong/(1-cong))
          b   = 120.00 ± 8.50 (1σ)
          R²  = 0.9420
          LOOCV MAPE = 4.15%   RMSE = 6.30

        [③a 생산저장]  storage_prod = α*wip + β*wip*(cong/(1-cong))
          α   = 0.550000   β = 0.003000  (β 유의: True)
          R²  = 0.9710
          LOOCV MAPE = 5.80%   RMSE = 320.10

        [③b 비생산저장]  storage_npw = γ + δ*move_qty
          γ   = 500.00   δ = 1.8000
          R²  = 0.9580
          LOOCV MAPE = 4.90%   RMSE = 180.20

        [물리 타당성]
          T0 > 0   : PASS
          b > 0    : PASS
          k > 0    : PASS
          alpha > 0: PASS
          delta > 0: PASS

        ===== 알려진 한계 =====
          - cong > 0.85 구간은 실측 없음 (이론 외삽)
          - 52행 월집계, 단일 라인/단일 DR 가정
          - 예측 품질은 생산계획·재공계획 품질에 종속
    """
    # TODO: 구현
    # lines = []
    # lines.append("===== OHT Forecast Model Parameters =====")
    # ...
    # return "\n".join(lines)
    raise NotImplementedError


def save_parameter_report(report: str, output_dir: str) -> None:
    """parameters.txt에 파라미터 리포트 저장"""
    # TODO: with open(os.path.join(output_dir, 'parameters.txt'), 'w', ...) as f: f.write(report)
    raise NotImplementedError


def save_predictions_csv(forecasts: List[MonthForecast],
                          bands: List[OHTBand],
                          output_dir: str) -> None:
    """
    predictions.csv 저장

    컬럼 순서:
      month, move_qty,
      oht_required, oht_lo1, oht_hi1, oht_lo2, oht_hi2,
      move_time, cong,
      storage_prod, storage_npw, storage_total, occupancy,
      warn_saturation, warn_occupancy, warn_convergence, extrapolation
    """
    # TODO: 구현
    # fieldnames = ['month','move_qty','oht_required','oht_lo1','oht_hi1',
    #               'oht_lo2','oht_hi2','move_time','cong',
    #               'storage_prod','storage_npw','storage_total','occupancy',
    #               'warn_saturation','warn_occupancy','warn_convergence','extrapolation']
    # path = os.path.join(output_dir, 'predictions.csv')
    # with open(path, 'w', newline='', encoding='utf-8') as f:
    #     writer = csv.DictWriter(f, fieldnames=fieldnames)
    #     writer.writeheader()
    #     for fc, band in zip(forecasts, bands):
    #         writer.writerow({...})
    raise NotImplementedError


def save_warnings_log(warnings: list, output_dir: str) -> None:
    """
    warnings.log 저장

    경고 유형:
      [포화]    month: 역산 중 cong >= 1 발생
      [비수렴]  month: CONVERGE_MAXIT 초과
      [점유초과] month: occupancy = X.XX (>= OCC_WARN)
      [외삽]   month: cong = X.XX (> 0.85)
      [계획검산] month: WIP 계획 Little's Law 기준 편차 XX%
      [β비유의] storage_prod 혼잡항 β 미유의로 제거됨
    """
    # TODO: 구현
    # path = os.path.join(output_dir, 'warnings.log')
    # with open(path, 'w', encoding='utf-8') as f:
    #     if not warnings:
    #         f.write("경고 없음\n")
    #     else:
    #         for w in warnings:
    #             f.write(w + "\n")
    raise NotImplementedError


def save_outputs(output_dir: str,
                 forecasts: List[MonthForecast],
                 bands: List[OHTBand],
                 mq: MoveQtyParams,
                 mt: MoveTimeParams,
                 sp: StorageProdParams,
                 snpw: StorageNPWParams,
                 loocv: dict,
                 warnings: list) -> None:
    """
    모든 출력 파일을 한 번에 저장하는 편의 함수 (main.py에서 호출)

    Args:
        output_dir: 출력 디렉토리 (없으면 생성)
        forecasts:  예측 결과
        bands:      OHT 불확실성 밴드
        mq/mt/sp/snpw: 적합 파라미터
        loocv:      LOOCV 결과
        warnings:   경고 문자열 리스트
    """
    # TODO: 구현
    # os.makedirs(output_dir, exist_ok=True)
    # report = parameter_report(mq, mt, sp, snpw, loocv)
    # save_parameter_report(report, output_dir)
    # save_predictions_csv(forecasts, bands, output_dir)
    # save_warnings_log(warnings, output_dir)
    # logger.info("출력 저장 완료: %s", output_dir)
    raise NotImplementedError
