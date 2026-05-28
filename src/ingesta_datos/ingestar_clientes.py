import json
import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Cargamos la conexión a Supabase
load_dotenv()
DATABASE_URL = os.getenv("SUPABASE_DB_URL")

def ingestar_clientes():
    if not DATABASE_URL:
        print("❌ ERROR: No se ha encontrado SUPABASE_DB_URL en el archivo .env")
        return

    # IMPORTANTE: Apuntamos al NUEVO archivo generado por tu compañero
    archivo_json = r"C:\Users\jrtm2\Desktop\Desafio\Desafio_Grupo1\data\customer_db_clean.json"
    
    try:
        with open(archivo_json, "r") as f:
            clientes = json.load(f)
        print(f"📦 Se han cargado {len(clientes)} clientes del archivo JSON limpio.")
    except FileNotFoundError:
        print(f"❌ ERROR: No se encuentra el archivo {archivo_json}.")
        return

    try:
        print("Conectando a la base de datos de producción...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("🧹 Limpiando la tabla 'ClientProfiles' antigua...")
        cur.execute('DELETE FROM "ClientProfiles";')

        # Consulta limpia con todas las columnas exactas que esperan las de Full Stack
        query = """
            INSERT INTO "ClientProfiles" (
                client_id, 
                total_transactions, 
                total_amount, 
                fraud_flags, 
                last_seen, 
                risk_profile, 
                "createdAt", 
                "updatedAt"
            )
            VALUES %s
        """

        # Extraemos los datos directamente, sin inventar ni transformar nada
        valores = [
            (
                c["client_id"],
                c["total_transactions"],
                c["total_amount"],
                c["fraud_flags"],
                c["last_seen"],
                c["risk_profile"],
                c["createdAt"],
                c["updatedAt"]
            )
            for c in clientes
        ]

        print("🚀 Iniciando inyección masiva (Bulk Insert)...")
        execute_values(cur, query, valores, page_size=1000)
        
        conn.commit()

        cur.close()
        conn.close()
        print("✅ Ingesta completada con éxito. La base de datos de clientes está perfectamente sincronizada.")

    except Exception as e:
        print(f"❌ Error crítico durante la ingesta: {e}")

if __name__ == "__main__":
    ingestar_clientes()