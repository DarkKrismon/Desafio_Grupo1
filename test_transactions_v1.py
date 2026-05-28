"""
test_transactions_v1.py
=======================
20 transacciones de prueba para NovaPay Fraud Shield.
Cubre el rango completo de risk score (~0.10 a ~0.90).

Uso:
    Terminal 1: MODEL_VERSION=r2 uvicorn api.main:app --reload --port 8001
    Terminal 2: python test_transactions_v1.py
"""

import requests
import json
import time

# 1. ACTUALIZAR A LA IP DE AWS Y PUERTO CORRECTO
API_URL  = "http://34.229.150.136:8000/fraud/decide"
API_KEY  = "centinela-secreto-123"
HEADERS  = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

transactions = [

    # ── RIESGO MUY BAJO (~0.05-0.15) ────────────────────────────────────────
    {
        "transaction_id": "TEST-001-VERY-LOW",
        "step": 120,
        "type": "PAYMENT",
        "amount": 25.50,
        "nameOrig": "C112233445",
        "oldbalanceOrg": 2000.00,
        "newbalanceOrig": 1974.50,
        "nameDest": "M998877665",
        "oldbalanceDest": 5000.00,
        "newbalanceDest": 5025.50,
        "merchant_category": "grocery",
        "ip_country": "ES",
        "hour_of_the_day": 11
    },
    {
        "transaction_id": "TEST-002-VERY-LOW",
        "step": 200,
        "type": "PAYMENT",
        "amount": 48.00,
        "nameOrig": "C223344556",
        "oldbalanceOrg": 3500.00,
        "newbalanceOrig": 3452.00,
        "nameDest": "M112233447",
        "oldbalanceDest": 8000.00,
        "newbalanceDest": 8048.00,
        "merchant_category": "restaurant",
        "ip_country": "FR",
        "hour_of_the_day": 14
    },
    {
        "transaction_id": "TEST-003-LOW",
        "step": 310,
        "type": "PAYMENT",
        "amount": 120.00,
        "nameOrig": "C334455667",
        "oldbalanceOrg": 5000.00,
        "newbalanceOrig": 4880.00,
        "nameDest": "M223344558",
        "oldbalanceDest": 2000.00,
        "newbalanceDest": 2120.00,
        "merchant_category": "pharmacy",
        "ip_country": "DE",
        "hour_of_the_day": 10
    },

    # ── RIESGO BAJO-MEDIO (~0.20-0.35) ──────────────────────────────────────
    {
        "transaction_id": "TEST-004-LOW-MED",
        "step": 400,
        "type": "TRANSFER",
        "amount": 1500.00,
        "nameOrig": "C445566778",
        "oldbalanceOrg": 8000.00,
        "newbalanceOrig": 6500.00,
        "nameDest": "M334455669",
        "oldbalanceDest": 1000.00,
        "newbalanceDest": 2500.00,
        "merchant_category": "transport",
        "ip_country": "US",
        "hour_of_the_day": 23
    },
    {
        "transaction_id": "TEST-005-LOW-MED",
        "step": 500,
        "type": "CASH_OUT",
        "amount": 3000.00,
        "nameOrig": "C556677889",
        "oldbalanceOrg": 10000.00,
        "newbalanceOrig": 7000.00,
        "nameDest": "M445566770",
        "oldbalanceDest": 500.00,
        "newbalanceDest": 3500.00,
        "merchant_category": "fuel",
        "ip_country": "GB",
        "hour_of_the_day": 1
    },

    # ── RIESGO MEDIO (~0.40-0.55) ────────────────────────────────────────────
    {
        "transaction_id": "TEST-006-MEDIUM",
        "step": 250,
        "type": "TRANSFER",
        "amount": 9000.00,
        "nameOrig": "C667788990",
        "oldbalanceOrg": 15000.00,
        "newbalanceOrig": 6000.00,
        "nameDest": "M556677881",
        "oldbalanceDest": 200.00,
        "newbalanceDest": 9200.00,
        "merchant_category": "electronics",
        "ip_country": "US",
        "hour_of_the_day": 2
    },
    {
        "transaction_id": "TEST-007-MEDIUM",
        "step": 360,
        "type": "CASH_OUT",
        "amount": 5000.00,
        "nameOrig": "C778899001",
        "oldbalanceOrg": 7000.00,
        "newbalanceOrig": 2000.00,
        "nameDest": "M667788992",
        "oldbalanceDest": 100.00,
        "newbalanceDest": 5100.00,
        "merchant_category": "unknown",
        "ip_country": "CN",
        "hour_of_the_day": 3
    },
    {
        "transaction_id": "TEST-008-MEDIUM",
        "step": 480,
        "type": "TRANSFER",
        "amount": 12000.00,
        "nameOrig": "C889900112",
        "oldbalanceOrg": 20000.00,
        "newbalanceOrig": 8000.00,
        "nameDest": "M778899003",
        "oldbalanceDest": 500.00,
        "newbalanceDest": 12500.00,
        "merchant_category": "financial",
        "ip_country": "KH",
        "hour_of_the_day": 4
    },

    # ── RIESGO MEDIO-ALTO (~0.55-0.70) ───────────────────────────────────────
    {
        "transaction_id": "TEST-009-MED-HIGH",
        "step": 600,
        "type": "TRANSFER",
        "amount": 50000.00,
        "nameOrig": "C990011223",
        "oldbalanceOrg": 55000.00,
        "newbalanceOrig": 5000.00,
        "nameDest": "M889900114",
        "oldbalanceDest": 1000.00,
        "newbalanceDest": 51000.00,
        "merchant_category": "crypto",
        "ip_country": "US",
        "hour_of_the_day": 1
    },
    {
        "transaction_id": "TEST-010-MED-HIGH",
        "step": 700,
        "type": "CASH_OUT",
        "amount": 30000.00,
        "nameOrig": "C100112234",
        "oldbalanceOrg": 32000.00,
        "newbalanceOrig": 2000.00,
        "nameDest": "M990011225",
        "oldbalanceDest": 0.00,
        "newbalanceDest": 30000.00,
        "merchant_category": "electronics",
        "ip_country": "NG",
        "hour_of_the_day": 2
    },

    # ── RIESGO ALTO (~0.70-0.80) ─────────────────────────────────────────────
    {
        "transaction_id": "TEST-011-HIGH",
        "step": 150,
        "type": "TRANSFER",
        "amount": 100000.00,
        "nameOrig": "C211223345",
        "oldbalanceOrg": 100000.00,
        "newbalanceOrig": 0.00,
        "nameDest": "M100112236",
        "oldbalanceDest": 0.00,
        "newbalanceDest": 100000.00,
        "merchant_category": "crypto",
        "ip_country": "NG",
        "hour_of_the_day": 3
    },
    {
        "transaction_id": "TEST-012-HIGH",
        "step": 280,
        "type": "CASH_OUT",
        "amount": 80000.00,
        "nameOrig": "C322334456",
        "oldbalanceOrg": 80000.00,
        "newbalanceOrig": 0.00,
        "nameDest": "M211223347",
        "oldbalanceDest": 500.00,
        "newbalanceDest": 80500.00,
        "merchant_category": "electronics",
        "ip_country": "VE",
        "hour_of_the_day": 1
    },
    {
        "transaction_id": "TEST-013-HIGH",
        "step": 390,
        "type": "TRANSFER",
        "amount": 200000.00,
        "nameOrig": "C433445567",
        "oldbalanceOrg": 200000.00,
        "newbalanceOrig": 0.00,
        "nameDest": "M322334458",
        "oldbalanceDest": 0.00,
        "newbalanceDest": 200000.00,
        "merchant_category": "crypto",
        "ip_country": "CI",
        "hour_of_the_day": 2
    },

    # ── RIESGO MUY ALTO / BLOQUEO (~0.80-0.95) ───────────────────────────────
    {
        "transaction_id": "TEST-014-VERY-HIGH",
        "step": 50,
        "type": "TRANSFER",
        "amount": 500000.00,
        "nameOrig": "C544556678",
        "oldbalanceOrg": 500000.00,
        "newbalanceOrig": 0.00,
        "nameDest": "M433445569",
        "oldbalanceDest": 0.00,
        "newbalanceDest": 0.00,
        "merchant_category": "crypto",
        "ip_country": "NG",
        "hour_of_the_day": 3
    },
    {
        "transaction_id": "TEST-015-VERY-HIGH",
        "step": 600,
        "type": "CASH_OUT",
        "amount": 999000.00,
        "nameOrig": "C655667789",
        "oldbalanceOrg": 999000.00,
        "newbalanceOrig": 0.00,
        "nameDest": "M544556670",
        "oldbalanceDest": 0.00,
        "newbalanceDest": 0.00,
        "merchant_category": "electronics",
        "ip_country": "KH",
        "hour_of_the_day": 1
    },

    # ── CASOS ESPECIALES / BORDERLINE ────────────────────────────────────────

    # Balance que no cuadra (discrepancia contable) — señal fuerte para R2
    {
        "transaction_id": "TEST-016-BALANCE-ERROR",
        "step": 330,
        "type": "TRANSFER",
        "amount": 10000.00,
        "nameOrig": "C766778890",
        "oldbalanceOrg": 15000.00,
        "newbalanceOrig": 14500.00,   # debería ser 5000, hay discrepancia
        "nameDest": "M655667781",
        "oldbalanceDest": 2000.00,
        "newbalanceDest": 2500.00,    # debería ser 12000, hay discrepancia
        "merchant_category": "financial",
        "ip_country": "ES",
        "hour_of_the_day": 15
    },

    # Cuenta origen con saldo 0 antes y después (cuenta relay)
    {
        "transaction_id": "TEST-017-ZERO-RELAY",
        "step": 450,
        "type": "TRANSFER",
        "amount": 25000.00,
        "nameOrig": "C877889901",
        "oldbalanceOrg": 0.00,
        "newbalanceOrig": 0.00,
        "nameDest": "M766778892",
        "oldbalanceDest": 5000.00,
        "newbalanceDest": 30000.00,
        "merchant_category": "unknown",
        "ip_country": "GB",
        "hour_of_the_day": 4
    },

    # País seguro + categoría segura pero importe muy alto
    {
        "transaction_id": "TEST-018-HIGH-AMOUNT-SAFE",
        "step": 220,
        "type": "TRANSFER",
        "amount": 95000.00,
        "nameOrig": "C988990012",
        "oldbalanceOrg": 100000.00,
        "newbalanceOrig": 5000.00,
        "nameDest": "M877889903",
        "oldbalanceDest": 10000.00,
        "newbalanceDest": 105000.00,
        "merchant_category": "grocery",
        "ip_country": "DE",
        "hour_of_the_day": 10
    },

    # Fraude sigiloso estilo R2: importes pequeños, país/categoría seguros
    # pero el balance no cuadra en destino
    {
        "transaction_id": "TEST-019-STEALTH",
        "step": 144,
        "type": "PAYMENT",
        "amount": 350.00,
        "nameOrig": "C199001123",
        "oldbalanceOrg": 800.00,
        "newbalanceOrig": 450.00,
        "nameDest": "M988990014",
        "oldbalanceDest": 3000.00,
        "newbalanceDest": 3000.00,    # el dinero no llegó al destino
        "merchant_category": "restaurant",
        "ip_country": "FR",
        "hour_of_the_day": 23
    },

    # CASH_IN legítimo — no debería activar casi nada
    {
        "transaction_id": "TEST-020-CASH-IN-LEGIT",
        "step": 180,
        "type": "CASH_IN",
        "amount": 2000.00,
        "nameOrig": "C200112234",
        "oldbalanceOrg": 500.00,
        "newbalanceOrig": 2500.00,
        "nameDest": "M199001125",
        "oldbalanceDest": 10000.00,
        "newbalanceDest": 8000.00,
        "merchant_category": "grocery",
        "ip_country": "ES",
        "hour_of_the_day": 9
    },
]


