import joblib
import os
import pandas as pd
from api.schemas import Decision, RiskLevel, Transaction

# ============================================================
# CARGA DE MODELOS
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "xgb_fraud_pipeline.joblib")
PREP_PATH = os.path.join(BASE_DIR, "models", "xgb_fraud_pipeline.joblib")

pipeline_real = joblib.load(MODEL_PATH)

print("Cargando modelo de Machine Learning...")
try:
    pipeline = joblib.load(PREP_PATH)      # pipeline completo (preprocesador + XGBoost)
    threshold = joblib.load(MODEL_PATH)    # float escalar (ej: 0.6)
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

    # Pais de alto riesgo
    if tx.ip_country in high_risk_countries:
        bonus += 0.05

    # Categoria sospechosa
    if tx.merchant_category in high_risk_categories:
        bonus += 0.05

    # Monto muy alto (p95 aprox)
    if tx.amount > 8000:
        bonus += 0.05

    # Balance error origen
    balance_error_orig = abs((tx.oldbalanceOrg - tx.amount) - tx.newbalanceOrig)
    if balance_error_orig > 0.01:
        bonus += 0.08

    # Balance error destino
    balance_error_dest = abs((tx.oldbalanceDest + tx.amount) - tx.newbalanceDest)
    if balance_error_dest > 0.01:
        bonus += 0.08

    # Cuenta origen empieza en 0 y sigue en 0
    if tx.oldbalanceOrg == 0 and tx.newbalanceOrig == 0:
        bonus += 0.06

    # Combinacion pais + categoria (doble señal)
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

    input_data = pd.DataFrame([tx.model_dump()])

    # Inferencia matemática real del modelo XGBoost
    score_real = float(pipeline_real.predict_proba(input_data)[0][1])

    if score_real >= 0.75:
        risk = RiskLevel.high
    elif score_real >= 0.45:
        risk = RiskLevel.medium
    else:
        risk = RiskLevel.low

    return score_real, risk


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