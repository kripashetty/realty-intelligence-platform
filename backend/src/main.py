import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import router as api_v1_router

app = FastAPI(
    title="Realty Intelligence Platform",
    version="1.0.0",
    description="Rental market intelligence API — US1: pricing recommendations for Berlin landlords",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

_allowed_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok"}
