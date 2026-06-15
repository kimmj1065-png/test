"""
OHT/Storage 예측 모델 — 진입점
================================
사용법:
    python main.py                                   # 기본 샘플 데이터 사용
    python main.py --actuals my_actuals.csv          # 실적 파일 지정
    python main.py --actuals a.csv --plan p.csv      # 실적 + 계획 모두 지정
"""
import argparse
import sys
from pathlib import Path

# oht_predictor 디렉터리를 sys.path에 추가 (어느 위치에서 실행해도 동작)
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import load_actuals, load_plan
from model import fit
from predictor import predict
from reporter import save_all


def main() -> None:
    parser = argparse.ArgumentParser(description="OHT/Storage 예측 모델")
    parser.add_argument("--actuals", default=None,
                        help="실적 CSV 경로 (기본: sample_data/actuals.csv)")
    parser.add_argument("--plan", default=None,
                        help="계획 CSV 경로 (기본: sample_data/plan.csv)")
    args = parser.parse_args()

    print("=" * 50)
    print("  OHT/Storage 예측 모델  v2")
    print("=" * 50)

    print("\n[1/4] 데이터 로드")
    actuals  = load_actuals(args.actuals) if args.actuals else load_actuals()
    plan_df  = load_plan(args.plan)       if args.plan    else load_plan()
    print(f"  실적: {len(actuals)}행 "
          f"({actuals['month'].dt.strftime('%Y-%m').iloc[0]} ~ "
          f"{actuals['month'].dt.strftime('%Y-%m').iloc[-1]})")
    print(f"  계획: {len(plan_df)}행 "
          f"({plan_df['month'].dt.strftime('%Y-%m').iloc[0]} ~ "
          f"{plan_df['month'].dt.strftime('%Y-%m').iloc[-1]})")

    print("\n[2/4] 모델 학습")
    params, metrics = fit(actuals)
    print(f"  k={params.k:.4f}, T0_ref={params.T0_ref:.1f}초, "
          f"OHT_FIXED={params.OHT_FIXED}대")
    print(f"  move_time R²={metrics.move_time_r2:.4f}, "
          f"MAPE(CV)={metrics.move_time_mape_cv*100:.2f}%")

    print("\n[3/4] 예측")
    forecast = predict(plan_df, params)
    warn_cols = ["포화경보", "부하율경보", "외삽여부", "점유경보"]
    n_warn = forecast[warn_cols].any(axis=1).sum()
    print(f"  예측 월수: {len(forecast)} | 경보 발생 월: {n_warn}")

    print("\n[4/4] 산출물 저장")
    save_all(actuals, forecast, params, metrics)


if __name__ == "__main__":
    main()
