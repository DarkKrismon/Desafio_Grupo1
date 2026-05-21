"""
src/scoring.py
==============
Logica de scoring de fraude y explicabilidad.

Usa estadisticas reales del dataset cargado por data_loader.py:
  - Tasa de fraude por pais
  - Tasa de fraude por categoria de comercio
  - Tasa de fraude por tipo de transaccion
  - Umbrales de monto (percentil 95)

Esta basado en heuristica HOY. Cuando el modelo ML este entrenado,
sustituir score_transaction() para que llame a model.predict_proba().
La API no se entera del cambio.
"""

from api.schemas import (
    Decision,
    FeatureContribution,
    RiskLevel,
    Transaction,
    TransactionType,
)
from src.data_loader import compute_stats


# ============================================================
# CARGA DE STATS AL IMPORTAR
# ============================================================
_stats = compute_stats()
FRAUD_BY_COUNTRY = _stats["fraud_by_country"]
FRAUD_BY_CATEGORY = _stats["fraud_by_category"]
FRAUD_BY_TYPE = _stats["fraud_by_type"]
HIGH_AMOUNT_THRESHOLD = _stats["high_amount_threshold"]
AVG_AMOUNT = _stats["avg_amount"]
GLOBAL_FRAUD_RATE = _stats["global_fraud_rate"]


# ============================================================
# SCORING PRINCIPAL
# ============================================================
def score_transaction(tx: Transaction) -> tuple[float, RiskLevel]:
    """
    Calcula la probabilidad de fraude usando tasas reales del dataset.

    TODO: sustituir por modelo entrenado cuando este listo:
        from joblib import load
        model = load('models/fraud_xgb_v1.pkl')
        features = extract_features(tx)
        score = model.predict_proba([features])[0][1]
    """
    score = 0.05  # baseline minimo

    # 1. Pais: si conocemos su tasa real, pesa fuerte
    country_rate = FRAUD_BY_COUNTRY.get(tx.ip_country, GLOBAL_FRAUD_RATE)
    score += country_rate * 0.50

    # 2. Categoria de comercio
    category_rate = FRAUD_BY_CATEGORY.get(
        tx.merchant_category.lower(), GLOBAL_FRAUD_RATE
    )
    score += category_rate * 0.30

    # 3. Tipo de transaccion (TRANSFER y CASH_OUT suelen ser mas riesgosos)
    type_rate = FRAUD_BY_TYPE.get(tx.type.value, GLOBAL_FRAUD_RATE)
    score += type_rate * 0.20

    # 4. Importe alto
    if tx.amount > HIGH_AMOUNT_THRESHOLD:
        score += 0.20
    elif tx.amount > HIGH_AMOUNT_THRESHOLD * 0.5:
        score += 0.08

    # 5. Patron PaySim clasico: vaciado de cuenta origen
    if tx.oldbalanceOrg > 0:
        ratio_drained = (tx.oldbalanceOrg - tx.newbalanceOrig) / tx.oldbalanceOrg
        if ratio_drained > 0.95:
            score += 0.15

    score = min(round(score, 2), 0.99)

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
    Devuelve las features que mas contribuyeron al score,
    basadas en estadisticas reales del dataset.
    """
    contributions = []

    country_rate = FRAUD_BY_COUNTRY.get(ip_country, GLOBAL_FRAUD_RATE)
    if country_rate > GLOBAL_FRAUD_RATE * 1.5:
        contributions.append(FeatureContribution(
            feature="ip_country_high_risk",
            impact=round(country_rate * 0.50, 3),
            narrative=(
                f"El pais {ip_country} tiene una tasa de fraude del "
                f"{country_rate:.1%} en nuestro historico, frente al "
                f"{GLOBAL_FRAUD_RATE:.1%} global."
            ),
        ))

    category_rate = FRAUD_BY_CATEGORY.get(
        merchant_category.lower(), GLOBAL_FRAUD_RATE
    )
    if category_rate > GLOBAL_FRAUD_RATE * 1.5:
        contributions.append(FeatureContribution(
            feature="merchant_category_risky",
            impact=round(category_rate * 0.30, 3),
            narrative=(
                f"La categoria '{merchant_category}' tiene tasa de fraude "
                f"del {category_rate:.1%}, por encima de la media."
            ),
        ))

    if amount > HIGH_AMOUNT_THRESHOLD:
        contributions.append(FeatureContribution(
            feature="amount_high",
            impact=0.20,
            narrative=(
                f"Importe de {amount:,.0f} EUR supera el percentil 95 "
                f"({HIGH_AMOUNT_THRESHOLD:,.0f} EUR)."
            ),
        ))
    elif amount > HIGH_AMOUNT_THRESHOLD * 0.5:
        contributions.append(FeatureContribution(
            feature="amount_medium",
            impact=0.08,
            narrative=(
                f"Importe de {amount:,.0f} EUR es moderadamente alto "
                f"(media: {AVG_AMOUNT:,.0f} EUR)."
            ),
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

    country_rate = FRAUD_BY_COUNTRY.get(ip_country, GLOBAL_FRAUD_RATE)
    if country_rate > GLOBAL_FRAUD_RATE * 1.5:
        changes.append(f"el pais de origen no fuera {ip_country}")
        expected_drop += country_rate * 0.40

    category_rate = FRAUD_BY_CATEGORY.get(
        merchant_category.lower(), GLOBAL_FRAUD_RATE
    )
    if category_rate > GLOBAL_FRAUD_RATE * 1.5:
        changes.append(f"la categoria no fuera '{merchant_category}'")
        expected_drop += category_rate * 0.25

    if amount > HIGH_AMOUNT_THRESHOLD:
        changes.append(f"el importe fuera inferior a {HIGH_AMOUNT_THRESHOLD:,.0f} EUR")
        expected_drop += 0.20

    if not changes:
        return "La transaccion ya esta en el rango bajo de riesgo."

    new_score = max(current_score - expected_drop, 0.05)
    return (
        f"Si {' y '.join(changes)}, la probabilidad bajaria aproximadamente "
        f"a {new_score:.0%} y la transaccion se habria aprobado directamente."
    )
