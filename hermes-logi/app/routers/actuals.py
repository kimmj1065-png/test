from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, ActualRecord
from ..services.excel_parser import parse_actual_excel, generate_sample_actual_excel
from fastapi.responses import Response

router = APIRouter(prefix="/actuals", tags=["actuals"])


@router.post("/upload")
async def upload_actuals(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        df = parse_actual_excel(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    inserted = 0
    for _, row in df.iterrows():
        record = ActualRecord(
            site=row["site"],
            line=row["line"],
            floor=row["floor"],
            dr_type=row["dr_type"],
            actual_month=row["actual_month"],
            movement_actual=row.get("movement_actual"),
            transport_count_actual=row.get("transport_count_actual"),
            transport_time_actual=row.get("transport_time_actual"),
            storage_product_actual=row.get("storage_product_actual"),
            storage_total_actual=row.get("storage_total_actual"),
            input_plan=row.get("input_plan"),
        )
        db.add(record)
        inserted += 1
    db.commit()
    return {"inserted": inserted}


@router.get("/sample")
def download_sample():
    content = generate_sample_actual_excel()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=sample_actuals.xlsx"},
    )


@router.get("/list")
def list_actuals(site: str | None = None, db: Session = Depends(get_db)):
    q = db.query(ActualRecord)
    if site:
        q = q.filter(ActualRecord.site == site)
    records = q.order_by(ActualRecord.actual_month).all()
    return [
        {
            "id": r.id, "site": r.site, "line": r.line, "floor": r.floor,
            "dr_type": r.dr_type, "actual_month": r.actual_month,
            "movement_actual": r.movement_actual,
            "transport_count_actual": r.transport_count_actual,
            "transport_time_actual": r.transport_time_actual,
            "storage_product_actual": r.storage_product_actual,
            "storage_total_actual": r.storage_total_actual,
        }
        for r in records
    ]
