from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, PlanRecord
from ..services.excel_parser import parse_plan_excel, generate_sample_plan_excel
from fastapi.responses import Response

router = APIRouter(prefix="/planning", tags=["planning"])


@router.post("/upload")
async def upload_plan(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        df = parse_plan_excel(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    inserted = 0
    for _, row in df.iterrows():
        record = PlanRecord(
            site=row["site"],
            line=row["line"],
            floor=row["floor"],
            dr_type=row["dr_type"],
            plan_month=row["plan_month"],
            movement_plan=row.get("movement_plan"),
            wip_plan=row.get("wip_plan"),
            lot_size=row.get("lot_size"),
            npw_plan=row.get("npw_plan"),
            input_plan=row.get("input_plan"),  # history only
        )
        db.add(record)
        inserted += 1
    db.commit()
    return {"inserted": inserted}


@router.get("/sample")
def download_sample():
    content = generate_sample_plan_excel()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=sample_planning.xlsx"},
    )


@router.get("/list")
def list_plans(site: str | None = None, db: Session = Depends(get_db)):
    q = db.query(PlanRecord)
    if site:
        q = q.filter(PlanRecord.site == site)
    records = q.order_by(PlanRecord.plan_month).all()
    return [
        {
            "id": r.id, "site": r.site, "line": r.line, "floor": r.floor,
            "dr_type": r.dr_type, "plan_month": r.plan_month,
            "movement_plan": r.movement_plan, "wip_plan": r.wip_plan,
            "lot_size": r.lot_size, "npw_plan": r.npw_plan,
        }
        for r in records
    ]
