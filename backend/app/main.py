"""Punto de entrada de la API de Crisantemo (FastAPI)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_analysis import router as analysis_router
from app.api.routes_health import router as health_router
from app.config import get_settings
from app.scoring.model_loader import load_model_bundle


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.model_bundle = load_model_bundle(settings.model_path, settings.feature_schema_path)
    yield


app = FastAPI(title="Crisantemo API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(analysis_router)
