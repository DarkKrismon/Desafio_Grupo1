"""
src/scoring.py
==============
Logica de scoring de fraude y explicabilidad.

HOY: heuristica mock calibrada con los datos sinteticos.
MAÑANA: cuando el modelo ML este entrenado, sustituir score_transaction()
        para que cargue desde models/ y llame a model.predict_proba().

La API NO se entera del cambio. Solo importa estas funciones.
"""

from api.schemas import (
    Decision,
    FeatureContribution,
    RiskLevel,
    Transaction,
    TransactionType,
)


# ============================================================
# CONFIGURACION DE LA HEURISTICA (mock)
# ============================================================
HIGH_RISK_COUNTRIES = {"KH", "NG", "PK", "RU"}
MEDIUM_RISK_COUNTRIES = {"VE", "CN", "BR", "MX", "TH", "ID", "EG"}
HIGH_RISK_CATEGORIES = {"crypto", "gambling", "wire_transfer"}


# ============================================================
# SCORING PRINCIPAL
# ============================================================
def score_transaction(tx: Transaction) -> tuple[float, RiskLevel]:
    """
    Calcula la probabilidad de fraude de una transaccion.

    Returns:
        (probabilidad_fraude entre 0 y 1, RiskLevel)

    TODO: sustituir por modelo entrenado cuando este listo:
        from joblib import load
        model = load('models/fraud_xgb_v1.pkl')
        features = extract_features(tx)
        score = model.predict_proba([features])[0][1]
    """
    score = 0.10  # baseline

    # Pais de origen
    if tx.ip_country in HIGH_RISK_COUNTRIES:
        score += 0.30
    elif tx.ip_country in MEDIUM_RISK_COUNTRIES:
        score += 0.18

    # Categoria de comercio
    if tx.merchant_category.lower() in HIGH_RISK_CATEGORIES:
        score += 0.20

    # Importe
    if tx.amount > 1000:
        score += 0.15
    elif tx.amount > 500:
        score += 0.05

    # Patron PaySim: vaciado de cuenta origen
    if tx.oldbalanceOrg > 0:
        ratio_drained = (tx.oldbalanceOrg - tx.newbalanceOrig) / tx.oldbalanceOrg
        if ratio_drained > 0.95:
            score += 0.15

    # Tipo de transaccion mas sospechoso
    if tx.type in (TransactionType.cash_out, TransactionType.transfer):
        score += 0.03

    score = min(round(score, 2), 0.99)

    # Mapear a risk level
    if score >= 0.75:
        risk = RiskLevel.high
    elif score >= 0.45:
        risk = RiskLevel.medium
    else:
        risk = RiskLevel.low

    return score, risk


def decision_from_score(score: float) -> Decision:
    """Mapea score a decision segun umbrales por defecto."""
    if score >= 0.75:
        return Decision.block
    elif score >= 0.50:
        return Decision.review
    else:
        return Decision.allow


# ============================================================
# EXPLICABILIDAD (XAI)
# ============================================================
def get_feature_contributions(
    ip_country: str,
    merchant_category: str,
    amount: float,
) -> list[FeatureContribution]:
    """
    Devuelve las features que mas contribuyeron al score.
    Mock hoy. Manana: sustituir por SHAP values reales.
    """
    contributions = []

    if ip_country in HIGH_RISK_COUNTRIES:
        contributions.append(FeatureContribution(
            feature="ip_country_high_risk",
            impact=0.30,
            narrative=f"El pais {ip_country} esta en la lista de alto riesgo.",
        ))
    elif ip_country in MEDIUM_RISK_COUNTRIES:
        contributions.append(FeatureContribution(
            feature="ip_country_medium_risk",
            impact=0.18,
            narrative=f"El pais {ip_country} tiene riesgo moderado.",
        ))

    if merchant_category.lower() in HIGH_RISK_CATEGORIES:
        contributions.append(FeatureContribution(
            feature="merchant_category_risky",
            impact=0.20,
            narrative=f"La categoria '{merchant_category}' tiene alta tasa historica de fraude.",
        ))

    if amount > 1000:
        contributions.append(FeatureContribution(
            feature="amount_high",
            impact=0.15,
            narrative=f"Importe de {amount} EUR supera el ticket habitual.",
        ))
    elif amount > 500:
        contributions.append(FeatureContribution(
            feature="amount_medium",
            impact=0.05,
            narrative=f"Importe de {amount} EUR es moderadamente alto.",
        ))

    return contributions


def build_counterfactual(
    ip_country: str,
    merchant_category: str,
    amount: float,
    current_score: float,
) -> str:
    """
    Genera un counterfactual: que tendria que haber cambiado
    para que la transaccion se hubiera aprobado.
    """
    changes = []
    expected_drop = 0.0

    if ip_country in HIGH_RISK_COUNTRIES or ip_country in MEDIUM_RISK_COUNTRIES:
        changes.append("el pais de origen fuera Espana")
        expected_drop += 0.25

    if merchant_category.lower() in HIGH_RISK_CATEGORIES:
        changes.append(f"la categoria no fuera '{merchant_category}'")
        expected_drop += 0.20

    if amount > 1000:
        changes.append("el importe fuera inferior a 500 EUR")
        expected_drop += 0.15

    if not changes:
        return "La transaccion ya esta en el rango bajo de riesgo."

    new_score = max(current_score - expected_drop, 0.05)
    return (
        f"Si {' y '.join(changes)}, la probabilidad bajaria aproximadamente "
        f"a {new_score:.0%} y la transaccion se habria aprobado directamente."
    )
