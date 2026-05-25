# Sentinel — API de Detección de Fraude en Tiempo Real

Sentinel es la capa de inteligencia antifraude de NovaPay. Evalúa cada transacción antes de ser aprobada y devuelve una decisión (**allow / review / block**) junto con un score de riesgo, nivel de riesgo y timestamp.

---

## Qué hace el equipo de Data Science

- **EDA:** Análisis exploratorio del dataset, detección de patrones de fraude, análisis de distribuciones y correlaciones.
- **Modelo:** Entrenamiento y validación de modelos de clasificación binaria (R1 y R2) con XGBoost.
- **API:** Desarrollo y despliegue de la API REST con FastAPI, integración del pipeline ML y sistema de bonus rules.

---

## Arquitectura

```
Transacción entrante
        ↓
POST /fraud/decide
        ↓
Pipeline ML (XGBoost) → score_ml
        ↓
Bonus Rules → score_final
        ↓
decision_from_score()
        ↓
allow / review / block
```

El sistema combina un modelo de Machine Learning serializado con un conjunto de reglas de negocio (bonus rules) que suman al score del modelo según patrones conocidos de fraude.

---

## Modelos

| Versión | Descripción | Pipeline | Threshold |
|---|---|---|---|
| R1 | Fraude obvio: país, categoría, tipo de transacción | `xgb_fraud_pipeline.joblib` | 0.65 |
| R2 | Fraude sigiloso: errores de balance, ratios de vaciado, hora cíclica | `xgb_fraud_pipeline_r2.joblib` | 0.90 |

Para seleccionar el modelo al arrancar:

```bash
# R1 (por defecto)
MODEL_VERSION=r1 python3 -m uvicorn api.main:app --port 8000 --reload

# R2
MODEL_VERSION=r2 python3 -m uvicorn api.main:app --port 8001 --reload
```

---

## Umbrales de decisión

| Score | Decisión |
|---|---|
| >= 0.75 | block |
| >= 0.45 | review |
| < 0.45 | allow |

---

## Endpoints

| Método | Endpoint | Función |
|---|---|---|
| POST | `/fraud/decide` | Decisión de fraude en tiempo real |
| GET | `/fraud/queue` | Cola de casos pendientes de revisión |
| POST | `/fraud/decide/explain` | Explicación XAI del resultado |
| POST | `/fraud/decide/preview` | Simulación de impacto de umbrales |
| POST | `/fraud/challenge` | Recomendación adaptativa de fricción |
| POST | `/fraud/feedback` | Cierre de caso por analista |
| GET | `/fraud/client/{nameOrig}` | Perfil histórico del cliente |
| GET | `/health` | Estado de la API |
| GET | `/ready` | Estado del modelo |

---

## Instalación y ejecución

```bash
# Instalar dependencias
pip install -r requirements-api.txt

# Arrancar API (R1 por defecto)
python3 -m uvicorn api.main:app --reload

# Arrancar con R2
MODEL_VERSION=r2 python3 -m uvicorn api.main:app --port 8001 --reload
```

---

## Autenticación

Todos los endpoints requieren el header:

```
X-API-Key: <api_key>
```

---

## Ejemplo de request

```bash
curl -X POST http://localhost:8000/fraud/decide \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api_key>" \
  -d '{
    "transaction_id": "TXN-001",
    "step": 10,
    "type": "TRANSFER",
    "amount": 500.0,
    "nameOrig": "C123456789",
    "oldbalanceOrg": 5000.0,
    "newbalanceOrig": 4500.0,
    "nameDest": "C987654321",
    "oldbalanceDest": 1000.0,
    "newbalanceDest": 1500.0,
    "merchant_category": "retail",
    "ip_country": "ES"
  }'
```

### Respuesta

```json
{
  "transaction_id": "TXN-001",
  "decision": "allow",
  "fraud_probability": 0.0119,
  "risk_level": "low",
  "timestamp": "2026-05-25T10:00:00Z"
}
```

---

## Validaciones de entrada

- `transaction_id`: string, 1-50 caracteres
- `amount`: float, mínimo 10.0, máximo 1.000.000.000
- `nameOrig` / `nameDest`: formato `C` + 9 dígitos (ej. `C123456789`)
- `type`: `TRANSFER`, `CASH_OUT`, `PAYMENT`, `DEBIT`, `CASH_IN`
- `step`: entero >= 1

---

## Estructura del proyecto

```
Desafio_Grupo1/
├── api/
│   ├── main.py
│   ├── routes/
│   │   └── fraud.py
│   └── schemas.py
├── src/
│   └── scoring.py
├── models/
│   ├── xgb_fraud_pipeline.joblib
│   ├── xgb_fraud_pipeline_r2.joblib
│   ├── best_threshold.joblib
│   └── best_threshold_r2.joblib
├── notebooks/
│   ├── 01_EDA.ipynb
│   ├── 02_ML.ipynb
│   └── 03_ML_Ronda2.ipynb
├── data/
├── reports/
└── docs/
    └── DECISIONS.md
```
