"""
src/data_loader.py
==================
Carga el dataset sintetico una sola vez al arrancar y calcula
estadisticas reales que la heuristica de scoring usa.

Cuando llegue el modelo ML entrenado, este modulo seguira siendo util
para mostrar stats en /data/stats y para feature engineering.
"""

from pathlib import Path
from typing import Optional

import pandas as pd


# ============================================================
# CONFIGURACION
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "synthetic_fin_data_CLEAN.csv"


# ============================================================
# CARGA UNICA (lazy: solo si se llama)
# ============================================================
_df: Optional[pd.DataFrame] = None
_stats: Optional[dict] = None


def load_dataset() -> pd.DataFrame:
    """Carga el CSV una sola vez y lo cachea en memoria."""
    global _df
    if _df is None:
        if not DATA_PATH.exists():
            raise FileNotFoundError(
                f"No se encuentra el dataset en {DATA_PATH}. "
                "Verifica que data/synthetic_fin_data_CLEAN.csv existe."
            )
        _df = pd.read_csv(DATA_PATH)
        print(f"[data_loader] Dataset cargado: {len(_df):,} transacciones")
    return _df


def compute_stats() -> dict:
    """
    Calcula estadisticas reales del dataset:
      - tasa de fraude por pais
      - tasa de fraude por categoria
      - tasa de fraude por tipo de transaccion
      - monto medio y umbral de "monto alto" (percentil 95)
      - tasa global de fraude
    """
    global _stats
    if _stats is not None:
        return _stats

    df = load_dataset()

    # Tasa de fraude por pais (solo paises con >= 10 transacciones, evitar ruido)
    country_counts = df.groupby("ip_country").size()
    valid_countries = country_counts[country_counts >= 10].index
    fraud_by_country = (
        df[df["ip_country"].isin(valid_countries)]
        .groupby("ip_country")["isFraud"]
        .mean()
        .to_dict()
    )

    # Tasa de fraude por categoria
    fraud_by_category = df.groupby("merchant_category")["isFraud"].mean().to_dict()

    # Tasa de fraude por tipo de transaccion
    fraud_by_type = df.groupby("type")["isFraud"].mean().to_dict()

    # Stats de monto
    avg_amount = float(df["amount"].mean())
    median_amount = float(df["amount"].median())
    high_amount_threshold = float(df["amount"].quantile(0.95))

    # Tasa global
    global_fraud_rate = float(df["isFraud"].mean())

    _stats = {
        "fraud_by_country": fraud_by_country,
        "fraud_by_category": fraud_by_category,
        "fraud_by_type": fraud_by_type,
        "avg_amount": avg_amount,
        "median_amount": median_amount,
        "high_amount_threshold": high_amount_threshold,
        "global_fraud_rate": global_fraud_rate,
        "total_transactions": len(df),
        "total_fraud_cases": int(df["isFraud"].sum()),
    }

    print(f"[data_loader] Stats calculadas:")
    print(f"  - Tasa global de fraude: {global_fraud_rate:.2%}")
    print(f"  - Paises analizados: {len(fraud_by_country)}")
    print(f"  - Categorias: {len(fraud_by_category)}")
    print(f"  - Umbral monto alto (p95): {high_amount_threshold:,.2f} EUR")

    return _stats


def get_summary_for_api() -> dict:
    """
    Devuelve un resumen 'safe' del dataset para exponer por la API.
    Filtra info sensible y limita listas.
    """
    stats = compute_stats()

    # Top 10 paises mas peligrosos
    top_risky_countries = sorted(
        stats["fraud_by_country"].items(),
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    # Top categorias mas peligrosas
    top_risky_categories = sorted(
        stats["fraud_by_category"].items(),
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    return {
        "total_transactions": stats["total_transactions"],
        "total_fraud_cases": stats["total_fraud_cases"],
        "global_fraud_rate": round(stats["global_fraud_rate"], 4),
        "avg_amount_eur": round(stats["avg_amount"], 2),
        "median_amount_eur": round(stats["median_amount"], 2),
        "high_amount_threshold_eur": round(stats["high_amount_threshold"], 2),
        "top_risky_countries": [
            {"country": c, "fraud_rate": round(r, 4)} for c, r in top_risky_countries
        ],
        "top_risky_categories": [
            {"category": c, "fraud_rate": round(r, 4)} for c, r in top_risky_categories
        ],
    }
