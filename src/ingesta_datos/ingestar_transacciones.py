import os
import uuid
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

# Cargamos credenciales
load_dotenv()
DATABASE_URL = os.getenv("SUPABASE_DB_URL")

def ingestar_transacciones():
    if not DATABASE_URL:
        print("❌ ERROR: SUPABASE_DB_URL no configurada.")
        return

    # IMPORTANTE: Pon la ruta exacta a tu CSV
    archivo_csv = r"C:\Users\jrtm2\Desktop\Desafio\Desafio_Grupo1\data\synthetic_fin_data_CLEAN.csv"
    
    if not os.path.exists(archivo_csv):
        print(f"❌ ERROR: No se encuentra el archivo en {archivo_csv}.")
        return

    print("Conectando a la base de datos de producción...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Opcional: Si quieres asegurarte de que la tabla está vacía antes de empezar
        # cur.execute('DELETE FROM "Transactions";')
        # conn.commit()

        query = """
            INSERT INTO "Transactions" (
                "transaction_id", "amount", "type", "nameOrig", "nameDest", 
                "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest", 
                "ip_country", "merchant_category", "fraud_probability", 
                "risk_level", "decision", "status", "timestamp", "createdAt", "updatedAt", "step"
            ) VALUES %s
        """

        base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        
        chunk_size = 10000
        total_procesado = 0

        print(f"🚀 Iniciando inyección por lotes de {chunk_size} filas...")

        # Leemos el CSV en trozos para no reventar la RAM
        for chunk in pd.read_csv(archivo_csv, chunksize=chunk_size):
            valores = []
            
            # Limpiamos posibles valores nulos en textos
            chunk['ip_country'] = chunk['ip_country'].fillna('UNKNOWN')
            chunk['merchant_category'] = chunk['merchant_category'].fillna('UNKNOWN')

            for _, row in chunk.iterrows():
                is_fraud = int(row['isFraud'])
                
                # Traducimos lógica de ML a lógica de negocio (BD)
                risk = 'high' if is_fraud == 1 else 'low'
                dec = 'block' if is_fraud == 1 else 'allow'
                timestamp_real = base_date + timedelta(hours=int(row['step']))

                valores.append((
                    str(uuid.uuid4()),                  # transaction_id
                    float(row['amount']),               # amount
                    str(row['type']),                   # type
                    str(row['nameOrig']),               # nameOrig
                    str(row['nameDest']),               # nameDest
                    float(row['oldbalanceOrg']),        # oldbalanceOrg
                    float(row['newbalanceOrig']),       # newbalanceOrig
                    float(row['oldbalanceDest']),       # oldbalanceDest
                    float(row['newbalanceDest']),       # newbalanceDest
                    str(row['ip_country']),             # ip_country
                    str(row['merchant_category']),      # merchant_category
                    float(is_fraud),                    # fraud_probability (1.0 o 0.0)
                    risk,                               # risk_level
                    dec,                                # decision
                    'pending',                        # status
                    timestamp_real,                     # timestamp
                    now_utc,                            # createdAt
                    now_utc,                            # updatedAt
                    int(row['step'])                    # step
                ))
            
            # Insertamos el bloque
            execute_values(cur, query, valores, page_size=1000)
            conn.commit()
            
            total_procesado += len(chunk)
            print(f"✅ Procesadas e inyectadas {total_procesado} transacciones...")

        cur.close()
        conn.close()
        print("🎉 INGESTA MASIVA FINALIZADA. La tabla de Transacciones está operativa.")

    except Exception as e:
        print(f"❌ Error crítico durante la inyección de transacciones: {e}")

if __name__ == "__main__":
    ingestar_transacciones()