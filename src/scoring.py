import joblib
import os
from api.schemas import Decision, RiskLevel, Transaction

# 1. Cargar modelos al arrancar (Singleton)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "best_threshold.joblib")
PREP_PATH = os.path.join(BASE_DIR, "models", "xgb_fraud_pipeline.joblib")

print("Cargando modelo de Machine Learning...")
try:
    modelo = joblib.load(MODEL_PATH)
    preprocesador = joblib.load(PREP_PATH)
    print("✅ Modelo cargado con éxito.")
except Exception as e:
    modelo = None
    preprocesador = None
    print(f"⚠️ ERROR CRÍTICO: No se pudo cargar el modelo. {e}")

def score_transaction(tx: Transaction) -> tuple[float, RiskLevel]:
    if modelo is None:
        return 0.0, RiskLevel.low # Fallback de emergencia

    # 2. Extraer datos del JSON (tx) al formato que espera el preprocesador
    import pandas as pd
    df_tx = pd.DataFrame([{
        "amount": tx.amount,
        "oldbalanceOrg": tx.oldbalanceOrg,
        "newbalanceOrig": tx.newbalanceOrig,
        "oldbalanceDest": tx.oldbalanceDest,
        "newbalanceDest": tx.newbalanceDest,
        "type": tx.type.value,
        # ... añade las variables derivadas que creaste (ej. error_balance)
    }])

    # 3. Preprocesar e Inferir
    X_limpio = preprocesador.transform(df_tx)
    
    # predict_proba devuelve algo como [[0.15, 0.85]] (Prob Legitimo, Prob Fraude)
    score = float(modelo.predict_proba(X_limpio)[0][1])

    # 4. Asignar Riesgo
    if score >= 0.75:
        risk = RiskLevel.high
    elif score >= 0.45:
        risk = RiskLevel.medium
    else:
        risk = RiskLevel.low

    return score, risk