import psycopg2
import os
from dotenv import load_dotenv

# Cargamos la URL del búnker
load_dotenv()
DATABASE_URL = os.getenv("SUPABASE_DB_URL")

def purgar_transacciones():
    if not DATABASE_URL:
        print("❌ ERROR: No se ha encontrado SUPABASE_DB_URL en el archivo .env")
        return

    print("⚠️ ATENCIÓN: Te estás conectando a la base de datos de producción.")
    confirmacion = input("¿Estás 100% seguro de que quieres borrar TODAS las transacciones y decisiones? (escribe 'SI' para continuar): ")
    
    if confirmacion != "SI":
        print("Abortando operación. La base de datos está a salvo.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("Iniciando purga...")
        
        # 1. Borramos primero las decisiones de los analistas para evitar errores de claves foráneas (Foreign Keys)
        cur.execute('DELETE FROM "AnalystDecisions";')
        print("✅ Tabla 'AnalystDecisions' vaciada.")

        # 2. Ahora sí, borramos todas las transacciones
        cur.execute('DELETE FROM "Transactions";')
        print("✅ Tabla 'Transactions' vaciada.")

        # Confirmamos los cambios (si no haces commit, no se guarda el borrado)
        conn.commit()
        
        cur.close()
        conn.close()
        print("🔥 Purga completada con éxito. La base de datos está limpia y lista para el nuevo dataset.")

    except Exception as e:
        print(f"❌ Error crítico durante el borrado: {e}")

if __name__ == "__main__":
    purgar_transacciones()