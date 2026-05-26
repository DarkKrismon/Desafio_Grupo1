from fastapi import APIRouter
from src.storage import get_connection

router = APIRouter(prefix="/meta", tags=["Meta"])

@router.get("/health")
def health_check():
    """Endpoint para comprobar que la API y la Base de Datos están vivas"""
    db_status = "ok"
    try:
        conn = get_connection()
        conn.close()
    except Exception:
        db_status = "error_db"

    return {
        "status": "up",
        "database": db_status,
        "version": "1.0.0"
    }