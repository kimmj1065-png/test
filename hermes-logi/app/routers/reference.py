"""
기준 데이터 관리 API
- OHT 대수: (site, floor) 단위
- Storage 용량: (site, line, floor) 단위
- DR별 공정 step 수
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db, FloorConfig, StorageConfig, DRStepConfig

router = APIRouter(prefix="/reference", tags=["reference"])


# ── OHT 기준 데이터 ──────────────────────────────────────

class FloorConfigIn(BaseModel):
    site: str
    floor: str
    line: str
    oht_count: int
    oht_monthly_hours: float  # 대당 월 가동시간 (예: 720)


@router.post("/floor-config")
def upsert_floor_config(body: FloorConfigIn, db: Session = Depends(get_db)):
    existing = (
        db.query(FloorConfig)
        .filter_by(site=body.site, floor=body.floor, line=body.line)
        .first()
    )
    if existing:
        existing.oht_count = body.oht_count
        existing.oht_monthly_hours = body.oht_monthly_hours
    else:
        db.add(FloorConfig(**body.model_dump()))
    db.commit()
    return {"status": "ok"}


@router.get("/floor-config")
def get_floor_config(site: str | None = None, db: Session = Depends(get_db)):
    q = db.query(FloorConfig)
    if site:
        q = q.filter_by(site=site)
    rows = q.all()
    return [
        {
            "site": r.site, "floor": r.floor, "line": r.line,
            "oht_count": r.oht_count, "oht_monthly_hours": r.oht_monthly_hours,
        }
        for r in rows
    ]


@router.delete("/floor-config/{config_id}")
def delete_floor_config(config_id: int, db: Session = Depends(get_db)):
    row = db.query(FloorConfig).filter_by(id=config_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"status": "deleted"}


# ── Storage 기준 데이터 ──────────────────────────────────

class StorageConfigIn(BaseModel):
    site: str
    line: str
    floor: str
    storage_capacity: int  # FOUP 포트 수


@router.post("/storage-config")
def upsert_storage_config(body: StorageConfigIn, db: Session = Depends(get_db)):
    existing = (
        db.query(StorageConfig)
        .filter_by(site=body.site, line=body.line, floor=body.floor)
        .first()
    )
    if existing:
        existing.storage_capacity = body.storage_capacity
    else:
        db.add(StorageConfig(**body.model_dump()))
    db.commit()
    return {"status": "ok"}


@router.get("/storage-config")
def get_storage_config(site: str | None = None, db: Session = Depends(get_db)):
    q = db.query(StorageConfig)
    if site:
        q = q.filter_by(site=site)
    return [
        {"site": r.site, "line": r.line, "floor": r.floor, "storage_capacity": r.storage_capacity}
        for r in q.all()
    ]


# ── DR Step 기준 데이터 ──────────────────────────────────

class DRStepIn(BaseModel):
    dr_type: str
    step_count: int


@router.post("/dr-steps")
def upsert_dr_step(body: DRStepIn, db: Session = Depends(get_db)):
    existing = db.query(DRStepConfig).filter_by(dr_type=body.dr_type).first()
    if existing:
        existing.step_count = body.step_count
    else:
        db.add(DRStepConfig(**body.model_dump()))
    db.commit()
    return {"status": "ok"}


@router.get("/dr-steps")
def get_dr_steps(db: Session = Depends(get_db)):
    return [
        {"dr_type": r.dr_type, "step_count": r.step_count}
        for r in db.query(DRStepConfig).all()
    ]
