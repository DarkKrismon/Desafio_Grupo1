import requests

API_URL = "http://127.0.0.1:8001/fraud/decide"
API_KEY = "centinela-secreto-123"
headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

transactions = [
    # ── ALLOW (13 transactions) ─────────────────────────────────────────
    {
        "transaction_id": "POOL-001",
        "nameOrig": "C875710680",       # avg €2,381 | GB | pharmacy | 9-17h
        "nameDest": "M427733001",
        "type": "PAYMENT",
        "amount": 2500.0,
        "oldbalanceOrg": 138757.0,
        "newbalanceOrig": 136257.0,
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 7500.0,
        "merchant_category": "pharmacy",
        "ip_country": "GB",
        "step": 200,
        "hour_of_the_day": 10,
        "_expected": "allow"
    },
    {
        "transaction_id": "POOL-002",
        "nameOrig": "C1150782627",      # avg €4,047 | FR | transport | 0h
        "nameDest": "M643984524",
        "type": "PAYMENT",
        "amount": 4200.0,
        "oldbalanceOrg": 35606.0,
        "newbalanceOrig": 31406.0,
        "oldbalanceDest": 3000.0,
        "newbalanceDest": 7200.0,
        "merchant_category": "transport",
        "ip_country": "FR",
        "step": 150,
        "hour_of_the_day": 9,
        "_expected": "allow"
    },
    {
        "transaction_id": "POOL-003",
        "nameOrig": "C383300507",       # avg €8,630 | DE | transport | 11h
        "nameDest": "M138742913",
        "type": "PAYMENT",
        "amount": 8500.0,
        "oldbalanceOrg": 28023.0,
        "newbalanceOrig": 19523.0,
        "oldbalanceDest": 2000.0,
        "newbalanceDest": 10500.0,
        "merchant_category": "transport",
        "ip_country": "DE",
        "step": 300,
        "hour_of_the_day": 11,
        "_expected": "allow"
    },
    {
        "transaction_id": "POOL-004",
        "nameOrig": "C438377140",       # avg €6,978 | US | grocery | 22h
        "nameDest": "M173085433",
        "type": "PAYMENT",
        "amount": 7000.0,
        "oldbalanceOrg": 476650.0,
        "newbalanceOrig": 469650.0,
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 12000.0,
        "merchant_category": "grocery",
        "ip_country": "US",
        "step": 400,
        "hour_of_the_day": 22,
        "_expected": "allow"
    },
    {
        "transaction_id": "POOL-005",
        "nameOrig": "C718133173",       # avg €4,350 | US | transport | 21h
        "nameDest": "M106540025",
        "type": "DEBIT",
        "amount": 4500.0,
        "oldbalanceOrg": 83248.0,
        "newbalanceOrig": 78748.0,
        "oldbalanceDest": 1000.0,
        "newbalanceDest": 5500.0,
        "merchant_category": "transport",
        "ip_country": "US",
        "step": 500,
        "hour_of_the_day": 21,
        "_expected": "allow"
    },
    {
        "transaction_id": "POOL-006",
        "nameOrig": "C907175864",       # avg €22,035 | FR | grocery | 20h
        "nameDest": "M427733001",
        "type": "PAYMENT",
        "amount": 22000.0,
        "oldbalanceOrg": 50000.0,
        "newbalanceOrig": 28000.0,
        "oldbalanceDest": 3000.0,
        "newbalanceDest": 25000.0,
        "merchant_category": "grocery",
        "ip_country": "FR",
        "step": 600,
        "hour_of_the_day": 20,
        "_expected": "allow"
    },
    {
        "transaction_id": "POOL-007",
        "nameOrig": "C1788189132",      # avg €10,347 | GB | restaurant | 15h
        "nameDest": "M643984524",
        "type": "PAYMENT",
        "amount": 10000.0,
        "oldbalanceOrg": 7092.0,
        "newbalanceOrig": -2908.0,
        "oldbalanceDest": 2000.0,
        "newbalanceDest": 12000.0,
        "merchant_category": "restaurant",
        "ip_country": "GB",
        "step": 250,
        "hour_of_the_day": 15,
        "_expected": "allow"
    },
    {
        "transaction_id": "POOL-008",
        "nameOrig": "C478300053",       # avg €18,110 | DE | transport | 17h
        "nameDest": "M138742913",
        "type": "PAYMENT",
        "amount": 18000.0,
        "oldbalanceOrg": 104801.0,
        "newbalanceOrig": 86801.0,
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 23000.0,
        "merchant_category": "transport",
        "ip_country": "DE",
        "step": 350,
        "hour_of_the_day": 17,
        "_expected": "allow"
    },
    {
        "transaction_id": "POOL-009",
        "nameOrig": "C911939325",       # avg €20,175 | FR | grocery | 13h
        "nameDest": "M173085433",
        "type": "PAYMENT",
        "amount": 20000.0,
        "oldbalanceOrg": 40000.0,
        "newbalanceOrig": 20000.0,
        "oldbalanceDest": 3000.0,
        "newbalanceDest": 23000.0,
        "merchant_category": "grocery",
        "ip_country": "FR",
        "step": 450,
        "hour_of_the_day": 13,
        "_expected": "allow"
    },
    {
        "transaction_id": "POOL-010",
        "nameOrig": "C1164296510",      # avg €11,971 | GB | fuel | 11h
        "nameDest": "M106540025",
        "type": "PAYMENT",
        "amount": 12000.0,
        "oldbalanceOrg": 94298.0,
        "newbalanceOrig": 82298.0,
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 17000.0,
        "merchant_category": "fuel",
        "ip_country": "GB",
        "step": 200,
        "hour_of_the_day": 11,
        "_expected": "allow"
    },
    {
        "transaction_id": "POOL-011",
        "nameOrig": "C1694174810",      # avg €39,162 | ES | fuel | 15h
        "nameDest": "M427733001",
        "type": "PAYMENT",
        "amount": 39000.0,
        "oldbalanceOrg": 1198.0,
        "newbalanceOrig": 0.0,
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 44000.0,
        "merchant_category": "fuel",
        "ip_country": "ES",
        "step": 300,
        "hour_of_the_day": 15,
        "_expected": "allow"
    },
    {
        "transaction_id": "POOL-012",
        "nameOrig": "C484556834",       # avg €189,952 | US | grocery | 19h
        "nameDest": "M643984524",
        "type": "PAYMENT",
        "amount": 190000.0,
        "oldbalanceOrg": 38661.0,
        "newbalanceOrig": 0.0,
        "oldbalanceDest": 10000.0,
        "newbalanceDest": 200000.0,
        "merchant_category": "grocery",
        "ip_country": "US",
        "step": 400,
        "hour_of_the_day": 19,
        "_expected": "allow"
    },
    {
        "transaction_id": "POOL-013",
        "nameOrig": "C855450603",       # avg €109,957 | ES | grocery | 16h
        "nameDest": "M138742913",
        "type": "PAYMENT",
        "amount": 110000.0,
        "oldbalanceOrg": 200000.0,
        "newbalanceOrig": 90000.0,
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 115000.0,
        "merchant_category": "grocery",
        "ip_country": "ES",
        "step": 500,
        "hour_of_the_day": 16,
        "_expected": "allow"
    },

    # ── REVIEW (14 transactions) ────────────────────────────────────────
    {
        "transaction_id": "POOL-014",
        "nameOrig": "C875710680",       # GB | pharmacy — unusual high amount
        "nameDest": "M427733001",
        "type": "CASH_OUT",
        "amount": 9500.0,              # 4x their average → +0.05 (>8000)
        "oldbalanceOrg": 138757.0,
        "newbalanceOrig": 129257.0,
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 14500.0,
        "merchant_category": "pharmacy",
        "ip_country": "GB",
        "step": 200,
        "hour_of_the_day": 3,          # nocturnal
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-015",
        "nameOrig": "C1150782627",      # FR | transport — high risk country
        "nameDest": "M643984524",
        "type": "CASH_OUT",
        "amount": 9000.0,              # +0.05 (>8000)
        "oldbalanceOrg": 35606.0,
        "newbalanceOrig": 30000.0,     # balance error → +0.08
        "oldbalanceDest": 3000.0,
        "newbalanceDest": 12000.0,
        "merchant_category": "transport",
        "ip_country": "NG",            # unusual country → +0.05
        "step": 150,
        "hour_of_the_day": 13,
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-016",
        "nameOrig": "C383300507",       # DE | transport — crypto category
        "nameDest": "M138742913",
        "type": "TRANSFER",
        "amount": 9000.0,              # +0.05 (>8000)
        "oldbalanceOrg": 28023.0,
        "newbalanceOrig": 19023.0,
        "oldbalanceDest": 2000.0,
        "newbalanceDest": 11000.0,
        "merchant_category": "crypto", # unusual category → +0.05
        "ip_country": "DE",
        "step": 300,
        "hour_of_the_day": 3,
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-017",
        "nameOrig": "C438377140",       # US | grocery — balance discrepancy
        "nameDest": "M173085433",
        "type": "CASH_OUT",
        "amount": 9000.0,              # +0.05 (>8000)
        "oldbalanceOrg": 476650.0,
        "newbalanceOrig": 471000.0,    # balance error = 4650 → +0.08
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 14000.0,
        "merchant_category": "grocery",
        "ip_country": "US",
        "step": 400,
        "hour_of_the_day": 4,
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-018",
        "nameOrig": "C718133173",       # US | transport — drain ratio
        "nameDest": "M106540025",
        "type": "CASH_OUT",
        "amount": 15000.0,             # +0.05 + drain_ratio=0.18 → +0.12
        "oldbalanceOrg": 83248.0,
        "newbalanceOrig": 68248.0,
        "oldbalanceDest": 1000.0,
        "newbalanceDest": 16000.0,
        "merchant_category": "transport",
        "ip_country": "KH",            # +0.05 + combined risk
        "step": 500,
        "hour_of_the_day": 14,
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-019",
        "nameOrig": "C907175864",       # FR | grocery — electronics category
        "nameDest": "M427733001",
        "type": "TRANSFER",
        "amount": 9500.0,              # +0.05
        "oldbalanceOrg": 50000.0,
        "newbalanceOrig": 40500.0,
        "oldbalanceDest": 3000.0,
        "newbalanceDest": 12500.0,
        "merchant_category": "electronics",  # +0.05
        "ip_country": "FR",
        "step": 600,
        "hour_of_the_day": 3,
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-020",
        "nameOrig": "C1788189132",      # GB | restaurant — CN country
        "nameDest": "M643984524",
        "type": "CASH_OUT",
        "amount": 9000.0,              # +0.05
        "oldbalanceOrg": 7092.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 2000.0,
        "newbalanceDest": 11000.0,
        "merchant_category": "restaurant",
        "ip_country": "CN",            # +0.05
        "step": 250,
        "hour_of_the_day": 14,
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-021",
        "nameOrig": "C478300053",       # DE | transport — VE country
        "nameDest": "M138742913",
        "type": "TRANSFER",
        "amount": 9000.0,              # +0.05
        "oldbalanceOrg": 104801.0,
        "newbalanceOrig": 99000.0,     # balance error → +0.08
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 14000.0,
        "merchant_category": "transport",
        "ip_country": "VE",            # +0.05
        "step": 350,
        "hour_of_the_day": 10,
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-022",
        "nameOrig": "C911939325",       # FR | grocery — high amount + NG
        "nameDest": "M173085433",
        "type": "CASH_OUT",
        "amount": 9500.0,              # +0.05
        "oldbalanceOrg": 40000.0,
        "newbalanceOrig": 30500.0,
        "oldbalanceDest": 3000.0,
        "newbalanceDest": 12500.0,
        "merchant_category": "grocery",
        "ip_country": "NG",            # +0.05
        "step": 450,
        "hour_of_the_day": 13,
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-023",
        "nameOrig": "C1164296510",      # GB | fuel — electronics + high amount
        "nameDest": "M106540025",
        "type": "TRANSFER",
        "amount": 9500.0,              # +0.05
        "oldbalanceOrg": 94298.0,
        "newbalanceOrig": 84798.0,
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 14500.0,
        "merchant_category": "electronics",  # +0.05
        "ip_country": "GB",
        "step": 200,
        "hour_of_the_day": 3,
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-024",
        "nameOrig": "C1694174810",      # ES | fuel — CI country + high amount
        "nameDest": "M427733001",
        "type": "CASH_OUT",
        "amount": 9000.0,              # +0.05
        "oldbalanceOrg": 50000.0,
        "newbalanceOrig": 41000.0,
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 14000.0,
        "merchant_category": "fuel",
        "ip_country": "CI",            # +0.05 + combined
        "step": 300,
        "hour_of_the_day": 14,
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-025",
        "nameOrig": "C484556834",       # US | grocery — KH + high amount
        "nameDest": "M643984524",
        "type": "TRANSFER",
        "amount": 9500.0,              # +0.05
        "oldbalanceOrg": 38661.0,
        "newbalanceOrig": 29161.0,
        "oldbalanceDest": 10000.0,
        "newbalanceDest": 19500.0,
        "merchant_category": "grocery",
        "ip_country": "KH",            # +0.05
        "step": 400,
        "hour_of_the_day": 10,
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-026",
        "nameOrig": "C855450603",       # ES | grocery — balance discrepancy
        "nameDest": "M138742913",
        "type": "CASH_OUT",
        "amount": 9000.0,              # +0.05
        "oldbalanceOrg": 200000.0,
        "newbalanceOrig": 194000.0,    # balance error = 3000 → +0.08
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 14000.0,
        "merchant_category": "grocery",
        "ip_country": "ES",
        "step": 500,
        "hour_of_the_day": 3,
        "_expected": "review"
    },
    {
        "transaction_id": "POOL-027",
        "nameOrig": "C1274776055",      # DE | transport — VE + high amount
        "nameDest": "M173085433",
        "type": "TRANSFER",
        "amount": 9500.0,              # +0.05
        "oldbalanceOrg": 50000.0,
        "newbalanceOrig": 40500.0,
        "oldbalanceDest": 3000.0,
        "newbalanceDest": 12500.0,
        "merchant_category": "transport",
        "ip_country": "VE",            # +0.05
        "step": 600,
        "hour_of_the_day": 14,
        "_expected": "review"
    },

    # ── BLOCK (13 transactions) ─────────────────────────────────────────
    {
        "transaction_id": "POOL-028",
        "nameOrig": "C875710680",       # GB | pharmacy — full drain + NG + crypto
        "nameDest": "M427733001",
        "type": "CASH_OUT",
        "amount": 138757.0,
        "oldbalanceOrg": 138757.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 143757.0,
        "merchant_category": "crypto", # +0.05 + combined
        "ip_country": "NG",            # +0.05
        "step": 200,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "POOL-029",
        "nameOrig": "C1150782627",      # FR | transport — full drain + KH
        "nameDest": "M643984524",
        "type": "TRANSFER",
        "amount": 35606.0,
        "oldbalanceOrg": 35606.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 3000.0,
        "newbalanceDest": 38606.0,
        "merchant_category": "electronics",  # +0.05 + combined
        "ip_country": "KH",            # +0.05
        "step": 150,
        "hour_of_the_day": 2,
        "_expected": "block"
    },
    {
        "transaction_id": "POOL-030",
        "nameOrig": "C383300507",       # DE | transport — massive drain + CN
        "nameDest": "M138742913",
        "type": "CASH_OUT",
        "amount": 28000.0,
        "oldbalanceOrg": 28023.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 2000.0,
        "newbalanceDest": 30000.0,
        "merchant_category": "crypto", # +0.05 + combined
        "ip_country": "CN",            # +0.05
        "step": 300,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "POOL-031",
        "nameOrig": "C438377140",       # US | grocery — full drain + CI
        "nameDest": "M173085433",
        "type": "TRANSFER",
        "amount": 476650.0,
        "oldbalanceOrg": 476650.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 481650.0,
        "merchant_category": "electronics",  # +0.05 + combined
        "ip_country": "CI",            # +0.05
        "step": 400,
        "hour_of_the_day": 4,
        "_expected": "block"
    },
    {
        "transaction_id": "POOL-032",
        "nameOrig": "C718133173",       # US | transport — full drain + VE
        "nameDest": "M106540025",
        "type": "CASH_OUT",
        "amount": 83248.0,
        "oldbalanceOrg": 83248.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 1000.0,
        "newbalanceDest": 84248.0,
        "merchant_category": "crypto", # +0.05 + combined
        "ip_country": "VE",            # +0.05
        "step": 500,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "POOL-033",
        "nameOrig": "C907175864",       # FR | grocery — massive amount + NG
        "nameDest": "M427733001",
        "type": "TRANSFER",
        "amount": 500000.0,
        "oldbalanceOrg": 600000.0,
        "newbalanceOrig": 100000.0,
        "oldbalanceDest": 3000.0,
        "newbalanceDest": 503000.0,
        "merchant_category": "electronics",  # +0.05 + combined
        "ip_country": "NG",            # +0.05
        "step": 600,
        "hour_of_the_day": 2,
        "_expected": "block"
    },
    {
        "transaction_id": "POOL-034",
        "nameOrig": "C1788189132",      # GB | restaurant — full drain + CI
        "nameDest": "M643984524",
        "type": "CASH_OUT",
        "amount": 7092.0,
        "oldbalanceOrg": 7092.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 2000.0,
        "newbalanceDest": 9092.0,
        "merchant_category": "crypto", # +0.05 + combined
        "ip_country": "CI",            # +0.05
        "step": 250,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "POOL-035",
        "nameOrig": "C478300053",       # DE | transport — full drain + KH
        "nameDest": "M138742913",
        "type": "TRANSFER",
        "amount": 104801.0,
        "oldbalanceOrg": 104801.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 109801.0,
        "merchant_category": "electronics",  # +0.05 + combined
        "ip_country": "KH",            # +0.05
        "step": 350,
        "hour_of_the_day": 4,
        "_expected": "block"
    },
    {
        "transaction_id": "POOL-036",
        "nameOrig": "C911939325",       # FR | grocery — full drain + CN
        "nameDest": "M173085433",
        "type": "CASH_OUT",
        "amount": 40000.0,
        "oldbalanceOrg": 40000.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 3000.0,
        "newbalanceDest": 43000.0,
        "merchant_category": "crypto", # +0.05 + combined
        "ip_country": "CN",            # +0.05
        "step": 450,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "POOL-037",
        "nameOrig": "C1164296510",      # GB | fuel — full drain + VE
        "nameDest": "M106540025",
        "type": "TRANSFER",
        "amount": 94298.0,
        "oldbalanceOrg": 94298.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 99298.0,
        "merchant_category": "electronics",  # +0.05 + combined
        "ip_country": "VE",            # +0.05
        "step": 200,
        "hour_of_the_day": 2,
        "_expected": "block"
    },
    {
        "transaction_id": "POOL-038",
        "nameOrig": "C1694174810",      # ES | fuel — full drain + NG
        "nameDest": "M427733001",
        "type": "CASH_OUT",
        "amount": 1198.0,
        "oldbalanceOrg": 1198.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 6198.0,
        "merchant_category": "crypto", # +0.05 + combined
        "ip_country": "NG",            # +0.05
        "step": 300,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
    {
        "transaction_id": "POOL-039",
        "nameOrig": "C484556834",       # US | grocery — full drain + CI
        "nameDest": "M643984524",
        "type": "TRANSFER",
        "amount": 38661.0,
        "oldbalanceOrg": 38661.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 10000.0,
        "newbalanceDest": 48661.0,
        "merchant_category": "electronics",  # +0.05 + combined
        "ip_country": "CI",            # +0.05
        "step": 400,
        "hour_of_the_day": 4,
        "_expected": "block"
    },
    {
        "transaction_id": "POOL-040",
        "nameOrig": "C855450603",       # ES | grocery — full drain + KH
        "nameDest": "M138742913",
        "type": "CASH_OUT",
        "amount": 200000.0,
        "oldbalanceOrg": 200000.0,
        "newbalanceOrig": 0.0,         # full drain → +0.10
        "oldbalanceDest": 5000.0,
        "newbalanceDest": 205000.0,
        "merchant_category": "crypto", # +0.05 + combined
        "ip_country": "KH",            # +0.05
        "step": 500,
        "hour_of_the_day": 3,
        "_expected": "block"
    },
]

results = []
wrong = []

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
            score = round(data["fraud_probability"], 3)
            matched = decision == expected
            status = "✅" if matched else "❌"

            if not matched:
                wrong.append(tx["transaction_id"])

            print(f"{tx['transaction_id']:<12} {expected:<10} {decision:<10} {score:<8} {status}")
        else:
            print(f"{tx['transaction_id']:<12} ERROR {response.status_code}: {response.text[:60]}")

    except Exception as e:
        print(f"{tx['transaction_id']:<12} ERROR: {e}")

print("-" * 55)
print(f"\nWrong: {len(wrong)}/40")
print(f"Wrong IDs: {wrong if wrong else 'None'}")
