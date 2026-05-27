transactions = [
    # ── PATTERN 1: high amount // good country // bad hour ──────────────
    {
        "transaction_id": "HISTORY-TEST-001",
        "nameOrig": "C1000036340",
        "nameDest": "M427733001",
        "type": "PAYMENT",
        "amount": 85.00,
        "oldbalanceOrg": 5000.00,
        "newbalanceOrig": 4915.00,
        "oldbalanceDest": 2000.00,
        "newbalanceDest": 2085.00,
        "merchant_category": "grocery",
        "ip_country": "ES",
        "step": 100,
        "hour_of_the_day": 11,
        "_expected": "review"
    },

    {
        "transaction_id": "EVIL-001",
        "nameOrig": "C937189368",
        "nameDest": "M427733001",
        "type": "TRANSFER",
        "amount": 95000.0,
        "oldbalanceOrg": 200000.0,
        "newbalanceOrig": 105000.0,
        "oldbalanceDest": 50000.0,
        "newbalanceDest": 145000.0,
        "merchant_category": "grocery",
        "ip_country": "GB",
        "step": 100,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-002",
        "nameOrig": "C558899863",
        "nameDest": "M643984524",
        "type": "CASH_OUT",
        "amount": 78000.0,
        "oldbalanceOrg": 150000.0,
        "newbalanceOrig": 72000.0,
        "oldbalanceDest": 30000.0,
        "newbalanceDest": 108000.0,
        "merchant_category": "pharmacy",
        "ip_country": "FR",
        "step": 200,
        "hour_of_the_day": 4,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-003",
        "nameOrig": "C112233445",
        "nameDest": "M138742913",
        "type": "TRANSFER",
        "amount": 120000.0,
        "oldbalanceOrg": 300000.0,
        "newbalanceOrig": 180000.0,
        "oldbalanceDest": 20000.0,
        "newbalanceDest": 140000.0,
        "merchant_category": "fuel",
        "ip_country": "DE",
        "step": 300,
        "hour_of_the_day": 2,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-004",
        "nameOrig": "C998877665",
        "nameDest": "M173085433",
        "type": "CASH_OUT",
        "amount": 65000.0,
        "oldbalanceOrg": 180000.0,
        "newbalanceOrig": 115000.0,
        "oldbalanceDest": 10000.0,
        "newbalanceDest": 75000.0,
        "merchant_category": "transport",
        "ip_country": "ES",
        "step": 400,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-005",
        "nameOrig": "C174995208",
        "nameDest": "M106540025",
        "type": "TRANSFER",
        "amount": 88000.0,
        "oldbalanceOrg": 200000.0,
        "newbalanceOrig": 112000.0,
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 93000.0,
        "merchant_category": "restaurant",
        "ip_country": "US",
        "step": 500,
        "hour_of_the_day": 4,
        "_expected": "block"
    },

    # ── PATTERN 2: low amount // bad country // bad hour ────────────────
    {
        "transaction_id": "EVIL-006",
        "nameOrig": "C334455667",
        "nameDest": "M427733001",
        "type": "PAYMENT",
        "amount": 85.0,
        "oldbalanceOrg": 5000.0,
        "newbalanceOrig": 4915.0,
        "oldbalanceDest": 2000.0,
        "newbalanceDest": 2085.0,
        "merchant_category": "grocery",
        "ip_country": "NG",
        "step": 150,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-007",
        "nameOrig": "C778899001",
        "nameDest": "M643984524",
        "type": "PAYMENT",
        "amount": 120.0,
        "oldbalanceOrg": 8000.0,
        "newbalanceOrig": 7880.0,
        "oldbalanceDest": 3000.0,
        "newbalanceDest": 3120.0,
        "merchant_category": "pharmacy",
        "ip_country": "KH",
        "step": 250,
        "hour_of_the_day": 4,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-008",
        "nameOrig": "C445566778",
        "nameDest": "M138742913",
        "type": "DEBIT",
        "amount": 95.0,
        "oldbalanceOrg": 4000.0,
        "newbalanceOrig": 3905.0,
        "oldbalanceDest": 1000.0,
        "newbalanceDest": 1095.0,
        "merchant_category": "fuel",
        "ip_country": "VE",
        "step": 350,
        "hour_of_the_day": 2,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-009",
        "nameOrig": "C937189368",
        "nameDest": "M173085433",
        "type": "PAYMENT",
        "amount": 75.0,
        "oldbalanceOrg": 6000.0,
        "newbalanceOrig": 5925.0,
        "oldbalanceDest": 2000.0,
        "newbalanceDest": 2075.0,
        "merchant_category": "restaurant",
        "ip_country": "CN",
        "step": 450,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-010",
        "nameOrig": "C223344556",
        "nameDest": "M106540025",
        "type": "DEBIT",
        "amount": 110.0,
        "oldbalanceOrg": 7000.0,
        "newbalanceOrig": 6890.0,
        "oldbalanceDest": 1500.0,
        "newbalanceDest": 1610.0,
        "merchant_category": "transport",
        "ip_country": "CI",
        "step": 550,
        "hour_of_the_day": 4,
        "_expected": "block"
    },

    # ── PATTERN 3: low amount // good country // bad hour ───────────────
    {
        "transaction_id": "EVIL-011",
        "nameOrig": "C667788990",
        "nameDest": "M427733001",
        "type": "PAYMENT",
        "amount": 65.0,
        "oldbalanceOrg": 3000.0,
        "newbalanceOrig": 2935.0,
        "oldbalanceDest": 1000.0,
        "newbalanceDest": 1065.0,
        "merchant_category": "grocery",
        "ip_country": "ES",
        "step": 100,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-012",
        "nameOrig": "C558899863",
        "nameDest": "M643984524",
        "type": "DEBIT",
        "amount": 90.0,
        "oldbalanceOrg": 5000.0,
        "newbalanceOrig": 4910.0,
        "oldbalanceDest": 2000.0,
        "newbalanceDest": 2090.0,
        "merchant_category": "pharmacy",
        "ip_country": "GB",
        "step": 200,
        "hour_of_the_day": 4,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-013",
        "nameOrig": "C889900112",
        "nameDest": "M138742913",
        "type": "PAYMENT",
        "amount": 55.0,
        "oldbalanceOrg": 4000.0,
        "newbalanceOrig": 3945.0,
        "oldbalanceDest": 1500.0,
        "newbalanceDest": 1555.0,
        "merchant_category": "fuel",
        "ip_country": "FR",
        "step": 300,
        "hour_of_the_day": 2,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-014",
        "nameOrig": "C174995208",
        "nameDest": "M173085433",
        "type": "DEBIT",
        "amount": 80.0,
        "oldbalanceOrg": 6000.0,
        "newbalanceOrig": 5920.0,
        "oldbalanceDest": 2000.0,
        "newbalanceDest": 2080.0,
        "merchant_category": "transport",
        "ip_country": "DE",
        "step": 400,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-015",
        "nameOrig": "C112233000",
        "nameDest": "M106540025",
        "type": "PAYMENT",
        "amount": 70.0,
        "oldbalanceOrg": 5000.0,
        "newbalanceOrig": 4930.0,
        "oldbalanceDest": 1000.0,
        "newbalanceDest": 1070.0,
        "merchant_category": "restaurant",
        "ip_country": "US",
        "step": 500,
        "hour_of_the_day": 4,
        "_expected": "block"
    },

    # ── PATTERN 4: high amount // bad country // bad hour ───────────────
    {
        "transaction_id": "EVIL-016",
        "nameOrig": "C334400111",
        "nameDest": "M427733001",
        "type": "TRANSFER",
        "amount": 95000.0,
        "oldbalanceOrg": 200000.0,
        "newbalanceOrig": 105000.0,
        "oldbalanceDest": 10000.0,
        "newbalanceDest": 105000.0,
        "merchant_category": "grocery",
        "ip_country": "NG",
        "step": 150,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-017",
        "nameOrig": "C937189368",
        "nameDest": "M643984524",
        "type": "CASH_OUT",
        "amount": 78000.0,
        "oldbalanceOrg": 150000.0,
        "newbalanceOrig": 72000.0,
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 83000.0,
        "merchant_category": "pharmacy",
        "ip_country": "KH",
        "step": 250,
        "hour_of_the_day": 4,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-018",
        "nameOrig": "C999888777",
        "nameDest": "M138742913",
        "type": "TRANSFER",
        "amount": 120000.0,
        "oldbalanceOrg": 300000.0,
        "newbalanceOrig": 180000.0,
        "oldbalanceDest": 20000.0,
        "newbalanceDest": 140000.0,
        "merchant_category": "fuel",
        "ip_country": "VE",
        "step": 350,
        "hour_of_the_day": 2,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-019",
        "nameOrig": "C111222333",
        "nameDest": "M173085433",
        "type": "CASH_OUT",
        "amount": 65000.0,
        "oldbalanceOrg": 180000.0,
        "newbalanceOrig": 115000.0,
        "oldbalanceDest": 8000.0,
        "newbalanceDest": 73000.0,
        "merchant_category": "transport",
        "ip_country": "CN",
        "step": 450,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "EVIL-020",
        "nameOrig": "C223344556",
        "nameDest": "M106540025",
        "type": "TRANSFER",
        "amount": 88000.0,
        "oldbalanceOrg": 200000.0,
        "newbalanceOrig": 112000.0,
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 93000.0,
        "merchant_category": "restaurant",
        "ip_country": "CI",
        "step": 550,
        "hour_of_the_day": 4,
        "_expected": "block"
    },
]

