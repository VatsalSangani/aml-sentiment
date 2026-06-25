"""
AML Sentinel — FastAPI entry point
XGBoost + LightGBM Ensemble + GPT-4o-mini XAI
"""

import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from config import API_HOST, API_PORT
from db import monitor
from security import limiter
from services.model_service import model_service
from routes import analyze, health, monitoring, reports, stats, xai


@asynccontextmanager
async def lifespan(app: FastAPI):
    monitor.init_db()
    model_service.load()
    yield


app = FastAPI(
    title="AML Sentinel",
    description="XGBoost + LightGBM Ensemble + GPT-4o-mini XAI",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://portfolio.vatsalsangani.in",
        "http://localhost:3000",   # local dev only
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(monitoring.router)
app.include_router(reports.router)
app.include_router(stats.router)
app.include_router(xai.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=False)
