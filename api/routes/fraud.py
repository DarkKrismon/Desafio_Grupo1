"""
api/routes/fraud.py
===================
Endpoints de producto (lo que NovaPay integraria):
  POST   /fraud/decide            -> decision en tiempo real
  GET    /fraud/queue             -> cola de casos pendientes
  POST   /fraud/decide/preview    -> what-if de umbrales
  POST   /fraud/challenge         -> recomendacion adaptativa de friccion
  POST   /fraud/feedback          -> cierre del caso por analista
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, Header
from api.limiter import limiter
from src.scoring import score_transaction, decision_from_score
from src.client_profile import build_client_profile

from src.storage import save_transaction, get_pending_queue, resolve_case, get_connection

from src.llm_explainer import analyze_fraud_with_llm
from psycopg2.extras import RealDictCursor

from api.schemas import (
    ChallengeOption, ChallengeRequest, ChallengeResponse,
    Decision, DecideResponse, ExplainRequest, ExplainResponse,
    FeedbackRequest, FeedbackResponse, PreviewMetrics, PreviewRequest, PreviewResponse,
    QueueItem, QueueResponse, RiskLevel, Transaction, ClientProfileResponse
)

router = APIRouter(prefix="/fraud", tags=["product"])

API_SECRET_KEY = "centinela-secreto-123"

# ============================================================
# POST /fraud/decide
# ============================================================
@router.post("/decide", response_model=DecideResponse, summary="Decision de fraude en tiempo real")
@limiter.limit("30/minute")
async def fraud_decide(
    request: Request, 
    tx_data: Transaction,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Acceso denegado. API Key inválida o faltante.")

    # ── DEMO OVERRIDE (debe ir primero) ─────────────────────────────────────
    if tx_data.transaction_id == "TXN-DEMO-REVIEW":
        score    = 0.58
        risk     = RiskLevel.medium
        decision = Decision.review
        response = DecideResponse(
            transaction_id=tx_data.transaction_id,
            decision=decision,
            fraud_probability=score,
            risk_level=risk,
            timestamp=datetime.now(timezone.utc),
        )
        tx_dict = tx_data.model_dump(mode='json')
        tx_dict["type"] = tx_data.type.value
        tx_dict["fraud_probability"] = score
        tx_dict["risk_level"] = risk.value
        tx_dict["decision"] = decision.value
        save_transaction(tx_dict)
        return response

    # 1. Scoring ML
    score, risk = score_transaction(tx_data)

    # Bonus por historial del cliente
    try:
        profile = build_client_profile(tx_data.nameOrig, recent_limit=5)
        if profile:
            from src.scoring import apply_client_history_bonus
            history_bonus = apply_client_history_bonus(
                fraud_rate=profile["stats"]["fraud_rate_historical"],
                total_transactions=profile["stats"]["total_transactions"]
            )
            score = min(score + history_bonus, 1.0)
            score = round(score, 4)

            total_tx = profile["stats"]["total_transactions"]
            if total_tx == 0 and score > 0:
                score = max(score, 0.45)
        else:
            if score > 0:
                score = max(score, 0.45)
    except Exception as e:
        print(f"⚠️ Error historial cliente: {e}")

    decision = decision_from_score(score)

    response = DecideResponse(
        transaction_id=tx_data.transaction_id,
        decision=decision,
        fraud_probability=score,
        risk_level=risk,
        timestamp=datetime.now(timezone.utc),
    )

    # 2. Guardamos en Supabase
    tx_dict = tx_data.model_dump(mode='json')
    tx_dict["type"] = tx_data.type.value
    tx_dict["fraud_probability"] = score
    tx_dict["risk_level"] = risk.value
    tx_dict["decision"] = decision.value
    save_transaction(tx_dict)

    return response

# ============================================================
# GET /fraud/queue
# ============================================================
@router.get("/queue", response_model=QueueResponse, summary="Cola de casos pendientes de revision")
async def fraud_queue(
    limit: int = Query(default=50, le=200),
    risk_level: Optional[RiskLevel] = None,
    x_api_key: str = Header(None, alias="X-API-Key"),  # Requerimos API Key para proteger la cola de casos pendientes
):
    # Verificamos que la API Key sea válida antes de mostrar la cola de revisión
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado. API Key inválida o faltante."
        )
    
    total_pending, items = get_pending_queue(limit=limit, risk_level=risk_level)
    return QueueResponse(
        total_pending=total_pending,
        queue=items,
    )

# ============================================================
# POST /fraud/decide/preview
# ============================================================
@router.post("/decide/preview", response_model=PreviewResponse, summary="What-if: simula impacto")
async def fraud_preview(req: PreviewRequest):
    # (Funcionalidad original mantenida intacta)
    current = PreviewMetrics(
        threshold_block=0.75, threshold_review=0.50, blocked=142, reviewed=380, allowed=9478,
        fraud_caught=38, false_positives=12, money_saved_eur=28400.0,
    )

    threshold_delta = 0.75 - req.threshold_block
    extra_blocked = int(threshold_delta * 1000)
    extra_fraud_caught = int(threshold_delta * 100)
    extra_false_positives = int(threshold_delta * 900)
    extra_money_saved = threshold_delta * 50000

    preview = PreviewMetrics(
        threshold_block=req.threshold_block, threshold_review=req.threshold_review,
        blocked=current.blocked + extra_blocked, reviewed=current.reviewed + int(threshold_delta * 500),
        allowed=current.allowed - extra_blocked - int(threshold_delta * 500),
        fraud_caught=current.fraud_caught + extra_fraud_caught,
        false_positives=current.false_positives + extra_false_positives,
        money_saved_eur=round(current.money_saved_eur + extra_money_saved, 2),
    )

    recommendation = "Análisis de impacto calculado."
    if extra_fraud_caught > 0 and extra_false_positives < extra_fraud_caught * 10:
        recommendation = f"Recomendado: Ahorro neto estimado: {extra_money_saved:.0f} EUR."

    return PreviewResponse(
        current_config=current, preview_config=preview,
        delta={"extra_fraud_caught": extra_fraud_caught, "extra_false_positives": extra_false_positives, "recommendation": recommendation}
    )

# ============================================================
# POST /fraud/challenge
# ============================================================
@router.post("/challenge", response_model=ChallengeResponse, summary="Friccion adaptativa")
async def fraud_challenge(req: ChallengeRequest):
    # (Funcionalidad original mantenida intacta)
    score = req.fraud_probability
    ctx = req.transaction_context

    if score < 0.45:
        primary = ChallengeOption(action="allow", friction="none", user_message="Aprobada.")
    elif score < 0.60:
        primary = ChallengeOption(action="sms_otp", friction="low", user_message="Enviado código SMS.")
    elif score < 0.75:
        primary = ChallengeOption(action="biometric_auth", friction="medium", user_message="Verifica identidad.")
    else:
        primary = ChallengeOption(action="manual_review", friction="high", user_message="En revisión.")

    return ChallengeResponse(
        transaction_id=req.transaction_id, recommended_action=primary.action,
        primary_option=primary, alternative_options=[], reasoning="Cálculo basado en score."
    )

# ============================================================
# POST /fraud/feedback
# ============================================================
@router.post("/feedback", response_model=FeedbackResponse, summary="Cierre del caso por analista")
async def fraud_feedback(
    req: FeedbackRequest,
    x_api_key: str = Header(None, alias="X-API-Key"),  # Requerimos API Key para proteger el cierre de casos
):
    """
    Cuando el analista aprueba o bloquea en el panel web, actualizamos la base de datos real.
    """
    # Verificamos que la API Key sea válida antes de procesar el feedback
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado. API Key inválida o faltante."
        )

    case_id = f"case_{uuid4().hex[:8]}"
    
    resolve_case(req.transaction_id, req.analyst_decision, req.analyst_id)

    return FeedbackResponse(
        status="stored",
        case_id=case_id,
        transaction_id=req.transaction_id,
        decision=req.analyst_decision,
    )

# ============================================================
# GET /fraud/client/{name_orig}
# ============================================================
@router.get(
    "/client/{name_orig}",
    response_model=ClientProfileResponse,
    summary="Perfil del cliente para el modal del analista",
)
async def get_client_profile(
    name_orig: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_api_key: str = Header(None, alias="X-API-Key"),  # Validación de API Key
):
    """
    Devuelve estadísticas históricas y banderas de riesgo consultando
    directamente la base de datos de Full Stack.
    """
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado. API Key inválida o faltante."
        )
    
    profile = build_client_profile(name_orig, recent_limit=limit, recent_offset=offset)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cliente '{name_orig}' no encontrado en el histórico",
        )
    return profile


# ============================================================
# GET /fraud/explain/{transaction_id}
# ============================================================
@router.get("/explain/{transaction_id}", summary="Explicación del fraude simplificada")
async def fraud_explain_simple(transaction_id: str):
    # 1. Buscamos la transacción directamente con el ID de la URL
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM "Transactions" WHERE transaction_id = %s', (transaction_id,))
        tx = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error conectando a la base de datos.")
    
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada.")

    # 2. Preparamos el payload anonimizado
    anon_data = {
        "step_hours": tx["step"],
        "type": tx["type"],
        "amount": tx["amount"],
        "oldbalanceOrg": tx["oldbalanceOrg"],
        "newbalanceOrig": tx["newbalanceOrig"],
        "oldbalanceDest": tx["oldbalanceDest"],
        "newbalanceDest": tx["newbalanceDest"],
        "ip_country": tx["ip_country"],
        "merchant_category": tx["merchant_category"]
    }

    # 3. Delegamos el trabajo al módulo LLM
    explicacion = analyze_fraud_with_llm(anon_data)

    # 4. Devolvemos el JSON minimalista
    return {"narrative": explicacion}