# API Reference — NovaPay Fraud Shield

Sentinel · NovaPay Fraud Detection — Vertical Backend & Ingeniería de Software
Última actualización: 26 de mayo de 2026

Este documento unifica la referencia técnica de la API REST de NovaPay Fraud Shield: arquitectura del servidor, validación de entrada, motor de inferencia híbrido y especificación completa de endpoints. Sustituye a los documentos previos `Documentacion_Logica_API.md` y `Documentacion_Consultas_API.md`.

Para decisiones de diseño, justificaciones y discrepancias abiertas, ver `DECISIONS.md`.

---

## 1. Arquitectura general

El backend está construido sobre FastAPI bajo una arquitectura asíncrona y modular. El servidor actúa como pasarela entre el frontend de NovaPay y los artefactos de Machine Learning, soportando carga transaccional concurrente.

```
                    ┌────────────────────────────────────────┐
                    │       FastAPI Core (main.py)           │
                    │  Puerto 8000 · Prefijo /api/v1         │
                    └───────────────────┬────────────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│   Router de Fraude   │    │  Router de Métricas  │    │ Router de Metadatos  │
│  (routes/fraud.py)   │    │  (routes/stats.py)   │    │  (routes/meta.py)    │
└──────────┬───────────┘    └──────────┬───────────┘    └──────────────────────┘
           │                           │
           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐
│    Motor de Scoring  │    │     Cargador de      │
│     (scoring.py)     │    │  Datos (data_loader) │
└──────────┬───────────┘    └──────────────────────┘
           │
           ▼
┌──────────────────────┐
│  Artefactos .joblib  │
│ Pipeline + Threshold │
└──────────────────────┘
```

### Características del núcleo (`main.py`)

- **Prefijo global y versionado**: toda la superficie de exposición se encapsula bajo `/api/v1`, aislando los contratos actuales de futuras iteraciones.
- **Control de orígenes (CORS)**: políticas Cross-Origin integradas en el middleware de FastAPI, permitiendo peticiones HTTP asíncronas desde el panel de control sin bloqueos de red.
- **Inyección modular de rutas**: uso de `APIRouter` para desacoplar el servidor en submódulos independientes, aislando el procesamiento transaccional del cálculo de métricas agregadas.

### Mapa de módulos

| Módulo | Archivo | Responsabilidad |
|---|---|---|
| Detección y operaciones | `routes/fraud.py` | Evaluación en tiempo real, cola de revisión, feedback de analistas |
| Analítica global | `routes/stats.py` | Métricas agregadas para el dashboard |
| Metadatos del sistema | `routes/meta.py` | Healthcheck y auditoría técnica |

---

## 2. Validación de entrada (`schemas.py`)

Antes de que cualquier transacción llegue al motor de scoring, Pydantic valida automáticamente el contrato de datos. Esto actúa como primera línea de defensa contra requests malformados.

### Validación de usuario origen (`nameOrig`)

El campo `nameOrig` está sujeto a validación por expresión regular estricta: se aceptan únicamente identificadores con formato `C` seguido de exactamente 9 dígitos numéricos (ej: `C691771226`). Cualquier request que no cumpla este patrón recibe un error `422` automático sin consumir recursos del pipeline de ML.

```python
@field_validator('nameOrig')
@classmethod
def validate_user_id(cls, v):
    pattern = r'^[Cc]\d{9}$'
    if not re.match(pattern, v):
        raise ValueError('nameOrig inválido. Formato: C + 9 dígitos (ej: C123456789)')
    return v.upper()
```

Esta decisión responde a dos razones:

- **Técnica**: evita que el modelo aprenda patrones ligados a IDs de usuario específicos, garantizando que un usuario nuevo sin historial sea evaluado únicamente por el comportamiento de su transacción.
- **De negocio**: en producción real nunca se bloquea a un cliente nuevo por no tener historial previo.

---

## 3. Motor de inferencia híbrido (`scoring.py`)

El subsistema de scoring combina la predicción probabilística del modelo XGBoost con un sistema de reglas de negocio aditivas. Esto garantiza que señales individuales no obvias, que por sí solas no activarían el modelo, sean capturadas cuando se presentan en combinación.

### Carga atómica de artefactos (patrón Singleton)

Los dos artefactos serializados se cargan una única vez al arrancar Uvicorn:

- **`xgb_fraud_pipeline.joblib`**: pipeline completo que incluye el `ColumnTransformer` (con `StandardScaler` para numéricas y los encoders correspondientes para categóricas) y el clasificador XGBoost. Se carga como objeto `pipeline`.
- **`best_threshold.joblib`**: valor escalar `float` que define la frontera de decisión óptima. Se carga como objeto `threshold`.

> **Nota**: el encoder concreto aplicado a `ip_country` y el valor exacto del threshold de R1 están registrados en `DECISIONS.md §06` como discrepancias documentales abiertas pendientes de validar contra el artefacto desplegado.

```python
pipeline = joblib.load(PREP_PATH)    # pipeline completo
threshold = joblib.load(MODEL_PATH)  # float escalar
```

### Score base del modelo (`predict_proba`)

El pipeline recibe el DataFrame crudo de la transacción y ejecuta internamente la transformación y la predicción en un único paso, eliminando cualquier riesgo de inconsistencia entre el preprocesamiento de entrenamiento y el de inferencia:

```python
score_ml = float(pipeline.predict_proba(df_tx)[0][1])
```

### Sistema de bonus rules (`apply_bonus_rules`)

