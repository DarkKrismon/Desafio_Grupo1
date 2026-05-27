"""
api/schemas.py
==============
Modelos Pydantic: contratos de entrada y salida de la API.

Estos schemas son el "contrato" con Full Stack.
NO los cambies sin avisar al equipo.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Literal
import re

from pydantic import BaseModel, field_validator, Field, ConfigDict


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
    payment  = "PAYMENT"
    debit    = "DEBIT"
    cash_in  = "CASH_IN"


# ============================================================
# REQUEST
# ============================================================
class Transaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(min_length=1, max_length=50, description="ID único de la transacción")
    step:           int = Field(ge=1, le=744, description="Horas transcurridas en el sistema (máx 744 = 31 días)")
    type:           TransactionType = Field(description="Tipo de movimiento financiero")
    amount:         float = Field(ge=10.0, le=1_000_000.0, description="Importe de la transacción")
    nameOrig:       str = Field(min_length=10, max_length=11, description="ID del cliente origen")
    oldbalanceOrg:  float = Field(ge=0.0, description="Saldo inicial del origen")
    newbalanceOrig: float = Field(ge=0.0, description="Saldo final del origen")
    nameDest:       str = Field(min_length=10, max_length=11, description="ID del cliente destino")
    oldbalanceDest: float = Field(ge=0.0, description="Saldo inicial del destino")
    newbalanceDest: float = Field(ge=0.0, description="Saldo final del destino")
    merchant_category: str | None = Field(default="unknown", max_length=30)
    ip_country:        str | None = Field(default="unknown", max_length=10)
    hour_of_the_day:   int | None = Field(default=None, ge=0, le=23, description="Hora del día (0-23)")

    VALID_COUNTRIES = {
        "AD","AE","AF","AG","AL","AM","AO","AR","AT","AU","AZ","BA","BB","BD",
        "BE","BF","BG","BH","BI","BJ","BN","BO","BR","BS","BT","BW","BY","BZ",
        "CA","CD","CF","CG","CH","CI","CL","CM","CN","CO","CR","CU","CV","CY",
        "CZ","DE","DJ","DK","DM","DO","DZ","EC","EE","EG","ER","ES","ET","FI",
        "FJ","FK","FM","FR","GA","GB","GD","GE","GH","GM","GN","GQ","GR","GT",
        "GW","GY","HN","HR","HT","HU","ID","IE","IL","IN","IQ","IR","IS","IT",
        "JM","JO","JP","KE","KG","KH","KI","KM","KN","KP","KR","KW","KZ","LA",
        "LB","LC","LI","LK","LR","LS","LT","LU","LV","LY","MA","MC","MD","ME",
        "MG","MH","MK","ML","MM","MN","MR","MT","MU","MV","MW","MX","MY","MZ",
        "NA","NE","NG","NI","NL","NO","NP","NR","NZ","OM","PA","PE","PG","PH",
        "PK","PL","PT","PW","PY","QA","RO","RS","RU","RW","SA","SB","SC","SD",
        "SE","SG","SI","SK","SL","SM","SN","SO","SR","SS","ST","SV","SY","SZ",
        "TD","TG","TH","TJ","TL","TM","TN","TO","TR","TT","TV","TZ","UA","UG",
        "US","UY","UZ","VA","VC","VE","VN","VU","WS","YE","ZA","ZM","ZW","UNKNOWN"
    }

    VALID_CATEGORIES = {
        "crypto", "electronics", "restaurant", "pharmacy", "grocery",
        "transport", "fuel", "financial", "unknown"
    }

    @field_validator("nameOrig", "nameDest")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        if not re.match(r"^[CM]\d{8,10}$", v):
            raise ValueError(
                f"Identificador inválido: '{v}'. Formato esperado: C o M seguido de 8 o 10 dígitos (ej. C123456789 o M987654321)"
            )
        return v

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return round(v, 2)

    @field_validator("ip_country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        if v is None:
            return "unknown"
        v_upper = v.upper()
        if v_upper not in cls.VALID_COUNTRIES:
            raise ValueError(
                f"País inválido: '{v}'. Debe ser un código ISO 3166-1 alpha-2 (ej. ES, US, NG)"
            )
        return v_upper

    @field_validator("merchant_category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v is None:
            return "unknown"
        v_lower = v.lower()
        if v_lower not in cls.VALID_CATEGORIES:
            raise ValueError(
                f"Categoría inválida: '{v}'. Categorías válidas: {', '.join(sorted(cls.VALID_CATEGORIES))}"
            )
        return v_lower

    @field_validator("nameDest")
    @classmethod
    def validate_different_accounts(cls, v: str, info) -> str:
        if "nameOrig" in info.data and v == info.data["nameOrig"]:
            raise ValueError("nameOrig y nameDest no pueden ser el mismo cliente")
        return v
    
    @field_validator("transaction_id", "merchant_category", "ip_country")
    @classmethod
    def sanitize_strings(cls, v: str) -> str:
        if v is None:
            return v
        import re
        # Eliminamos caracteres que pueden ser usados en ataques XSS
        clean = re.sub(r"[<>\"'%;()&+]", "", v)
        if clean != v:
            raise ValueError("El campo contiene caracteres no permitidos")
        return clean


class FeedbackRequest(BaseModel):
    transaction_id:    str = Field(..., example="TXN-002")
    analyst_decision:  str = Field(..., example="fraud")
    analyst_notes:     Optional[str] = Field(None, example="Confirmado por usuario")
    analyst_id:        str = Field(..., example="analyst_42")


class ExplainRequest(BaseModel):
    transaction_id: str = Field(..., example="TXN-001")


class PreviewRequest(BaseModel):
    threshold_block:  float = Field(..., ge=0, le=1, example=0.75)
    threshold_review: float = Field(..., ge=0, le=1, example=0.45)
    test_set:         str = Field(default="round_1", example="round_1")


class ChallengeRequest(BaseModel):
    transaction_id:      str = Field(..., example="TXN-002")
    fraud_probability:   float = Field(..., ge=0, le=1, example=0.54)
    risk_level:          RiskLevel = Field(..., example="medium")
    transaction_context: Transaction


# ============================================================
# RESPONSE
# ============================================================
class DecideResponse(BaseModel):
    transaction_id:    str
    decision:          Decision
    fraud_probability: float
    risk_level:        RiskLevel
    timestamp:         datetime


class QueueItem(BaseModel):
    transaction_id:    str
    amount:            float
    type:              str
    ip_country:        str
    merchant_category: str
    fraud_probability: float
    risk_level:        RiskLevel
    timestamp:         datetime


class QueueResponse(BaseModel):
    total_pending: int
    queue:         list[QueueItem]


class FeatureContribution(BaseModel):
    feature:   str
    impact:    float
    narrative: str


class ExplainResponse(BaseModel):
    transaction_id:       str
    fraud_probability:    float
    narrative:            str
    feature_contributions: list[FeatureContribution]
    counterfactual:       str


class PreviewMetrics(BaseModel):
    threshold_block:  float
    threshold_review: float
    blocked:          int
    reviewed:         int
    allowed:          int
    fraud_caught:     int
    false_positives:  int
    money_saved_eur:  float


class PreviewResponse(BaseModel):
    current_config: PreviewMetrics
    preview_config: PreviewMetrics
    delta:          dict


class ChallengeOption(BaseModel):
    action:       str
    friction:     str
    user_message: Optional[str] = None


class ChallengeResponse(BaseModel):
    transaction_id:     str
    recommended_action: str
    primary_option:     ChallengeOption
    alternative_options: list[ChallengeOption]
    reasoning:          str


class FeedbackResponse(BaseModel):
    status:         str
    case_id:        str
    transaction_id: str
    decision:       str


# ============================================================
# CLIENT PROFILE
# ============================================================
class ClientStats(BaseModel):
    total_transactions:    int = Field(..., description="Nº total de transacciones")
    total_volume:          float = Field(..., description="Suma de importes (€)")
    avg_amount:            float = Field(..., description="Importe medio (€)")
    max_amount:            float = Field(..., description="Mayor importe (€)")
    first_seen:            Optional[datetime] = Field(None, description="Prim