import requests

API_URL = "http://127.0.0.1:8001/fraud/decide"
API_KEY = "centinela-secreto-123"

headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

results = []
evaded  = []

print(f"{'ID':<12} {'Expected':<10} {'Got':<10} {'Score':<8} {'Result'}")
print("-" * 55)

for tx in transactions:
    expected = tx.pop("_expected")
    tx.pop("_id", None)
    tx.pop("_note", None)

    try:
        response = requests.post(API_URL, json=tx, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            decision = data["decision"]
            score    = round(data["fraud_probability"], 3)
            matched  = decision == expected
            status   = "✅" if matched else "❌ EVADED"
            if not matched and expected == "block":
                evaded.append(tx["transaction_id"])
            print(f"{tx['transaction_id']:<12} {expected:<10} {decision:<10} {score:<8} {status}")
        else:
            print(f"{tx['transaction_id']:<12} {expected:<10} {'ERROR':<10} {'N/A':<8} ⚠️ {response.status_code}: {response.text[:60]}")
    except Exception as e:
        print(f"{tx['transaction_id']:<12} ERROR: {e}")

print("-" * 55)
print(f"\nTotal evaded: {len(evaded)}/{len([t for t in transactions if t.get('transaction_id','') in [e for e in evaded] or True])}")
print(f"Evaded: {evaded if evaded else 'None'}")
