"""
api/routes/meta.py
==================
Endpoints meta: health, ready, info del sistema.
"""

from fastapi import APIRouter

from src.storage import queue_size
from src.scoring import pipeline

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health():
    """Healthcheck basico."""
    return {"status": "ok", "service": "sentinel-api"}


@router.get("/ready")
async def ready():
    """Readiness: confirma estado del modelo y servicios."""
    return {
        "status": "ready",
        "model_loaded": pipeline is not None,
        "model_version": "xgb-v1.0",
        "queue_size": queue_size(),
    }