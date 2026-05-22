# Arquitectura y Mapa de Endpoints de NovaPay API

Toda la API está montada bajo el prefijo global /api/v1. Las llamadas se dividen en tres grandes módulos operativos:

## 1. Módulo de Detección y Operaciones (routes/fraud.py)

Es el corazón transaccional del sistema. Controla la lógica de evaluación en tiempo real y la interacción con los analistas humanos.

- `POST /api/v1/fraud/decide` (Evaluación en Tiempo Real)
  - Qué hace: Recibe una transacción financiera desde el backend de Full Stack, valida el formato del usuario origen, calcula el nivel de riesgo mediante el modelo XGBoost combinado con reglas de negocio híbridas, y dictamina si la operación se aprueba, se bloquea o se envía a revisión manual. Si la transacción cae en estado de revisión (REVIEW), el script la añade automáticamente a una cola de almacenamiento temporal para que los analistas la examinen en su panel visual.

  - Validación previa (Pydantic): El campo nameOrig es validado automáticamente antes de llegar al modelo. Solo se aceptan identificadores con formato C seguido de exactamente 9 dígitos (ej: C691771226). Cualquier request que no cumpla este formato recibe un error 422 sin consumir recursos del pipeline.

  - Qué recibe (Cuerpo JSON):

```json
    {
      "transaction_id": "TXN-001",
      "nameOrig": "C691771226",
      "type": "CASH_OUT",
      "amount": 183806.32,
      "oldbalanceOrg": 19391.0,
      "newbalanceOrig": 0.0,
      "oldbalanceDest": 382572.19,
      "newbalanceDest": 566378.51,
      "merchant_category": "financial",
      "ip_country": "US"
    }
```

  - Qué devuelve (Respuesta JSON):

```json
    {
      "transaction_id": "TXN-001",
      "decision": "block",
      "fraud_probability": 0.87,
      "risk_level": "high",
      "timestamp": "2025-05-22T10:34:00Z"
    }
```

- `GET /api/v1/fraud/queue` (Cola de Trabajo de Analistas)
  - Qué hace: Consulta el almacenamiento interno y extrae todas las transacciones cuyo veredicto fue REVIEW y que aún están esperando que un analista humano dicte si eran fraude real o legítimas. El Frontend llamará a este endpoint de forma recurrente para pintar la tabla de casos pendientes. Permite filtrar por nivel de riesgo (low, medium, high) y limitar el número de resultados.
  - Qué recibe: Parámetros opcionales de query: limit (por defecto 50, máximo 200) y risk_level.
  - Qué devuelve:

```json
    {
      "total_pending": 12,
      "queue": [
        {
          "transaction_id": "TXN-001",
          "amount": 183806.32,
          "type": "CASH_OUT",
          "ip_country": "US",
          "merchant_category": "financial",
          "fraud_probability": 0.54,
          "risk_level": "medium",
          "timestamp": "2025-05-22T10:34:00Z"
        }
      ]
    }
```

- `POST /api/v1/fraud/feedback` (Cierre del Bucle de Aprendizaje)
  - Qué hace: Permite que un analista humano, desde la interfaz web, guarde la resolución definitiva de una transacción sospechosa. Elimina el caso de la cola de pendientes y almacena la etiqueta real para futuros reentrenamientos del modelo.
  - Qué recibe (Cuerpo JSON):

```json
    {
      "transaction_id": "TXN-001",
      "analyst_decision": "fraud",
      "analyst_notes": "Confirmado por usuario",
      "analyst_id": "analyst_42"
    }
```

  - Qué devuelve:

```json
    {
      "status": "stored",
      "case_id": "case_a1b2c3d4",
      "transaction_id": "TXN-001",
      "decision": "fraud"
    }
```

## 2. Módulo de Analítica Global (routes/stats.py)

- `GET /api/v1/data/stats` (Métricas del Dashboard)
  - Qué hace: Llama al cargador de datos estático (data_loader.py) y extrae los indicadores acumulados del volumen histórico. Es la fuente de información que usará Full Stack para maquetar los gráficos principales de la aplicación.
  - Qué recibe: Nada.
  - Qué devuelve:

```json
    {
      "total_transactions": 273213,
      "total_fraud_cases": 8213,
      "global_fraud_rate": 0.0301,
      "avg_amount_eur": 15420.50,
      "median_amount_eur": 2300.10,
      "high_amount_threshold_eur": 8000.00,
      "top_risky_countries": [
        {"country": "KH", "fraud_rate": 0.12}
      ],
      "top_risky_categories": [
        {"category": "crypto", "fraud_rate": 0.09}
      ]
    }
```

## 3. Módulo de Metadatos del Sistema (routes/meta.py)

- `GET /api/v1/health` (Healthcheck Básico)
  - Qué hace: Confirma que el servidor está levantado y respondiendo.
  - Qué devuelve:

```json
    {
      "status": "ok",
      "service": "sentinel-api"
    }
```

- `GET /api/v1/ready` (Auditoría Técnica)
  - Qué hace: Expone el estado real del modelo en memoria, el tamaño actual de la cola de analistas y la versión del pipeline activo. Sirve para validar que la API en producción esté utilizando la versión matemática correcta.
  - Qué devuelve:

```json
    {
      "status": "ready",
      "model_loaded": true,
      "model_version": "xgb-v1.0",
      "queue_size": 12
    }
```
