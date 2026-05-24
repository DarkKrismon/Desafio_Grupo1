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
    test_set: Literal["round_1", "round_2"] = Field(
        default="round_1",
        description="Dataset sobre el que evaluar: 'round_1' (línea base) o 'round_2' (adversario adaptado)",
    )
    compare: bool = Field(
        default=False,
        description="Si es true, devuelve además un bloque 'comparison' con métricas R1 vs R2 en la misma respuesta. Ideal para el dashboard de benchmark.",
    )


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


class QueueItem(BaseModel):
    transaction_id: str
    amount: float
    type: str
    ip_country: str
    merchant_category: str
    fraud_probability: float
    risk_level: RiskLevel
    timestamp: datetime


class QueueResponse(BaseModel):
    total_pending: int
    queue: list[QueueItem]


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


class RoundComparison(BaseModel):
    """Métricas de detección de una ronda para el benchmark R1 vs R2."""
    round_id: Literal["round_1", "round_2"]
    total_transactions: int
    fraud_in_dataset: int
    fraud_caught: int
    fraud_missed: int
    recall: float
    precision: float
    f1_score: float
    money_saved_eur: float
    avg_fraud_probability: float


class PreviewResponse(BaseModel):
    current_config: PreviewMetrics
    preview_config: PreviewMetrics
    delta: dict
    comparison: Optional[dict] = Field(
        default=None,
        description="Sólo presente si la petición incluyó compare=true. Contiene métricas de round_1, round_2 y bloque 'improvement' con los deltas y una interpretación textual.",
    )


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