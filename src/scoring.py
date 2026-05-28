import joblib
import os
import numpy as np
import pandas as pd
from api.schemas import Decision, RiskLevel, Transaction
 
# ============================================================
# SELECCIÓN DE MODELO
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_VERSION = os.getenv("MODEL_VERSION", "r1")
 
if MODEL_VERSION == "r2":
    PIPELINE_PATH = os.path.join(BASE_DIR, "models", "xgb_fraud_pipeline_r2.joblib")
    print("Modo: R2 (fraude sigiloso)")
else:
    PIPELINE_PATH = os.path.join(BASE_DIR, "models", "xgb_fraud_pipeline.joblib")
    print("Modo: R1 (fraude obvio)")
 
print("Cargando modelo de Machine Learning...")
try:
    pipeline = joblib.load(PIPELINE_PATH)
    print("✅ Modelo cargado con éxito.")
except Exception as e:
    pipeline = None
    print(f"⚠️ ERROR CRÍTICO: No se pudo cargar el modelo. {e}")
 
 
# ============================================================
# UMBRALES DE IMPORTE POR CATEGORÍA
# Contexto: clientes individuales, no empresas.
# Una persona física raramente supera estos importes en estas categorías.
# ============================================================
CATEGORY_AMOUNT_THRESHOLDS = {
    "restaurant": 50_000.0,   # restaurantes de lujo con botellas incluidas
    "pharmacy":    2_000.0,   # medicación individual
    "grocery":     3_000.0,   # compra personal de supermercado
    "fuel":        2_500.0,   # repostaje individual
    "transport":  35_000.0,   # billete de primera clase de aerolínea de lujo
    # electronics y crypto no tienen umbral aquí:
    # ya tienen bonus por ser categorías de alto riesgo
}
 
 
# ============================================================
# BONUS RULES
# ============================================================
def apply_bonus_rules(tx: Transaction, score_ml: float) -> float:
    bonus = 0.0
 
    high_risk_countries  = ['KH', 'CN', 'NG', 'CI', 'VE']
    high_risk_categories = ['crypto', 'electronics']
    drain_types          = ['CASH_OUT', 'TRANSFER', 'DEBIT']
 
    # País de alto riesgo
    if tx.ip_country in high_risk_countries:
        bonus += 0.10
 
    # Categoría de alto riesgo
    if tx.merchant_category in high_risk_categories:
        bonus += 0.10
 
    # Importe elevado (> percentil 95 del dataset)
    if tx.amount > 8_000:
        bonus += 0.10
 
    # Importe muy elevado (independiente de país y categoría)
    if tx.amount > 50_000:
        bonus += 0.25
 
    # Importe anómalo para la categoría del comercio
    # Una persona física raramente supera estos umbrales en estas categorías
    category_threshold = CATEGORY_AMOUNT_THRESHOLDS.get(tx.merchant_category)
    if category_threshold and tx.amount > category_threshold:
        bonus += 0.20
 
    # Error contable en balance origen
    balance_error_orig = abs((tx.oldbalanceOrg - tx.amount) - tx.newbalanceOrig)
    if balance_error_orig > 0.01:
        bonus += 0.12
 
    # Error contable en balance destino
    balance_error_dest = abs((tx.oldbalanceDest + tx.amount) - tx.newbalanceDest)
    if balance_error_dest > 0.01:
        bonus += 0.12
 
    # Cuenta origen con saldo cero antes Y después en operaciones que deberían drenar
    # (indica cuenta fantasma usada como relay, no vaciado real)
    if tx.oldbalanceOrg == 0 and tx.newbalanceOrig == 0 and tx.type.value in drain_types:
        bonus += 0.15
 
    # Combinación país + categoría de alto riesgo
    if tx.ip_country in high_risk_countries and tx.merchant_category in high_risk_categories:
        bonus += 0.10
 
    # Ratio de drenaje con señal de riesgo activa
    has_risk_signal = (tx.ip_country in high_risk_countries or tx.merchant_category in high_risk_categories)
    drain_ratio = tx.amount / (tx.oldbalanceOrg + 1)
    if drain_ratio > 0.15 and has_risk_signal:
        bonus += 0.15
 
    # Vaciado total de cuenta: aplica a cualquier tipo de drenaje
    if tx.oldbalanceOrg > 0 and tx.newbalanceOrig == 0 and tx.type.value in drain_types:
        bonus += 0.25
 
    # Discrepancia entre amount y cambio real de balance origen
    # Solo aplica a operaciones de salida para evitar falsos positivos en CASH_IN
    if tx.type.value in drain_types:
        expected_change_orig = tx.amount
        actual_change_orig   = abs(tx.oldbalanceOrg - tx.newbalanceOrig)
        discrepancy_ratio    = abs(expected_change_orig - actual_change_orig) / (tx.amount + 1)
        if discrepancy_ratio > 0.5:
            bonus += 0.25
 
    # Cap: el bonus nunca puede mover el score más de 0.75
    bonus = min(bonus, 0.75)
 
    score_final = min(score_ml + bonus, 1.0)
    return round(score_final, 4)
 
 
