import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("SUPABASE_DB_URL")

router = APIRouter()

def get_connection():
    return psycopg2.connect(DATABASE_URL)

@router.get("/")
def get_general_stats():
    """
    Devuelve las estadísticas delegando el esfuerzo computacional a Supabase.
    """
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                SUM(CASE WHEN decision = 'block' THEN 1 ELSE 0 END) as blocked_transactions,
                SUM(CASE WHEN decision = 'allow' THEN 1 ELSE 0 END) as allowed_transactions,
                COALESCE(SUM(amount), 0) as total_volume
            FROM "Transactions";
        """)
        stats = cur.fetchone()
        
        cur.close()
        conn.close()
        
        total = stats['total_transactions']
        blocked = stats['blocked_transactions']
        allowed = stats['allowed_transactions']
        
        fraud_rate = (blocked / total) if total > 0 else 0.0
        
        return {
            "total_transactions": total,
            "fraud_rate": round(fraud_rate, 4),
            "blocked_transactions": blocked,
            "allowed_transactions": allowed,
            "total_volume": float(stats['total_volume'])
        }
        
    except Exception as e:
        return {"error": f"Error de conexión con la base de datos: {str(e)}"}