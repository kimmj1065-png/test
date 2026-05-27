"""
Capa 산출 API
- OHT 과부족: (site, floor, 월) 단위
- Storage 과부족: (site, line, floor, 월) 단위
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import pandas as pd
from ..database import get_db, PlanRecord, ActualRecord, FloorConfig, StorageConfig, DRStepConfig
from ..services.oht_calculator import calculate_oht_demand, aggregate_oht_by_floor, line_contribution
from ..services.storage_calculator import calculate_storage_demand

router = APIRouter(prefix="/capacity", tags=["capacity"])


def _df_from_query(rows, exclude=("_sa_instance_state",)):
    return pd.DataFrame(
        [{k: v for k, v in r.__dict__.items() if k not in exclude} for r in rows]
    )


def _load_plan(db, site=None, from_month=None, to_month=None):
    q = db.query(PlanRecord)
    if site:
        q = q.filter(PlanRecord.site == site)
    if from_month:
        q = q.filter(PlanRecord.plan_month >= from_month)
    if to_month:
        q = q.filter(PlanRecord.plan_month <= to_month)
    return _df_from_query(q.all())


@router.get("/oht")
def oht_capacity(
    site: str | None = None,
    from_month: str | None = Query(None, example="2026-01"),
    to_month: str | None = Query(None, example="2026-12"),
    db: Session = Depends(get_db),
):
    """OHT 과부족 산출. floor 단위 집계 결과 반환."""
    plan_df = _load_plan(db, site, from_month, to_month)
    if plan_df.empty:
        raise HTTPException(status_code=400, detail="해당 조건의 계획 데이터가 없습니다.")

    floor_cfg = _df_from_query(db.query(FloorConfig).all())
    dr_steps = {r.dr_type: r.step_count for r in db.query(DRStepConfig).all()}

    if floor_cfg.empty:
        raise HTTPException(status_code=400, detail="OHT 기준 데이터(Floor Config)가 없습니다.")

    demand = calculate_oht_demand(plan_df, floor_cfg, dr_steps)
    floor_result = aggregate_oht_by_floor(demand, floor_cfg)
    line_result = line_contribution(demand)

    return {
        "floor_summary": floor_result.to_dict(orient="records"),
        "line_detail": line_result.to_dict(orient="records"),
    }


@router.get("/storage")
def storage_capacity(
    site: str | None = None,
    from_month: str | None = Query(None, example="2026-01"),
    to_month: str | None = Query(None, example="2026-12"),
    db: Session = Depends(get_db),
):
    """Storage 과부족 산출. (site, line, floor) 단위 결과 반환."""
    plan_df = _load_plan(db, site, from_month, to_month)
    if plan_df.empty:
        raise HTTPException(status_code=400, detail="해당 조건의 계획 데이터가 없습니다.")

    actuals_df = _df_from_query(db.query(ActualRecord).all())
    storage_cfg = _df_from_query(db.query(StorageConfig).all())
    dr_steps = {r.dr_type: r.step_count for r in db.query(DRStepConfig).all()}

    result = calculate_storage_demand(plan_df, actuals_df, storage_cfg, dr_steps)
    return result.to_dict(orient="records")


@router.get("/oht/line-contribution")
def oht_line_contribution(
    site: str | None = None,
    plan_month: str | None = Query(None, example="2026-06"),
    db: Session = Depends(get_db),
):
    """특정 월, floor 내 라인별 OHT 수요 기여 비중 (파이차트용)."""
    plan_df = _load_plan(db, site, plan_month, plan_month)
    if plan_df.empty:
        raise HTTPException(status_code=400, detail="데이터 없음")

    floor_cfg = _df_from_query(db.query(FloorConfig).all())
    dr_steps = {r.dr_type: r.step_count for r in db.query(DRStepConfig).all()}

    demand = calculate_oht_demand(plan_df, floor_cfg, dr_steps)
    contrib = line_contribution(demand)
    return contrib[["site", "floor", "line", "plan_month", "required_oht_hours", "line_share"]].to_dict(
        orient="records"
    )
