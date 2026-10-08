import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.logs import router as logs_router

app = FastAPI(
    title="TraceFix Log Analyzer",
    version="1.0.0",
    description="Analyzes uploaded production logs against a source repository.",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

app.include_router(logs_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