# ============================================================
# FEATURES R1
# ============================================================
def build_features_r1(tx: Transaction) -> pd.DataFrame:
    return pd.DataFrame([{
        "amount":            tx.amount,
        "oldbalanceOrg":     tx.oldbalanceOrg,
        "newbalanceOrig":    tx.newbalanceOrig,
        "oldbalanceDest":    tx.oldbalanceDest,
        "newbalanceDest":    tx.newbalanceDest,
        "type":              tx.type.value,
        "merchant_category": tx.merchant_category,
        "ip_country":        tx.ip_country,
    }])
 
 
# ============================================================
# FEATURES R2
# ============================================================
def build_features_r2(tx: Transaction) -> pd.DataFrame:
    balance_error_orig   = (tx.oldbalanceOrg - tx.amount) - tx.newbalanceOrig
    balance_error_dest   = (tx.oldbalanceDest + tx.amount) - tx.newbalanceDest
    drain_ratio_orig     = tx.amount / (tx.oldbalanceOrg + 1)
    dest_received_ratio  = (tx.newbalanceDest - tx.oldbalanceDest) / (tx.amount + 1)
    amount_to_orig_ratio = tx.amount / (tx.oldbalanceOrg + 1)
    both_orig_zero       = 1 if (tx.oldbalanceOrg == 0 and tx.newbalanceOrig == 0) else 0
    both_balances_zero   = 1 if (tx.oldbalanceOrg == 0 and tx.oldbalanceDest == 0) else 0
 
    hour     = tx.step % 24
    hour_sin = float(np.sin(2 * np.pi * hour / 24))
    hour_cos = float(np.cos(2 * np.pi * hour / 24))
 
    return pd.DataFrame([{
        "amount":               tx.amount,
        "oldbalanceOrg":        tx.oldbalanceOrg,
        "newbalanceOrig":       tx.newbalanceOrig,
        "oldbalanceDest":       tx.oldbalanceDest,
        "newbalanceDest":       tx.newbalanceDest,
        "balance_error_dest":   balance_error_dest,
        "drain_ratio_orig":     drain_ratio_orig,
        "dest_received_ratio":  dest_received_ratio,
        "amount_to_orig_ratio": amount_to_orig_ratio,
        "both_orig_zero":       both_orig_zero,
        "both_balances_zero":   both_balances_zero,
        "hour_sin":             hour_sin,
        "hour_cos":             hour_cos,
        "type":                 tx.type.value,
    }])
 
 
# ============================================================
# SCORING
# ============================================================
def score_transaction(tx: Transaction) -> tuple[float, RiskLevel]:
    if pipeline is None:
        return 0.0, RiskLevel.low
 
    if MODEL_VERSION == "r2":
        df_tx = build_features_r2(tx)
    else:
        df_tx = build_features_r1(tx)
 
    score_ml = float(pipeline.predict_proba(df_tx)[0][1])
    print(f"🔍 [{tx.transaction_id}] Score ML puro: {score_ml:.4f}")      # ← AÑADE
    score_final = apply_bonus_rules(tx, score_ml)
    print(f"🔍 [{tx.transaction_id}] Score final (con bonus): {score_final:.4f}")  # ← AÑADE
 
    if score_final >= 0.80:
        risk = RiskLevel.high
    elif score_final >= 0.30:
        risk = RiskLevel.medium
    else:
        risk = RiskLevel.low
 
    return score_final, risk
 
 
def apply_client_history_bonus(fraud_rate: float, total_transactions: int) -> float:
    """Bonus basado en historial del cliente consultado de Supabase."""
    bonus = 0.0
 
    if fraud_rate > 0.5:
        bonus += 0.25
    elif fraud_rate > 0.2:
        bonus += 0.15
    elif fraud_rate > 0.0:
        bonus += 0.08
 
    if total_transactions <= 3:
        bonus += 0.05
 
    return bonus
 
 
# ============================================================
# DECISION
# ============================================================
def decision_from_score(score: float) -> Decision:
    if score >= 0.80:
        return Decision.block
    elif score >= 0.30:
        return Decision.review
    else:
        return Decision.allow