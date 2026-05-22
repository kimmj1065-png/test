from fastapi import FastAPI
from app.routers import auth, personas

app = FastAPI(title="Persona API", version="1.0.0")

app.include_router(auth.router)
app.include_router(personas.router)


@app.get("/health")
def health():
    return {"status": "ok"}
