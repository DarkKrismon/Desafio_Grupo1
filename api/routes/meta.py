"""
api/routes/meta.py
==================
Endpoints meta: health, ready, info del sistema.
"""

from fastapi import APIRouter

from src.storage import queue_size

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
        "model_loaded": False,  # cambiar a True cuando se enchufe el modelo real
        "model_version": "mock-v0.1",
        "queue_size": queue_size(),
    }
