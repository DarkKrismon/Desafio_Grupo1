import os
import uuid
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("SUPABASE_DB_URL")

connection_pool = pool.SimpleConnectionPool(1, 10, DATABASE_URL)

def get_connection():
    return connection_pool.getconn()

def release_connection(conn):
    connection_pool.putconn(conn)

def save_transaction(tx_data: dict):
    # Inicializamos conn a None para que el bloque finally pueda comprobar
    # si la conexión llegó a abrirse antes de intentar liberarla
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # ==========================================
        # 1. UPSERT: Crear clientes si no existen
        # ==========================================
        now_utc = datetime.now(timezone.utc)
        
        # Insertar cliente ORIGEN (ignorando si ya existe)
        client_orig = str(tx_data.get("nameOrig", "UNKNOWN"))
        cur.execute("""
            INSERT INTO "ClientProfiles" (client_id, total_transactions, total_amount, fraud_flags, last_seen, risk_profile, "createdAt", "updatedAt")
            VALUES (%s, 0, 0.0, 0, %s, 'low', %s, %s)
            ON CONFLICT (client_id) DO NOTHING;
        """, (client_orig, now_utc, now_utc, now_utc))

        # Insertar cliente DESTINO (solo si es un cliente 'C' y no un mercader 'M')
        client_dest = str(tx_data.get("nameDest", "UNKNOWN"))
        if client_dest.startswith("C"):
            cur.execute("""
                INSERT INTO "ClientProfiles" (client_id, total_transactions, total_amount, fraud_flags, last_seen, risk_profile, "createdAt", "updatedAt")
                VALUES (%s, 0, 0.0, 0, %s, 'low', %s, %s)
                ON CONFLICT (client_id) DO NOTHING;
            """, (client_dest, now_utc, now_utc, now_utc))

        # ==========================================
        # 2. Inserción normal de la transacción
        # ==========================================
        query = """
            INSERT INTO "Transactions" (
                "transaction_id", "amount", "type", "nameOrig", "nameDest",
                "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest",
                "ip_country", "merchant_category", "fraud_probability",
                "risk_level", "decision", "status", "timestamp", "createdAt", "updatedAt", "step"
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        valores = (
            str(tx_data.get("transaction_id", str(uuid.uuid4()))),
            float(tx_data.get("amount", 0.0)),
            str(tx_data.get("type", "UNKNOWN")),
            client_orig,
            client_dest,
            float(tx_data.get("oldbalanceOrg", 0.0)),
            float(tx_data.get("newbalanceOrig", 0.0)),
            float(tx_data.get("oldbalanceDest", 0.0)),
            float(tx_data.get("newbalanceDest", 0.0)),
            str(tx_data.get("ip_country", "UNKNOWN")),
            str(tx_data.get("merchant_category", "UNKNOWN")),
            float(tx_data.get("fraud_probability", 0.0)),
            str(tx_data.get("risk_level", "low")),
            str(tx_data.get("decision", "allow")),
            "pending",
            now_utc,
            now_utc,
            now_utc,
            int(tx_data.get("step", 1))
        )
        
        cur.execute(query, valores)
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"❌ Error crítico de base de datos en save_transaction: {e}")
    finally:
        # Devolvemos la conexión al pool en lugar de destruirla
        # Esto evita crear una conexión nueva en cada llamada y mejora el rendimiento
        if conn:
            release_connection(conn)

def get_transactions():
    # Solo como fallback. Limitado a 50 para no colapsar la memoria.
    # Inicializamos conn a None para que el bloque finally pueda comprobar
    # si la conexión llegó a abrirse antes de intentar liberarla
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM "Transactions" ORDER BY "timestamp" DESC LIMIT 50;')
        rows = cur.fetchall()
        cur.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Error de base de datos en get_transactions: {e}")
        return []
    finally:
        # Devolvemos la conexión al pool en lugar de destruirla
        # Esto evita crear una conexión nueva en cada llamada y mejora el rendimiento
        if conn:
            release_connection(conn)

from psycopg2.extras import RealDictCursor

def get_pending_queue(limit: int = 50, risk_level: str = None):
    """Obtiene de Supabase las transacciones que están pendientes de revisión."""
    # Inicializamos conn a None para que el bloque finally pueda comprobar
    # si la conexión llegó a abrirse antes de intentar liberarla
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = 'SELECT * FROM "Transactions" WHERE status = %s'
        params = ['pending']
        
        if risk_level:
            query += ' AND risk_level = %s'
            # Convertimos el Enum a string si es necesario
            params.append(risk_level.value if hasattr(risk_level, 'value') else risk_level)
            
        query += ' ORDER BY timestamp DESC LIMIT %s'
        params.append(limit)
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        # Consultamos el conteo total para la paginación del frontend
        count_query = 'SELECT COUNT(*) FROM "Transactions" WHERE status = %s'
        count_params = ['pending']
        if risk_level:
            count_query += ' AND risk_level = %s'
            count_params.append(risk_level.value if hasattr(risk_level, 'value') else risk_level)
            
        cur.execute(count_query, count_params)
        total_pending = cur.fetchone()['count']
        
        cur.close()
        
        return total_pending, [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Error en DB leyendo la cola: {e}")
        return 0, []
    finally:
        # Devolvemos la conexión al pool en lugar de destruirla
        # Esto evita crear una conexión nueva en cada llamada y mejora el rendimiento
        if conn:
            release_connection(conn)

def resolve_case(transaction_id: str, decision: str, analyst_id: str):
    """Actualiza una transacción en Supabase marcándola como revisada por un humano."""
    # Inicializamos conn a None para que el bloque finally pueda comprobar
    # si la conexión llegó a abrirse antes de intentar liberarla
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Cambiamos el estado a 'reviewed' y guardamos la decisión final del analista
        cur.execute(
            'UPDATE "Transactions" SET status = %s, decision = %s, "updatedAt" = %s WHERE transaction_id = %s',
            ('reviewed', decision, datetime.now(timezone.utc), transaction_id)
        )
        
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"❌ Error actualizando estado en DB: {e}")
    finally:
        # Devolvemos la conexión al pool en lugar de destruirla
        # Esto evita crear una conexión nueva en cada llamada y mejora el rendimiento
        if conn:
            release_connection(conn)