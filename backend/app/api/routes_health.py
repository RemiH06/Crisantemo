"""GET /health y GET /api/v1/model-info."""

from __future__ import annotations

from fastapi import APIRouter, Request

from acoustic_features import FEATURE_NAMES

from app.schemas import ModelInfo

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/api/v1/model-info", response_model=ModelInfo)
def model_info(request: Request) -> ModelInfo:
    bundle = request.app.state.model_bundle
    return ModelInfo(
        schema_version=bundle.schema_version,
        model_version=bundle.model_version,
        feature_names=FEATURE_NAMES,
    )