def run_tests():
    print(f"\n{'='*65}")
    print(f"  NovaPay Fraud Shield — Test Transactions")
    print(f"  Modelo activo: ver Terminal 1")
    print(f"{'='*65}\n")

    results = []

    for tx in transactions:
        try:
            response = requests.post(API_URL, json=tx, headers=HEADERS)
            
            if response.status_code == 200:
                data = response.json()
                score    = data["fraud_probability"]
                decision = data["decision"]
                risk     = data["risk_level"]

                # Emoji visual por nivel de riesgo
                if decision == "block":
                    emoji = "🔴"
                elif decision == "review":
                    emoji = "🟡"
                else:
                    emoji = "🟢"

                print(f"{emoji} {tx['transaction_id']:<28} score={score:.4f}  decision={decision:<8}  risk={risk}")
                results.append({"id": tx["transaction_id"], "score": score, "decision": decision})
            else:
                print(f"❌ {tx['transaction_id']:<28} → HTTP {response.status_code}: {response.text}")

        except requests.exceptions.ConnectionError:
            print(f"⚠️  No se puede conectar a {API_URL}. ¿Está levantada la API en AWS?")
            break
        except Exception as e:
            print(f"❌ {tx['transaction_id']:<28} → Error: {e}")
            
        # 2. ENGAÑAR AL RATE LIMITER (Pausa de 2.1 segundos)
        # Como el límite es 30/minuto (1 cada 2 segundos), le damos un margen de seguridad.
        time.sleep(2.1)

    print(f"\n{'='*65}")
    print(f"  Resumen: {len(results)} transacciones procesadas correctamente")
    blocked = sum(1 for r in results if r["decision"] == "block")
    reviewed = sum(1 for r in results if r["decision"] == "review")
    allowed = sum(1 for r in results if r["decision"] == "allow")
    print(f"  🔴 Bloqueadas: {blocked} | 🟡 Revisión: {reviewed} | 🟢 Permitidas: {allowed}")
    print(f"{'='*65}\n")

if __name__ == "__main__":
    run_tests()
