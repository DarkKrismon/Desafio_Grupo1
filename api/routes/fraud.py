"""
api/routes/fraud.py
===================
Endpoints de producto (lo que NovaPay integraria):

  POST   /fraud/decide            -> decision en tiempo real
  GET    /fraud/queue             -> cola de casos pendientes
  POST   /fraud/decide/explain    -> explicabilidad (XAI)
  POST   /fraud/decide/preview    -> what-if de umbrales
  POST   /fraud/challenge         -> recomendacion adaptativa de friccion
  POST   /fraud/feedback          -> cierre del caso por analista
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, Header
from api.limiter import limiter
from src.scoring import score_transaction

from api.schemas import (
    ChallengeOption,
    ChallengeRequest,
    ChallengeResponse,
    Decision,
    DecideResponse,
    ExplainRequest,
    ExplainResponse,
    FeedbackRequest,
    FeedbackResponse,
    PreviewMetrics,
    PreviewRequest,
    PreviewResponse,
    QueueItem,
    QueueResponse,
    RiskLevel,
    Transaction,
)
from src.scoring import (
    decision_from_score,
    score_transaction,
)
from src.storage import (
    add_to_queue,
    find_in_queue,
    get_queue,
    queue_size,
    remove_from_queue,
    store_feedback,
)

router = APIRouter(prefix="/fraud", tags=["product"])

API_SECRET_KEY = "centinela-secreto-123"

# ============================================================
# BASELINES POR RONDA (mock hasta tener métricas reales)
# Cuando Juanra tenga los resultados reales de R1/R2 con el modelo
# definitivo, basta con sustituir estos valores.
# ============================================================
ROUND_BASELINES = {
    "round_1": {
        "blocked": 142, "reviewed": 380, "allowed": 9478,
        "fraud_caught": 38, "false_positives": 12,
        "money_saved_eur": 28400.0,
        "total_transactions": 10000, "fraud_in_dataset": 50,
        "recall": 0.76, "precision": 0.76, "f1": 0.76,
        "avg_fraud_probability": 0.42,
    },
    "round_2": {
        "blocked": 168, "reviewed": 425, "allowed": 9407,
        "fraud_caught": 51, "false_positives": 18,
        "money_saved_eur": 39800.0,
        "total_transactions": 10000, "fraud_in_dataset": 62,
        "recall": 0.82, "precision": 0.74, "f1": 0.78,
        "avg_fraud_probability": 0.48,
    },
}


def _build_round_comparison(round_id: str) -> dict:
    """Construye el bloque de métricas de una ronda para la comparativa."""
    b = ROUND_BASELINES[round_id]
    return {
        "round_id": round_id,
        "total_transactions": b["total_transactions"],
        "fraud_in_dataset": b["fraud_in_dataset"],
        "fraud_caught": b["fraud_caught"],
        "fraud_missed": b["fraud_in_dataset"] - b["fraud_caught"],
        "recall": b["recall"],
        "precision": b["precision"],
        "f1_score": b["f1"],
        "money_saved_eur": b["money_saved_eur"],
        "avg_fraud_probability": b["avg_fraud_probability"],
    }


# ============================================================
# POST /fraud/decide
# ============================================================
@router.post(
    "/decide",
    response_model=DecideResponse,
    summary="Decision de fraude en tiempo real",
)
@limiter.limit("30/minute")
async def fraud_decide(
    request: Request, 
    tx_data: Transaction,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    
    """
    Endpoint principal. NovaPay lo llama ANTES de aprobar una transaccion.
    Devuelve allow / review / block + probabilidad + nivel de riesgo.
    """

    if x_api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=403, 
            detail="Acceso denegado. API Key inválida o faltante."
        )
    

    score, risk = score_transaction(tx_data)
    decision = decision_from_score(score)

    if score >= 0.80:
        action = "BLOCK"
    elif score >= 0.48:
        action = "REVIEW"
    else:
        action = "ALLOW"
        
    response = DecideResponse(
        transaction_id=tx_data.transaction_id,
        decision=decision,
        fraud_probability=score,
        risk_level=risk,
        timestamp=datetime.now(timezone.utc),
    )

    # Si va a review, la metemos en la cola del analista
    if decision == Decision.review:
        add_to_queue(QueueItem(
            transaction_id=tx_data.transaction_id,
            amount=tx_data.amount,
            type=tx_data.type.value,
            ip_country=tx_data.ip_country,
            merchant_category=tx_data.merchant_category,
            fraud_probability=score,
            risk_level=risk,
            timestamp=response.timestamp,
        ))

    return response


# ============================================================
# GET /fraud/queue
# ============================================================
@router.get(
    "/queue",
    response_model=QueueResponse,
    summary="Cola de casos pendientes de revision",
)
async def fraud_queue(
    limit: int = Query(default=50, le=200),
    risk_level: Optional[RiskLevel] = None,
):
    items = get_queue(limit=limit, risk_level=risk_level)
    return QueueResponse(
        total_pending=queue_size(risk_level=risk_level),
        queue=items,
    )


'''
# ============================================================
# POST /fraud/decide/explain
# ============================================================
@router.post(
    "/decide/explain",
    response_model=ExplainResponse,
    summary="Explicacion detallada (XAI) con counterfactual",
)
async def fraud_explain(req: ExplainRequest):
    """
    Explicabilidad bajo demanda.
    Devuelve narrative + feature contributions + counterfactual.
    """
    case = find_in_queue(req.transaction_id)
    if not case:
        raise HTTPException(
            status_code=404,
            detail=f"Transaccion {req.transaction_id} no encontrada en cola",
        )

    contributions = get_feature_contributions(
        ip_country=case.ip_country,
        merchant_category=case.merchant_category,
        amount=case.amount,
    )

    narrative_parts = [c.narrative for c in contributions]
    if narrative_parts:
        narrative = (
            f"Transaccion marcada con probabilidad {case.fraud_probability:.0%}. "
            + " ".join(narrative_parts)
        )
    else:
        narrative = (
            f"Transaccion marcada con probabilidad {case.fraud_probability:.0%} "
            "por anomalia en el patron."
        )

    counterfactual = build_counterfactual(
        ip_country=case.ip_country,
        merchant_category=case.merchant_category,
        amount=case.amount,
        current_score=case.fraud_probability,
    )

    return ExplainResponse(
        transaction_id=case.transaction_id,
        fraud_probability=case.fraud_probability,
        narrative=narrative,
        feature_contributions=contributions,
        counterfactual=counterfactual,
    )
'''

# ============================================================
# POST /fraud/decide/preview
# ============================================================
@router.post(
    "/decide/preview",
    response_model=PreviewResponse,
    summary="What-if: simula impacto de cambiar umbrales (R1/R2 + comparativa)",
)
async def fraud_preview(req: PreviewRequest):
    """
    Permite a NovaPay simular el impacto de cambiar umbrales sin tocar producción.

    Soporta:
      - test_set='round_1' o 'round_2' para evaluar contra cada dataset adversarial
      - compare=true para devolver además un bloque 'comparison' con R1 vs R2
        en la misma respuesta (ideal para el dashboard de benchmark)
    """
    # Baseline según la ronda elegida
    baseline = ROUND_BASELINES[req.test_set]

    current = PreviewMetrics(
        threshold_block=0.75,
        threshold_review=0.50,
        blocked=baseline["blocked"],
        reviewed=baseline["reviewed"],
        allowed=baseline["allowed"],
        fraud_caught=baseline["fraud_caught"],
        false_positives=baseline["false_positives"],
        money_saved_eur=baseline["money_saved_eur"],
    )

    threshold_delta = 0.75 - req.threshold_block
    extra_blocked = int(threshold_delta * 1000)
    extra_fraud_caught = int(threshold_delta * 100)
    extra_false_positives = int(threshold_delta * 900)
    extra_money_saved = threshold_delta * 50000

    preview = PreviewMetrics(
        threshold_block=req.threshold_block,
        threshold_review=req.threshold_review,
        blocked=current.blocked + extra_blocked,
        reviewed=current.reviewed + int(threshold_delta * 500),
        allowed=current.allowed - extra_blocked - int(threshold_delta * 500),
        fraud_caught=current.fraud_caught + extra_fraud_caught,
        false_positives=current.false_positives + extra_false_positives,
        money_saved_eur=round(current.money_saved_eur + extra_money_saved, 2),
    )

    if extra_fraud_caught > 0 and extra_false_positives < extra_fraud_caught * 10:
        recommendation = (
            f"Cambio recomendado: capturamos {extra_fraud_caught} fraudes mas "
            f"con coste razonable de {extra_false_positives} falsos positivos. "
            f"Ahorro neto estimado: {extra_money_saved:.0f} EUR."
        )
    elif extra_fraud_caught > 0:
        recommendation = (
            f"Cuidado: el cambio captura {extra_fraud_caught} fraudes mas pero "
            f"genera {extra_false_positives} falsos positivos."
        )
    else:
        recommendation = "El cambio no aporta deteccion adicional significativa."

    response_data = {
        "current_config": current,
        "preview_config": preview,
        "delta": {
            "extra_fraud_caught": extra_fraud_caught,
            "extra_false_positives": extra_false_positives,
            "extra_money_saved_eur": round(extra_money_saved, 2),
            "recommendation": recommendation,
            "test_set_evaluated": req.test_set,
        },
    }

    # Si piden comparativa, añadimos R1 vs R2 + improvement
    if req.compare:
        r1 = _build_round_comparison("round_1")
        r2 = _build_round_comparison("round_2")
        response_data["comparison"] = {
            "round_1": r1,
            "round_2": r2,
            "improvement": {
                "recall_delta": round(r2["recall"] - r1["recall"], 4),
                "f1_delta": round(r2["f1_score"] - r1["f1_score"], 4),
                "extra_fraud_caught": r2["fraud_caught"] - r1["fraud_caught"],
                "extra_money_saved_eur": round(r2["money_saved_eur"] - r1["money_saved_eur"], 2),
                "interpretation": (
                    "El modelo de Ronda 2 detecta más fraude adaptativo que Ronda 1: "
                    f"+{round((r2['recall'] - r1['recall']) * 100, 1)}% de recall, "
                    f"+{r2['fraud_caught'] - r1['fraud_caught']} fraudes adicionales capturados, "
                    f"+{round(r2['money_saved_eur'] - r1['money_saved_eur'], 0)}€ ahorrados."
                ),
            },
        }

    return response_data

# ============================================================
# POST /fraud/challenge
# ============================================================
@router.post(
    "/challenge",
    response_model=ChallengeResponse,
    summary="Recomendacion adaptativa de friccion",
)
async def fraud_challenge(req: ChallengeRequest):
    """
    En vez de allow/block, recomienda una friccion proporcional al riesgo
    (SMS, biometria, revision manual...). Como hacen Revolut, Stripe, etc.
    """
    score = req.fraud_probability
    ctx = req.transaction_context

    if score < 0.45:
        primary = ChallengeOption(
            action="allow",
            friction="none",
            user_message="Transaccion aprobada.",
        )
        alternatives = []
        reasoning = "Score bajo. Transaccion dentro de patrones normales."

    elif score < 0.60:
        primary = ChallengeOption(
            action="sms_otp",
            friction="low",
            user_message="Hemos enviado un codigo a tu movil para confirmar esta operacion.",
        )
        alternatives = [
            ChallengeOption(action="email_confirmation", friction="low"),
            ChallengeOption(action="transaction_limit_24h", friction="low"),
        ]
        reasoning = f"Score medio ({score:.0%}). Recomendamos verificacion ligera."

    elif score < 0.75:
        primary = ChallengeOption(
            action="biometric_auth",
            friction="medium",
            user_message="Por favor verifica tu identidad con huella o reconocimiento facial.",
        )
        alternatives = [
            ChallengeOption(action="manual_review", friction="high"),
            ChallengeOption(action="sms_otp", friction="low"),
        ]
        reasoning = (
            f"Score medio-alto ({score:.0%}) + categoria {ctx.merchant_category}. "
            f"Recomendamos verificacion reforzada antes de bloquear."
        )

    else:
        primary = ChallengeOption(
            action="manual_review",
            friction="high",
            user_message="Hemos pausado esta operacion. Nuestro equipo la revisara en breve.",
        )
        alternatives = [
            ChallengeOption(action="block", friction="high"),
            ChallengeOption(action="biometric_auth", friction="medium"),
        ]
        reasoning = f"Score alto ({score:.0%}). Riesgo elevado, recomendamos revision humana."

    return ChallengeResponse(
        transaction_id=req.transaction_id,
        recommended_action=primary.action,
        primary_option=primary,
        alternative_options=alternatives,
        reasoning=reasoning,
    )


# ============================================================
# POST /fraud/feedback
# ============================================================
@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Cierra el ciclo: el analista marca el resultado real",
)
async def fraud_feedback(req: FeedbackRequest):
    """
    El analista cierra el caso. Esto se guarda para auditoria y reentrenamiento.
    """
    case_id = f"case_{uuid4().hex[:8]}"

    store_feedback(
        case_id=case_id,
        transaction_id=req.transaction_id,
        analyst_decision=req.analyst_decision,
        analyst_notes=req.analyst_notes,
        analyst_id=req.analyst_id,
    )

    # Quitar de la cola pendiente
    remove_from_queue(req.transaction_id)

    return FeedbackResponse(
        status="stored",
        case_id=case_id,
        transaction_id=req.transaction_id,
        decision=req.analyst_decision,
    )
