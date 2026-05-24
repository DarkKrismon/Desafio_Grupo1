"""
Lógica de perfil de cliente para el Client Profile Modal.

Esta capa NO sabe nada de HTTP. Lee el dataset histórico y devuelve
estadísticas agregadas + transacciones recientes + flags cualitativas.

La función pública `build_client_profile()` es la que llama el endpoint.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


# ============================================================
# Carga del dataset (singleton perezoso)
# ============================================================
_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "synthetic_fin_data_CLEAN.csv"
_df_cache: Optional[pd.DataFrame] = None


def _load_dataset() -> pd.DataFrame:
    """Carga el CSV una sola vez y lo cachea en memoria.

    Si el dataset cambia (nueva ronda de Red Team), reinicia la app.
    """
    global _df_cache
    if _df_cache is None:
        if not _DATA_PATH.exists():
            raise FileNotFoundError(
                f"Dataset no encontrado en {_DATA_PATH}. "
                "Verifica que data/synthetic_fin_data_CLEAN.csv existe."
            )
        _df_cache = pd.read_csv(_DATA_PATH)
    return _df_cache


# ============================================================
# Cálculo de flags cualitativas
# ============================================================
def _compute_risk_flags(client_df: pd.DataFrame, global_df: pd.DataFrame) -> list[str]:
    """Deriva banderas cualitativas legibles para el analista.

    Se calculan sobre el histórico del cliente. NO sustituyen al score del
    modelo: son señales rápidas que el analista ve en el modal.
    """
    flags: list[str] = []
    n = len(client_df)

    # Cliente nuevo: muy pocas transacciones
    if n <= 3:
        flags.append("new_client")

    # Marcado como fraude alguna vez en el histórico
    if "isFraud" in client_df.columns and client_df["isFraud"].sum() > 0:
        flags.append("previously_flagged")

    # Uso frecuente de CASH_OUT (típico patrón de cash-out fraud en PaySim)
    if "type" in client_df.columns and n > 0:
        cash_out_ratio = (client_df["type"] == "CASH_OUT").mean()
        if cash_out_ratio > 0.5:
            flags.append("frequent_cash_out")

    # Velocidad alta: muchas transacciones en pocos steps
    if "step" in client_df.columns and n >= 5:
        span = client_df["step"].max() - client_df["step"].min()
        if span > 0 and (n / span) > 0.5:
            flags.append("high_velocity")

    # Importe inusual: alguna transacción muy por encima de su media
    if "amount" in client_df.columns and n >= 3:
        mean_amt = client_df["amount"].mean()
        max_amt = client_df["amount"].max()
        if mean_amt > 0 and max_amt > 5 * mean_amt:
            flags.append("unusual_amount")

    # Concentración: gran parte del volumen va a un solo destinatario
    if "nameDest" in client_df.columns and "amount" in client_df.columns and n >= 5:
        by_dest = client_df.groupby("nameDest")["amount"].sum()
        if by_dest.sum() > 0:
            top_share = by_dest.max() / by_dest.sum()
            if top_share > 0.7:
                flags.append("concentrated_destination")

    return flags


# ============================================================
# Función pública
# ============================================================
def build_client_profile(
    name_orig: str,
    recent_limit: int = 20,
    recent_offset: int = 0,
) -> Optional[dict]:
    """Construye el perfil completo del cliente o devuelve None si no existe.

    Args:
        name_orig: ID del cliente (columna nameOrig del dataset).
        recent_limit: número de transacciones recientes a devolver.
        recent_offset: offset para paginar la lista de transacciones recientes.

    Returns:
        Diccionario con la estructura del ClientProfileResponse, o None si
        no se encuentra ninguna transacción para este cliente.
    """
    df = _load_dataset()

    client_df = df[df["nameOrig"] == name_orig]
    if client_df.empty:
        return None

    # Ordenamos por step (proxy temporal en PaySim) descendente
    client_df = client_df.sort_values("step", ascending=False)

    n = len(client_df)
    total_volume = float(client_df["amount"].sum())
    avg_amount = float(client_df["amount"].mean())
    max_amount = float(client_df["amount"].max())

    # Fraud rate histórico (si el dataset incluye la etiqueta)
    if "isFraud" in client_df.columns:
        fraud_rate = float(client_df["isFraud"].mean())
        fraud_flag_col = "isFraud"
    else:
        fraud_rate = 0.0
        fraud_flag_col = None

    # Tipo más usado
    most_used_type = (
        client_df["type"].mode().iloc[0] if "type" in client_df.columns and not client_df["type"].mode().empty else None
    )

    # Counterparties distintas
    distinct_counterparties = int(client_df["nameDest"].nunique()) if "nameDest" in client_df.columns else 0

    # Transacciones recientes (paginadas)
    recent_slice = client_df.iloc[recent_offset : recent_offset + recent_limit]
    recent_transactions = []
    for idx, row in recent_slice.iterrows():
        recent_transactions.append(
            {
                "transaction_id": f"TXN-{idx}",
                "timestamp": None,  # PaySim no tiene timestamp real, sólo step
                "step": int(row["step"]) if "step" in row else None,
                "type": str(row["type"]) if "type" in row else "UNKNOWN",
                "amount": float(row["amount"]),
                "nameDest": str(row["nameDest"]) if "nameDest" in row else "",
                "oldbalanceOrg": float(row.get("oldbalanceOrg", 0.0)),
                "newbalanceOrig": float(row.get("newbalanceOrig", 0.0)),
                "is_flagged_fraud": bool(row[fraud_flag_col]) if fraud_flag_col else False,
            }
        )

    risk_flags = _compute_risk_flags(client_df, df)

    return {
        "client_id": name_orig,
        "stats": {
            "total_transactions": n,
            "total_volume": round(total_volume, 2),
            "avg_amount": round(avg_amount, 2),
            "max_amount": round(max_amount, 2),
            "first_seen": None,  # PaySim no tiene fecha real
            "last_seen": None,
            "fraud_rate_historical": round(fraud_rate, 4),
            "distinct_counterparties": distinct_counterparties,
            "most_used_type": most_used_type,
        },
        "recent_transactions": recent_transactions,
        "risk_flags": risk_flags,
    }
