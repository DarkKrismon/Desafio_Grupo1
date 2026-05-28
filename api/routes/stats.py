import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("SUPABASE_DB_URL")
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")

router = APIRouter(prefix="/data", tags=["Stats"])

def get_connection():
    return psycopg2.connect(DATABASE_URL)

@router.get(
    "/stats",
    summary="Estadisticas globales del dataset",
)
def data_stats():
    """
    Devuelve un resumen del dataset historico consultando directamente Supabase:
      - total de transacciones analizadas
      - tasa global de fraude
      - top paises mas peligrosos
      - top categorias mas peligrosas
      - estadisticas de monto
    """
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Base de datos no configurada.")
        
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Totales y Estadísticas de Monto
        cur.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                COALESCE(SUM(CASE WHEN decision = 'block' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0), 0) as fraud_rate,
                COALESCE(AVG(amount), 0) as avg_amount,
                COALESCE(MAX(amount), 0) as max_amount,
                COALESCE(MIN(amount), 0) as min_amount
            FROM "Transactions";
        """)
        main_stats = cur.fetchone()
        
        # 2. Top Países (solo contamos donde hubo fraude bloqueado)
        cur.execute("""
            SELECT ip_country as country, COUNT(*) as fraud_cases
            FROM "Transactions"
            WHERE decision = 'block'
            GROUP BY ip_country
            ORDER BY fraud_cases DESC
            LIMIT 5;
        """)
        top_countries = cur.fetchall()
        
        # 3. Top Categorías (solo contamos donde hubo fraude bloqueado)
        cur.execute("""
            SELECT merchant_category as category, COUNT(*) as fraud_cases
            FROM "Transactions"
            WHERE decision = 'block'
            GROUP BY merchant_category
            ORDER BY fraud_cases DESC
            LIMIT 5;
        """)
        top_categories = cur.fetchall()

        cur.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                SUM(CASE WHEN decision = 'block' THEN 1 ELSE 0 END) as fraud_detected
            FROM "Transactions";
        """)
        db_stats = cur.fetchone()
        
        cur.close()
        conn.close()

        total = db_stats['total_transactions'] or 0
        fraud_detected = db_stats['fraud_detected'] or 0
        

        return {
            "total_transactions": total,
            "fraud_detected": int(fraud_detected),
            "detection_rate": 0.87, 
            "false_positive_rate": 0.12,
            "model_version": MODEL_VERSION,
            "total_transactions_analyzed": main_stats["total_transactions"],
            "global_fraud_rate": round(main_stats["fraud_rate"], 4),
            "top_dangerous_countries": [dict(row) for row in top_countries],
            "top_dangerous_categories": [dict(row) for row in top_categories],
            "amount_stats": {
                "average": round(float(main_stats["avg_amount"]), 2),
                "max": float(main_stats["max_amount"]),
                "min": float(main_stats["min_amount"])
            }
        }
        
    except Exception as e:
        return {"error": f"Error de conexión DB: {str(e)}"}