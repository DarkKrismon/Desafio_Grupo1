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

from pydantic import BaseModel, Field, field_validator
import re


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
    """Schema acordado con Full Stack (formato PaySim-like)."""
    transaction_id: str = Field(..., example="TXN-001")
    nameOrig: str = Field(..., example="C123456789")
    amount: float = Field(..., gt=0, example=1500.00)
    type: TransactionType = Field(..., example="TRANSFER")
    oldbalanceOrg: float = Field(..., ge=0, example=2000.00)
    newbalanceOrig: float = Field(..., ge=0, example=500.00)
    oldbalanceDest: float = Field(..., ge=0, example=0.00)
    newbalanceDest: float = Field(..., ge=0, example=1500.00)
    ip_country: str = Field(..., example="KH")
    merchant_category: str = Field(..., example="crypto")

    @field_validator('nameOrig')
    @classmethod
    def validate_user_id(cls, v):
        pattern = r'^[Cc]\d{9}$'
        if not re.match(pattern, v):
            raise ValueError('nameOrig inválido. Formato: C + 9 dígitos (ej: C123456789)')
        return v.upper()


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