Sobre el score base del modelo se aplica un sistema de bonificaciones aditivas. Ninguna regla individual es suficiente para cambiar la decisión, pero su combinación sí puede elevar el score final hasta activar `review` o `block`:

| Condición | Bonus |
|---|---|
| País de alto riesgo (KH, CN, NG, CI, VE) | +0.05 |
| Categoría sospechosa (crypto, electronics) | +0.05 |
| Monto superior al percentil 95 (> 8.000 EUR) | +0.05 |
| Error de balance en cuenta origen | +0.08 |
| Error de balance en cuenta destino | +0.08 |
| Cuenta origen empieza y termina en 0 | +0.06 |
| Combinación país + categoría de riesgo | +0.05 |

El score final nunca supera 1.0:

```python
score_final = min(score_ml + bonus, 1.0)
```

---

## 4. Referencia de endpoints

Todos los endpoints están montados bajo el prefijo global `/api/v1`.

### 4.1 Módulo de detección y operaciones

Es el corazón transaccional del sistema. Controla la lógica de evaluación en tiempo real y la interacción con los analistas humanos.

---

#### `POST /api/v1/fraud/decide`

Evaluación en tiempo real de una transacción.

**Descripción**
Recibe una transacción financiera desde el backend, valida el formato del usuario origen, calcula el nivel de riesgo mediante el modelo XGBoost combinado con las bonus rules de negocio, y dictamina si la operación se aprueba, se bloquea o se envía a revisión manual. Si la transacción cae en estado `REVIEW`, se añade automáticamente a la cola de almacenamiento temporal para que los analistas la examinen.

**Validación previa**
El campo `nameOrig` se valida con Pydantic antes de llegar al modelo (ver sección 2). Requests con formato inválido reciben un `422` sin consumir recursos del pipeline.

**Request**

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

**Response `200 OK`**

```json
{
  "transaction_id": "TXN-001",
  "decision": "block",
  "fraud_probability": 0.87,
  "risk_level": "high",
  "timestamp": "2025-05-22T10:34:00Z"
}
```

**Errores**

| Código | Causa |
|---|---|
| `422 Unprocessable Entity` | `nameOrig` con formato inválido u otros campos malformados |

---

#### `GET /api/v1/fraud/queue`

Cola de trabajo de analistas.

**Descripción**
Consulta el almacenamiento interno y extrae todas las transacciones cuyo veredicto fue `REVIEW` y que aún están esperando que un analista humano dicte si eran fraude real o legítimas. El frontend llama a este endpoint de forma recurrente para pintar la tabla de casos pendientes.

**Query parameters**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `limit` | int | 50 | Número máximo de resultados. Máximo permitido: 200. |
| `risk_level` | string | — | Filtra por nivel de riesgo: `low`, `medium`, `high`. |

**Response `200 OK`**

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

---

#### `POST /api/v1/fraud/feedback`

Cierre del bucle de aprendizaje.

**Descripción**
Permite que un analista humano, desde la interfaz web, guarde la resolución definitiva de una transacción sospechosa. Elimina el caso de la cola de pendientes y almacena la etiqueta real para futuros reentrenamientos del modelo.

**Request**

```json
{
  "transaction_id": "TXN-001",
  "analyst_decision": "fraud",
  "analyst_notes": "Confirmado por usuario",
  "analyst_id": "analyst_42"
}
```

**Response `200 OK`**

```json
{
  "status": "stored",
  "case_id": "case_a1b2c3d4",
  "transaction_id": "TXN-001",
  "decision": "fraud"
}
```

---

### 4.2 Módulo de analítica global

---

#### `GET /api/v1/data/stats`

Métricas del dashboard.

**Descripción**
Llama al cargador de datos estático (`data_loader.py`) y extrae los indicadores acumulados del volumen histórico. Es la fuente de información que usa el frontend para maquetar los gráficos principales de la aplicación.

**Response `200 OK`**

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

---

### 4.3 Módulo de metadatos del sistema

---

#### `GET /api/v1/health`

Healthcheck básico.

**Descripción**
Confirma que el servidor está levantado y respondiendo. Pensado para sondas de orquestadores (load balancers, Kubernetes, etc.).

**Response `200 OK`**

```json
{
  "status": "ok",
  "service": "sentinel-api"
}
```

---

#### `GET /api/v1/ready`

Auditoría técnica.

**Descripción**
Expone el estado real del modelo en memoria, el tamaño actual de la cola de analistas y la versión del pipeline activo. Sirve para validar que la API en producción esté utilizando la versión correcta del modelo.

**Response `200 OK`**

```json
{
  "status": "ready",
  "model_loaded": true,
  "model_version": "xgb-v1.0",
  "queue_size": 12
}
```

---

## 5. Códigos de error

| Código | Significado | Cuándo se produce |
|---|---|---|
| `200 OK` | Petición exitosa | Respuesta estándar |
| `422 Unprocessable Entity` | Validación de Pydantic fallida | `nameOrig` con formato inválido, tipos incorrectos, campos requeridos ausentes |
| `500 Internal Server Error` | Error inesperado en el pipeline | Fallo en la carga de artefactos o excepción no controlada en scoring |

---

## 6. Referencias cruzadas

- **`DECISIONS.md`** — Registro de decisiones técnicas y de negocio del equipo de Data Science. Incluye en su sección 06 el historial de versiones del modelo y las discrepancias documentales abiertas (threshold de R1, encoder de `ip_country`).
- **`Procesamiento_ML.md`** — Detalle del pipeline de preprocesamiento y entrenamiento del modelo.
