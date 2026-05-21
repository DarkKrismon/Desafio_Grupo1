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
# COLA DE CASOS PENDIENTES
# ============================================================
def add_to_queue(item: QueueItem) -> None:
    """Anade un caso a la cola pendiente de revision."""
    _pending_queue.append(item)


def get_queue(
    limit: int = 50,
    risk_level: Optional[RiskLevel] = None,
) -> list[QueueItem]:
    """Devuelve la cola filtrada."""
    items = _pending_queue
    if risk_level:
        items = [q for q in items if q.risk_level == risk_level]
    return items[:limit]


def queue_size(risk_level: Optional[RiskLevel] = None) -> int:
    if risk_level:
        return sum(1 for q in _pending_queue if q.risk_level == risk_level)
    return len(_pending_queue)


def find_in_queue(transaction_id: str) -> Optional[QueueItem]:
    return next(
        (q for q in _pending_queue if q.transaction_id == transaction_id),
        None,
    )


def remove_from_queue(transaction_id: str) -> None:
    global _pending_queue
    _pending_queue = [
        q for q in _pending_queue if q.transaction_id != transaction_id
    ]


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
