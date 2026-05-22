import joblib
import os
import pandas as pd
from api.schemas import Decision, RiskLevel, Transaction

# ============================================================
# CARGA DE MODELOS
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_PATH = os.path.join(BASE_DIR, "models", "xgb_fraud_pipeline.joblib")
THRESHOLD_PATH = os.path.join(BASE_DIR, "models", "best_threshold.joblib")

print("Cargando modelo de Machine Learning...")
try:
    pipeline = joblib.load(PIPELINE_PATH)
    threshold = joblib.load(THRESHOLD_PATH)
    print("✅ Modelo cargado con éxito.")
except Exception as e:
    pipeline = None
    threshold = 0.6
    print(f"⚠️ ERROR CRÍTICO: No se pudo cargar el modelo. {e}")


# ============================================================
# BONUS RULES
# ============================================================
def apply_bonus_rules(tx: Transaction, score_ml: float) -> float:
    bonus = 0.0

    high_risk_countries = ['KH', 'CN', 'NG', 'CI', 'VE']
    high_risk_categories = ['crypto', 'electronics']

    if tx.ip_country in high_risk_countries:
        bonus += 0.05

    if tx.merchant_category in high_risk_categories:
        bonus += 0.05

    if tx.amount > 8000:
        bonus += 0.05

    balance_error_orig = abs((tx.oldbalanceOrg - tx.amount) - tx.newbalanceOrig)
    if balance_error_orig > 0.01:
        bonus += 0.08

    balance_error_dest = abs((tx.oldbalanceDest + tx.amount) - tx.newbalanceDest)
    if balance_error_dest > 0.01:
        bonus += 0.08

    if tx.oldbalanceOrg == 0 and tx.newbalanceOrig == 0:
        bonus += 0.06

    if tx.ip_country in high_risk_countries and tx.merchant_category in high_risk_categories:
        bonus += 0.05

    score_final = min(score_ml + bonus, 1.0)
    return round(score_final, 4)


# ============================================================
# SCORING
# ============================================================
def score_transaction(tx: Transaction) -> tuple[float, RiskLevel]:
    if pipeline is None:
        return 0.0, RiskLevel.low

    df_tx = pd.DataFrame([{
        "amount": tx.amount,
        "oldbalanceOrg": tx.oldbalanceOrg,
        "newbalanceOrig": tx.newbalanceOrig,
        "oldbalanceDest": tx.oldbalanceDest,
        "newbalanceDest": tx.newbalanceDest,
        "type": tx.type.value,
        "merchant_category": tx.merchant_category,
        "ip_country": tx.ip_country,
        "is_high_risk_country": 1 if tx.ip_country in ['KH', 'CN', 'NG', 'CI', 'VE'] else 0,
        "is_high_risk_category": 1 if tx.merchant_category in ['crypto', 'electronics'] else 0,
    }])

    score_ml = float(pipeline.predict_proba(df_tx)[0][1])
    score_final = apply_bonus_rules(tx, score_ml)

    if score_final >= 0.75:
        risk = RiskLevel.high
    elif score_final >= 0.45:
        risk = RiskLevel.medium
    else:
        risk = RiskLevel.low

    return score_final, risk


# ============================================================
# DECISION
# ============================================================
def decision_from_score(score: float) -> Decision:
    if score >= threshold:
        return Decision.block
    elif score >= 0.45:
        return Decision.review
    else:
        return Decision.allow