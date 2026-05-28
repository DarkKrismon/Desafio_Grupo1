import psycopg2
import os
from dotenv import load_dotenv

# 1. Cargamos las variables ocultas del archivo .env
load_dotenv()

# 2. Leemos la URL de forma segura
DATABASE_URL = os.getenv("SUPABASE_DB_URL")

def explorar_base_de_datos():
    if not DATABASE_URL:
        print("❌ ERROR: No se ha encontrado SUPABASE_DB_URL en el archivo .env")
        return

    print("Conectando a Supabase de forma segura...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Sacamos los nombres de todas las tablas
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tablas = cur.fetchall()
        print("\n=== TABLAS ENCONTRADAS ===")
        for t in tablas:
            print(f"- {t[0]}")

        # Miramos las columnas de cada tabla
        for t in tablas:
            nombre_tabla = t[0]
            cur.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{nombre_tabla}'
            """)
            columnas = cur.fetchall()
            print(f"\n=== COLUMNAS DE LA TABLA '{nombre_tabla}' ===")
            for c in columnas:
                print(f"  > {c[0]} (Tipo: {c[1]})")

        cur.close()
        conn.close()
        print("\nExploración finalizada con éxito.")

    except Exception as e:
        print(f"Error al conectar o consultar: {e}")

if __name__ == "__main__":
    explorar_base_de_datos()