import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException
from api.schemas import Transaction, DecisionResponse
from src.scoring import score_transaction
from src.storage import save_transaction

# Inicialización del Router
router = APIRouter(prefix="/fraud", tags=["Fraud Detection"])

# Cargar el modelo en memoria una sola vez al arrancar
try:
    model = joblib.load("model/xgboost_fraud_model.joblib")
    print("✅ Modelo XGBoost cargado correctamente.")
except Exception as e:
    model = None
    print(f"⚠️ Advertencia crítica: No se pudo cargar el modelo. {e}")

@router.post("/decide", response_model=DecisionResponse)
def decide_fraud(tx: Transaction):
    if model is None:
        raise HTTPException(status_code=500, detail="Motor de Machine Learning inactivo.")

    try:
        # 1. Transformamos la petición (Pydantic) a un diccionario estándar
        tx_dict = tx.model_dump()
        
        # 2. Pasamos la transacción por tus reglas heurísticas de negocio
        scoring_result = score_transaction(tx)
        
        # 3. Metemos los datos en un DataFrame de 1 sola fila para que XGBoost no se queje
        df = pd.DataFrame([tx_dict])
        
        # 4. Inferencia: calculamos la probabilidad matemática y la etiqueta binaria
        fraud_prob = float(model.predict_proba(df)[0][1])
        is_fraud = int(model.predict(df)[0])
        
        # 5. Decisión Final: Si la IA detecta fraude O tus reglas de negocio lo exigen, se bloquea
        decision = "block" if (is_fraud == 1 or scoring_result.get("action") == "block") else "allow"
        
        # 6. Añadimos el veredicto de vuelta al diccionario para la base de datos
        tx_dict["fraud_probability"] = fraud_prob
        tx_dict["risk_level"] = "high" if decision == "block" else "low"
        tx_dict["decision"] = decision
        
        # 7. Inyección limpia en la base de datos de producción (Full Stack)
        save_transaction(tx_dict)
        
        # 8. Devolvemos la respuesta formateada al frontend
        return DecisionResponse(
            transaction_id="generado-en-db", # Supabase asignará el UUID real
            decision=decision,
            fraud_probability=fraud_prob,
            risk_factors=scoring_result.get("flags", [])
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en el motor de inferencia: {str(e)}")