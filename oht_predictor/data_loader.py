"""
실적 데이터 로더
=================
★ 실적(actuals) 데이터를 교체할 때는 이 파일만 수정합니다. ★

교체 방법:
  1. [간단] 아래 ACTUALS_PATH 경로의 CSV 파일을 덮어쓰기
  2. [CLI]  python main.py --actuals /your/path/actuals.csv 옵션 사용
  3. [고급] load_actuals() 함수 내부를 DB 조회 / API 호출로 교체

필수 컬럼 (actuals.csv)
─────────────────────────────────────────────────────────────────────
  month        YYYY-MM    연월 인덱스 (오름차순 정렬됨)
  prod                    생산량 (월합계, 웨이퍼 또는 로트 등 단위 통일)
  wip                     재공 (월말 기준)
  lot_size                평균 lot size
  move_qty      회/hr     OHT 시간당 반송량
  move_time     초         평균 반송시간
  load_dist     mm        평균 load 반송거리
  oht_count     대         OHT 투입 대수
  storage_prod  캐리어     생산 FOUP 저장량
  storage_npw   캐리어     비생산(NPW/Empty) FOUP 저장량

필수 컬럼 (plan.csv)
─────────────────────────────────────────────────────────────────────
  month        YYYY-MM    연월
  prod_plan               생산계획 (actuals.prod 와 동일 단위)
  lot_size_plan           계획 lot size
  wip_plan                예상 재공
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

_BASE         = Path(__file__).parent / "sample_data"
ACTUALS_PATH  = _BASE / "actuals.csv"
PLAN_PATH     = _BASE / "plan.csv"

_ACTUALS_COLS = {
    "month", "prod", "wip", "lot_size",
    "move_qty", "move_time", "load_dist",
    "oht_count", "storage_prod", "storage_npw",
}
_PLAN_COLS = {"month", "prod_plan", "lot_size_plan", "wip_plan"}


def load_actuals(path: str | Path = ACTUALS_PATH) -> pd.DataFrame:
    """
    실적(actuals) CSV 로드 → 정렬된 DataFrame 반환.

    이 함수를 수정해 DB / API / 엑셀 등 다른 소스로 교체하세요.
    반환 형식만 지키면(위 컬럼 보유 + month 오름차순) 하위 모듈은 그대로 작동합니다.
    """
    df = pd.read_csv(path)
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m")
    df = df.sort_values("month").reset_index(drop=True)
    _validate(df, _ACTUALS_COLS, "actuals")
    return df


def load_plan(path: str | Path = PLAN_PATH) -> pd.DataFrame:
    """계획(plan) CSV 로드 → 정렬된 DataFrame 반환."""
    df = pd.read_csv(path)
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m")
    df = df.sort_values("month").reset_index(drop=True)
    _validate(df, _PLAN_COLS, "plan")
    return df


def _validate(df: pd.DataFrame, required: set, name: str) -> None:
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"[{name}] 누락 컬럼: {sorted(missing)}")
    if df.empty:
        raise ValueError(f"[{name}] 데이터가 비어 있습니다.")
