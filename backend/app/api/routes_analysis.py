"""POST /api/v1/analyze. Ver docs/API.md para el contrato completo."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from acoustic_features import InsufficientVoiceError, extract_features

from app.audio.decode import InvalidAudioError, decode_upload
from app.schemas import AnalyzeResponse, FeaturesOut, FeedbackOut, MetaOut
from app.scoring.feedback import build_feedback
from app.scoring.predictor import predict

router = APIRouter()


@router.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze(request: Request, file: UploadFile = File(...)) -> AnalyzeResponse:
    try:
        samples, sample_rate = await decode_upload(file)
    except InvalidAudioError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        features = extract_features(samples, sample_rate)
    except InsufficientVoiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    bundle = request.app.state.model_bundle
    prediction = predict(bundle, features)
    feedback = build_feedback(prediction.score, features)

    feature_values = features.as_dict()
    feature_values.pop("voiced_seconds")
    feature_values.pop("duration_seconds")

    return AnalyzeResponse(
        score=prediction.score,
        confidence=prediction.confidence,
        features=FeaturesOut(**feature_values),
        feedback=FeedbackOut(**feedback),
        meta=MetaOut(
            voiced_seconds=features.voiced_seconds,
            duration_seconds=features.duration_seconds,
        ),
    )
