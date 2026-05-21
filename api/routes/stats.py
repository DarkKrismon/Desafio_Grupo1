"""
api/routes/stats.py
===================
Endpoint que expone estadisticas del dataset.

Util para que Full Stack muestre en el dashboard:
  - Volumen total procesado
  - Tasa global de fraude
  - Top paises y categorias mas peligrosas
"""

from fastapi import APIRouter

from src.data_loader import get_summary_for_api

router = APIRouter(prefix="/data", tags=["data"])


@router.get(
    "/stats",
    summary="Estadisticas globales del dataset",
)
async def data_stats():
    """
    Devuelve un resumen del dataset historico:
      - total de transacciones analizadas
      - tasa global de fraude
      - top paises mas peligrosos
      - top categorias mas peligrosas
      - estadisticas de monto
    """
    return get_summary_for_api()
