"""
src/storage.py
==============
Almacenamiento en memoria.

HOY: listas en memoria del proceso (se pierden al reiniciar).
MAÑANA: sustituir por consultas a PostgreSQL / SQLite / MongoDB
        sin tocar la API.

Las funciones publicas son la interfaz que usan los endpoints.
"""

from datetime import datetime
from typing import Optional

from api.schemas import QueueItem, RiskLevel


# ============================================================
# ESTADO EN MEMORIA
# ============================================================
_pending_queue: list[QueueItem] = []
_feedback_store: list[dict] = []


# ============================================================
# COLA DE REVISION
# ============================================================
def add_to_queue(item: QueueItem) -> None:
    """Añade un QueueItem a la cola de revisión."""
    _pending_queue.append(item)


def get_queue(
    limit: int = 50,
    offset: int = 0,
    risk_level: Optional[RiskLevel] = None,
    types: Optional[list[str]] = None,
) -> tuple[list[QueueItem], int]:
    """Devuelve una página de la cola y el total de casos que cumplen el filtro.

    Args:
        limit: máx items a devolver (1-200, validado en el endpoint).
        offset: offset para paginar.
        risk_level: si se pasa, filtra por nivel ('low', 'medium', 'high').
        types: si se pasa, filtra por tipo de transacción.
               Ej: ['TRANSFER', 'CASH_OUT'].

    Returns:
        (items_de_la_pagina, total_que_cumple_filtro)
    """
    filtered = _pending_queue

    if risk_level is not None:
        # risk_level puede llegar como Enum o como string, normalizamos
        rl_value = risk_level.value if hasattr(risk_level, "value") else risk_level
        filtered = [item for item in filtered if item.risk_level == rl_value or item.risk_level == risk_level]

    if types is not None and len(types) > 0:
        types_upper = {t.upper() for t in types}
        filtered = [item for item in filtered if (item.type or "").upper() in types_upper]

    total = len(filtered)

    # Ordenar por probabilidad descendente (los casos más sospechosos primero)
    filtered = sorted(filtered, key=lambda x: x.fraud_probability, reverse=True)

    # Paginar
    page = filtered[offset : offset + limit]
    return page, total


def queue_size(risk_level: Optional[RiskLevel] = None) -> int:
    """Tamaño actual de la cola, opcionalmente filtrado por nivel de riesgo."""
    if risk_level is None:
        return len(_pending_queue)
    rl_value = risk_level.value if hasattr(risk_level, "value") else risk_level
    return sum(1 for item in _pending_queue if item.risk_level == rl_value or item.risk_level == risk_level)


def find_in_queue(transaction_id: str) -> Optional[QueueItem]:
    """Busca un caso en la cola por transaction_id."""
    for item in _pending_queue:
        if item.transaction_id == transaction_id:
            return item
    return None


def remove_from_queue(transaction_id: str) -> bool:
    """Quita un caso de la cola. Devuelve True si se encontró y eliminó."""
    global _pending_queue
    before = len(_pending_queue)
    _pending_queue = [item for item in _pending_queue if item.transaction_id != transaction_id]
    return len(_pending_queue) < before


# ============================================================
# FEEDBACK DEL ANALISTA
# ============================================================
def store_feedback(
    case_id: str,
    transaction_id: str,
    analyst_decision: str,
    analyst_notes: Optional[str],
    analyst_id: str,
) -> None:
    _feedback_store.append({
        "case_id": case_id,
        "transaction_id": transaction_id,
        "analyst_decision": analyst_decision,
        "analyst_notes": analyst_notes,
        "analyst_id": analyst_id,
        "timestamp": datetime.utcnow().isoformat(),
    })


def get_all_feedback() -> list[dict]:
    return list(_feedback_store)