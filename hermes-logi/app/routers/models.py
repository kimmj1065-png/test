"""
모델 학습 및 계수 조회 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import pandas as pd
from ..database import get_db, ActualRecord, FloorConfig, DRStepConfig
from ..services.model_trainer import (
    train_movement_model,
    train_transport_count_model,
    train_transport_time_model,
    train_storage_model,
)
import joblib
from pathlib import Path
import os

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "model_store"))
router = APIRouter(prefix="/models", tags=["models"])


def _load_actuals(db: Session) -> pd.DataFrame:
    rows = db.query(ActualRecord).all()
    return pd.DataFrame([r.__dict__ for r in rows]).drop(columns=["_sa_instance_state"], errors="ignore")


def _load_floor_config(db: Session) -> pd.DataFrame:
    rows = db.query(FloorConfig).all()
    return pd.DataFrame([r.__dict__ for r in rows]).drop(columns=["_sa_instance_state"], errors="ignore")


def _load_dr_steps(db: Session) -> dict:
    rows = db.query(DRStepConfig).all()
    return {r.dr_type: r.step_count for r in rows}


@router.post("/train/all")
def train_all(db: Session = Depends(get_db)):
    """모든 모델 일괄 학습 (실적 데이터 기반)"""
    actuals = _load_actuals(db)
    if actuals.empty:
        raise HTTPException(status_code=400, detail="실적 데이터가 없습니다. 먼저 실적을 업로드하세요.")

    floor_cfg = _load_floor_config(db)
    dr_steps = _load_dr_steps(db)

    # Step 1: 생산량 → movement
    # actuals에서 movement_plan이 없으므로 movement_actual을 X/y로 자기 자신 학습은 의미 없음
    # 실무에서는 plan DB와 actual DB를 month 기준으로 join하여 사용
    # 여기서는 movement_actual을 y, movement_actual(lag) 대신 단순히 r1 학습 시연
    r1 = train_movement_model(actuals.rename(columns={"movement_actual": "movement_plan_proxy"}))

    # Step 2: movement → 반송량
    r2 = train_transport_count_model(actuals, dr_steps)

    # Step 3: 반송량 → 반송시간
    r3 = {}
    if not floor_cfg.empty:
        r3 = train_transport_time_model(actuals, floor_cfg)

    # Storage
    r4 = {}
    if "wip_plan" not in actuals.columns:
        actuals["wip_plan"] = None
    r4 = train_storage_model(actuals.rename(columns={"wip_plan": "wip_plan"}), dr_steps)

    return {
        "movement_model": {"groups_trained": len(r1)},
        "transport_count_model": {"groups_trained": len(r2)},
        "transport_time_model": {"groups_trained": len(r3)},
        "storage_model": {"groups_trained": len(r4)},
    }


@router.post("/train/movement")
def train_movement(db: Session = Depends(get_db)):
    actuals = _load_actuals(db)
    result = train_movement_model(actuals)
    return {"groups_trained": len(result), "detail": result}


@router.post("/train/transport-count")
def train_transport_count(db: Session = Depends(get_db)):
    actuals = _load_actuals(db)
    dr_steps = _load_dr_steps(db)
    result = train_transport_count_model(actuals, dr_steps)
    return {"groups_trained": len(result), "detail": result}


@router.post("/train/transport-time")
def train_transport_time(db: Session = Depends(get_db)):
    actuals = _load_actuals(db)
    floor_cfg = _load_floor_config(db)
    result = train_transport_time_model(actuals, floor_cfg)
    return {"groups_trained": len(result), "detail": result}


@router.post("/train/storage")
def train_storage(db: Session = Depends(get_db)):
    actuals = _load_actuals(db)
    dr_steps = _load_dr_steps(db)
    result = train_storage_model(actuals, dr_steps)
    return {"groups_trained": len(result)}


@router.get("/coefficients/movement")
def get_movement_coefficients():
    path = MODEL_DIR / "movement" / "coefficients.joblib"
    if not path.exists():
        raise HTTPException(status_code=404, detail="모델 미학습 상태입니다.")
    data = joblib.load(path)
    return {str(k): v for k, v in data.items()}


@router.get("/coefficients/transport-time")
def get_transport_time_coefficients():
    path = MODEL_DIR / "transport_time" / "coefficients.joblib"
    if not path.exists():
        raise HTTPException(status_code=404, detail="모델 미학습 상태입니다.")
    data = joblib.load(path)
    return {str(k): v for k, v in data.items()}
