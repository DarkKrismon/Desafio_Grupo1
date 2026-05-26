import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("SUPABASE_DB_URL")
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")

# Prefijo exacto que pide el equipo de Full Stack
router = APIRouter(prefix="/data", tags=["Stats"])

def get_connection():
    return psycopg2.connect(DATABASE_URL)

@router.get("/stats")
def get_global_stats():
    """
    Devuelve estadísticas globales combinando datos en tiempo real de Supabase 
    con las métricas de rendimiento estáticas del modelo.
    """
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Leemos los números reales de lo que hay inyectado en producción
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
        
        # En producción sin etiquetas perfectas (ground truth), 
        # el TPR (detection rate) y FPR se sacan del rendimiento en validación.
        return {
            "round": 1 if "r1" in MODEL_VERSION.lower() else 2,
            "total_transactions": total,
            "fraud_detected": int(fraud_detected),
            "detection_rate": 0.87, 
            "false_positive_rate": 0.12,
            "model_version": MODEL_VERSION
        }
        
    except Exception as e:
        return {"error": f"Error de conexión DB: {str(e)}"}