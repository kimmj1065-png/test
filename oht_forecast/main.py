"""
OHT / Storage Capa 예측 모델 — CLI 진입점

사용법:
  python -m oht_forecast.main
  python -m oht_forecast.main --actuals data/actuals.csv --plan data/plan.csv --output output/
  python -m oht_forecast.main --no-plots --loglevel DEBUG

실행 플로우:
  1. 데이터 로드 (actuals.csv, plan.csv)
  2. 단계별 파라미터 적합 (fit_all)
  3. LOOCV 검증 (loocv_report)
  4. 민감도 분석 (sensitivity_analysis)
  5. 미래 월 예측 (predict)
  6. Little's Law 계획 검산
  7. 경고 수집 및 경고 로그 구성
  8. 물리 타당성 검사
  9. 출력 저장 (CSV, parameters.txt, warnings.log)
  10. 그래프 저장 (--no-plots 아닌 경우)
  11. 콘솔 요약 출력
"""

import argparse
import logging
import os
import sys
from oht_forecast.data_loader import load_actuals, load_plan
from oht_forecast.fitting import fit_all
from oht_forecast.prediction import predict
from oht_forecast.validation import loocv_report, sensitivity_analysis, check_littles_law
from oht_forecast.plotting import make_plots
from oht_forecast.reporting import save_outputs


def _collect_warnings(forecasts) -> list:
    """
    MonthForecast 리스트에서 경고 문자열을 수집한다.
    """
    # TODO: 구현
    # warnings = []
    # for fc in forecasts:
    #     if fc.warn_saturation:
    #         warnings.append(f"[포화]    {fc.month}: 역산 중 cong >= 1 발생")
    #     if fc.warn_convergence:
    #         warnings.append(f"[비수렴] {fc.month}: {CONVERGE_MAXIT}회 초과")
    #     if fc.warn_occupancy:
    #         warnings.append(f"[점유초과] {fc.month}: occupancy={fc.occupancy:.3f}")
    #     if fc.extrapolation:
    #         warnings.append(f"[외삽]   {fc.month}: cong={fc.cong:.3f} > 0.85")
    # return warnings
    raise NotImplementedError


def _print_summary(forecasts, loocv, params) -> None:
    """
    실행 완료 후 콘솔 요약 출력
    """
    # TODO: 구현
    # print("\n===== 예측 요약 =====")
    # print(f"예측 기간: {forecasts[0].month} ~ {forecasts[-1].month} ({len(forecasts)}개월)")
    # print(f"LOOCV move_qty  MAPE: {loocv['move_qty']['mape']:.2f}%")
    # print(f"LOOCV move_time MAPE: {loocv['move_time']['mape']:.2f}%")
    # mt = params['mt']
    # print(f"T0={mt.T0:.1f}s, b={mt.b:.2f}±{mt.se_b:.2f}")
    # max_oht = max(f.oht_required for f in forecasts)
    # max_occ = max(f.occupancy for f in forecasts)
    # print(f"필요 OHT 최대: {max_oht}대  |  Storage 최대 점유율: {max_occ*100:.1f}%")
    # alarm_months = [f.month for f in forecasts if f.warn_occupancy]
    # if alarm_months:
    #     print(f"⚠ 점유율 경보 월: {', '.join(alarm_months)}")
    raise NotImplementedError


def main():
    parser = argparse.ArgumentParser(
        description='OHT / Storage Capa 예측 모델',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python -m oht_forecast.main
  python -m oht_forecast.main --actuals data/actuals.csv --plan data/plan.csv
  python -m oht_forecast.main --no-plots --loglevel DEBUG
        """
    )
    parser.add_argument('--actuals',  default='data/actuals.csv',
                        help='학습 실적 CSV 경로 (기본: data/actuals.csv)')
    parser.add_argument('--plan',     default='data/plan.csv',
                        help='예측 계획 CSV 경로 (기본: data/plan.csv)')
    parser.add_argument('--output',   default='output',
                        help='출력 디렉토리 (기본: output/)')
    parser.add_argument('--no-plots', action='store_true',
                        help='그래프 생성 생략')
    parser.add_argument('--loglevel', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='로그 레벨 (기본: INFO)')
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.loglevel),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
    )

    os.makedirs(args.output, exist_ok=True)

    # TODO: 아래 단계를 순서대로 구현
    # Step 1: 데이터 로드
    # actuals_df = load_actuals(args.actuals)
    # plan_df    = load_plan(args.plan)
    # logging.info("실적 %d행 로드, 계획 %d행 로드", len(actuals_df), len(plan_df))

    # Step 2: 파라미터 적합
    # params = fit_all(actuals_df)
    # mq, mt, sp, snpw = params['mq'], params['mt'], params['sp'], params['snpw']

    # Step 3: LOOCV
    # logging.info("LOOCV 실행 중 (%d fold)...", len(actuals_df))
    # loocv = loocv_report(actuals_df)

    # Step 4: 민감도 분석
    # sens = sensitivity_analysis(actuals_df, mt, sp,
    #                              mq_loocv_mape=loocv['move_qty']['mape'])

    # Step 5: 미래 예측
    # forecasts, bands = predict(plan_df, mq, mt, sp, snpw)

    # Step 6: Little's Law 검산
    # littles_warnings = check_littles_law(plan_df)

    # Step 7: 경고 수집
    # warnings = _collect_warnings(forecasts) + littles_warnings
    # if not sp.beta_significant:
    #     warnings.append("[β비유의] storage_prod 혼잡항 β 미유의로 제거됨")

    # Step 8: 출력 저장
    # save_outputs(args.output, forecasts, bands, mq, mt, sp, snpw, loocv, warnings)

    # Step 9: 그래프
    # if not args.no_plots:
    #     make_plots(actuals_df, forecasts, bands, mt, loocv, args.output)

    # Step 10: 요약 출력
    # _print_summary(forecasts, loocv, params)

    raise NotImplementedError("main.py 구현 필요")


if __name__ == '__main__':
    main()
