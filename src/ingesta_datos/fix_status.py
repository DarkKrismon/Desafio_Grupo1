import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("SUPABASE_DB_URL")

def fix_transaction_status():
    if not DATABASE_URL:
        print("❌ ERROR: SUPABASE_DB_URL no configurada.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
            UPDATE "Transactions"
            SET status = CASE
                WHEN decision = 'block' THEN 'reviewed'
                WHEN decision = 'allow' THEN 'reviewed'
                WHEN decision = 'review' THEN 'pending'
                ELSE 'reviewed'
            END
            WHERE status = 'pending'
        """)

        updated = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()

        print(f"✅ {updated} transacciones actualizadas correctamente.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_transaction_status()