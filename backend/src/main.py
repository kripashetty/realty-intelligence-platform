import os

from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler as _default_http_handler
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.v1 import router as api_v1_router

app = FastAPI(
    title="Realty Intelligence Platform",
    version="1.0.0",
    description="Rental market intelligence API — US1: pricing recommendations",
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

@app.exception_handler(HTTPException)
async def _http_exception_handler(request, exc: HTTPException):
    """Return dict details at root level instead of wrapping under 'detail'."""
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            headers=dict(exc.headers or {}),
        )
    return await _default_http_handler(request, exc)


app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok"}
