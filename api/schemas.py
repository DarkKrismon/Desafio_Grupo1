"""
api/schemas.py
==============
Modelos Pydantic: contratos de entrada y salida de la API.

Estos schemas son el "contrato" con Full Stack.
NO los cambies sin avisar al equipo.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator, Field, ConfigDict
from typing import Literal


TransactionType = Literal["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]

# ============================================================
# ENUMS
# ============================================================
class Decision(str, Enum):
    allow = "allow"
    review = "review"
    block = "block"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TransactionType(str, Enum):
    transfer = "TRANSFER"
    cash_out = "CASH_OUT"
    payment = "PAYMENT"
    debit = "DEBIT"
    cash_in = "CASH_IN"


# ============================================================
# REQUEST
# ============================================================
class Transaction(BaseModel):
    # 1. Prohibimos estrictamente campos no documentados
    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(min_length=1, max_length=50, description="ID único de la transacción")

    # 2. Tipado estricto y límites matemáticos
    step: int = Field(ge=1, description="Horas transcurridas en el sistema")
    type: TransactionType = Field(description="Tipo de movimiento financiero")
    
    # Prevenimos montos negativos y números infinitamente grandes
    amount: float = Field(ge=0.0, le=1_000_000_000.0, description="Importe de la transacción")
    
    nameOrig: str = Field(min_length=1, max_length=50, description="ID del cliente origen")
    
    oldbalanceOrg: float = Field(ge=0.0, description="Saldo inicial del origen")
    newbalanceOrig: float = Field(ge=0.0, description="Saldo final del origen")
    
    nameDest: str = Field(min_length=1, max_length=50, description="ID del cliente destino")
    
    oldbalanceDest: float = Field(ge=0.0, description="Saldo inicial del destino")
    newbalanceDest: float = Field(ge=0.0, description="Saldo final del destino")
    
    # Validamos que no nos pasen categorías o países absurdamente largos
    merchant_category: str | None = Field(default="unknown", max_length=30)
    ip_country: str | None = Field(default="unknown", max_length=10)


class FeedbackRequest(BaseModel):
    transaction_id: str = Field(..., example="TXN-002")
    analyst_decision: str = Field(..., example="fraud")
    analyst_notes: Optional[str] = Field(None, example="Confirmado por usuario")
    analyst_id: str = Field(..., example="analyst_42")


class ExplainRequest(BaseModel):
    transaction_id: str = Field(..., example="TXN-001")


class PreviewRequest(BaseModel):
    threshold_block: float = Field(..., ge=0, le=1, example=0.60)
    threshold_review: float = Field(..., ge=0, le=1, example=0.40)
    test_set: str = Field(default="round_1", example="round_1")


class ChallengeRequest(BaseModel):
    transaction_id: str = Field(..., example="TXN-002")
    fraud_probability: float = Field(..., ge=0, le=1, example=0.54)
    risk_level: RiskLevel = Field(..., example="medium")
    transaction_context: Transaction


# ============================================================
# RESPONSE
# ============================================================
class DecideResponse(BaseModel):
    transaction_id: str
    decision: Decision
    fraud_probability: float
    risk_level: RiskLevel
    timestamp: datetime


# ============================================================
# QueueItem: AMPLIADO con los campos crudos de la transacción
# ============================================================
class QueueItem(BaseModel):
    """Caso de la cola de revisión del analista.

    Incluye los campos derivados (score, risk_level) y los crudos de la
    transacción para que el panel de detalle del analista tenga toda la
    información sin tener que llamar a otro endpoint.
    """

    # --- Identificación y score (ya existentes) ---
    transaction_id: str
    amount: float
    type: str
    ip_country: Optional[str] = None
    merchant_category: Optional[str] = None
    fraud_probability: float
    risk_level: Literal["low", "medium", "high"]
    timestamp: Optional[datetime] = None

    # --- NUEVOS: campos crudos de la transacción para el panel del analista ---
    # Opcionales para no romper compatibilidad si alguna transacción no los trae.
    # En la práctica, todas las transacciones procesadas vía /decide los traerán.
    step: Optional[int] = Field(None, description="Paso temporal del dataset PaySim")
    nameOrig: Optional[str] = Field(None, description="Cuenta de origen")
    nameDest: Optional[str] = Field(None, description="Cuenta de destino")
    oldbalanceOrg: Optional[float] = Field(None, description="Saldo origen antes de la transacción")
    newbalanceOrig: Optional[float] = Field(None, description="Saldo origen después de la transacción")
    oldbalanceDest: Optional[float] = Field(None, description="Saldo destino antes de la transacción")
    newbalanceDest: Optional[float] = Field(None, description="Saldo destino después de la transacción")


# ============================================================
# QueueResponse: AMPLIADO con paginación
# ============================================================
class QueueResponse(BaseModel):
    """Respuesta paginada de la cola de revisión.

    Mantiene 'queue' como nombre del array (decisión acordada con Full Stack,
    NO cambiar a 'items') y añade campos de paginación.

    'total_pending' se mantiene por compatibilidad con la documentación previa
    y representa el total de casos pendientes en la cola (mismo valor que 'total').
    """

    queue: list[QueueItem]
    total: int = Field(..., description="Nº total de casos que cumplen el filtro (no solo los devueltos en esta página)")
    limit: int = Field(..., description="Nº máximo de items en esta respuesta")
    offset: int = Field(..., description="Offset aplicado")
    total_pending: int = Field(..., description="Alias de 'total' por compatibilidad con docs previas")


class FeatureContribution(BaseModel):
    feature: str
    impact: float
    narrative: str


class ExplainResponse(BaseModel):
    transaction_id: str
    fraud_probability: float
    narrative: str
    feature_contributions: list[FeatureContribution]
    counterfactual: str


class PreviewMetrics(BaseModel):
    threshold_block: float
    threshold_review: float
    blocked: int
    reviewed: int
    allowed: int
    fraud_caught: int
    false_positives: int
    money_saved_eur: float


class PreviewResponse(BaseModel):
    current_config: PreviewMetrics
    preview_config: PreviewMetrics
    delta: dict


class ChallengeOption(BaseModel):
    action: str
    friction: str
    user_message: Optional[str] = None


class ChallengeResponse(BaseModel):
    transaction_id: str
    recommended_action: str
    primary_option: ChallengeOption
    alternative_options: list[ChallengeOption]
    reasoning: str


class FeedbackResponse(BaseModel):
    status: str
    case_id: str
    transaction_id: str
    decision: str

# ============================================================
# CLIENT PROFILE
# ============================================================
class TransactionSummary(BaseModel):
    transaction_id: str
    amount: float
    type: str
    merchant_category: str
    ip_country: str
    fraud_probability: float
    decision: Decision
    timestamp: datetime

class ClientProfile(BaseModel):
    nameOrig: str
    total_transactions: int
    total_amount_eur: float
    fraud_flags: int
    first_seen: datetime
    last_seen: datetime
    risk_profile: RiskLevel
    recent_transactions: list[TransactionSummary]