"""
Hermes-Logi FastAPI 백엔드
실행: uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .routers import actuals, planning, reference, models, capacity

app = FastAPI(
    title="Hermes-Logi Capa API",
    description="반도체 물류 OHT·Storage 중장기 Capa 분석 시스템",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(actuals.router)
app.include_router(planning.router)
app.include_router(reference.router)
app.include_router(models.router)
app.include_router(capacity.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "hermes-logi"}
