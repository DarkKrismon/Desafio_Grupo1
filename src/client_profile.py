"""
Lógica de perfil de cliente conectada directamente a Supabase.
"""
from __future__ import annotations
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional

# Usamos os.getenv para leer del .env sin hardcodear credenciales
DATABASE_URL = os.getenv("SUPABASE_DB_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def _compute_risk_flags(stats: dict) -> list[str]:
    flags: list[str] = []
    n = stats["total_transactions"]

    if n <= 3:
        flags.append("new_client")
    if stats["fraud_rate_historical"] > 0:
        flags.append("previously_flagged")
    if stats["most_used_type"] == "CASH_OUT":
        flags.append("frequent_cash_out")
    if n >= 3 and stats["avg_amount"] > 0 and stats["max_amount"] > 5 * stats["avg_amount"]:
        flags.append("unusual_amount")

    return flags

def build_client_profile(name_orig: str, recent_limit: int = 20, recent_offset: int = 0) -> Optional[dict]:
    if not DATABASE_URL:
        print("❌ ERROR: SUPABASE_DB_URL no está configurada.")
        return None

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 1. Estadísticas agregadas
        stats_query = """
            SELECT 
                COUNT(*) as total_transactions,
                COALESCE(SUM(amount), 0) as total_volume,
                COALESCE(AVG(amount), 0) as avg_amount,
                COALESCE(MAX(amount), 0) as max_amount,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen,
                COUNT(DISTINCT "nameDest") as distinct_counterparties,
                MODE() WITHIN GROUP (ORDER BY type) as most_used_type,
                COALESCE(SUM(CASE WHEN decision = 'block' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0), 0) as fraud_rate_historical
            FROM "Transactions"
            WHERE "nameOrig" = %s;
        """
        cur.execute(stats_query, (name_orig,))
        stats = cur.fetchone()

        if stats["total_transactions"] == 0:
            cur.close()
            conn.close()
            return None

        # 2. Transacciones recientes
        recent_query = """
            SELECT transaction_id, timestamp, step, type, amount, "nameDest", "oldbalanceOrg", "newbalanceOrig", decision
            FROM "Transactions"
            WHERE "nameOrig" = %s
            ORDER BY timestamp DESC NULLS LAST, step DESC
            LIMIT %s OFFSET %s;
        """
        cur.execute(recent_query, (name_orig, recent_limit, recent_offset))
        recent_rows = cur.fetchall()

        cur.close()
        conn.close()

        recent_transactions = [{
            "transaction_id": row["transaction_id"],
            "timestamp": row["timestamp"],
            "step": row["step"],
            "type": str(row["type"]),
            "amount": float(row["amount"]),
            "nameDest": str(row["nameDest"]),
            "oldbalanceOrg": float(row["oldbalanceOrg"]),
            "newbalanceOrig": float(row["newbalanceOrig"]),
            "is_flagged_fraud": row["decision"] == "block"
        } for row in recent_rows]

        return {
            "client_id": name_orig,
            "stats": {
                "total_transactions": int(stats["total_transactions"]),
                "total_volume": round(float(stats["total_volume"]), 2),
                "avg_amount": round(float(stats["avg_amount"]), 2),
                "max_amount": round(float(stats["max_amount"]), 2),
                "first_seen": stats["first_seen"],
                "last_seen": stats["last_seen"],
                "fraud_rate_historical": round(float(stats["fraud_rate_historical"]), 4),
                "distinct_counterparties": int(stats["distinct_counterparties"]),
                "most_used_type": str(stats["most_used_type"]) if stats["most_used_type"] else None,
            },
            "recent_transactions": recent_transactions,
            "risk_flags": _compute_risk_flags(stats),
        }

    except Exception as e:
        print(f"❌ Error DB: {e}")
        return None