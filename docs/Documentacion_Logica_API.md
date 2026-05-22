# Documentación Técnica · Módulo de Servidor y Motores de Inferencia
NovaPay Fraud Shield · Operación Centinela Estado: Arquitectura Consolidada para Producción (Ronda 1 con Cambios Integrados)

Vertical: Arquitectura Backend & Ingeniería de Software

## 1. Arquitectura General del Servidor y Ciclo de Vida

El núcleo del backend está diseñado bajo una arquitectura limpia, asíncrona y altamente modular utilizando FastAPI como framework de alto rendimiento. El servidor está preparado para absorber cargas transaccionales concurrentes y actuar como pasarela intermedia entre los canales de Full Stack y los artefactos de Inteligencia Artificial.                                      


                    ┌────────────────────────────────────────┐
                    │       FastAPI Core (main.py)           │
                    │  - Puerto 8000 | Prefijo /api/v1       │
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


 ### Características del Núcleo (main.py)

- Prefijo Global y Versionado: Toda la superficie de exposición se encapsula bajo el prefijo único /api/v1, aislando los contratos de datos actuales de futuras iteraciones lógicas o evoluciones del sistema.

- Control de Orígenes (CORS): Implementación de políticas de seguridad Cross-Origin Resource Sharing integradas de forma nativa en el middleware de FastAPI. Esto permite que el panel de control maquetado por el equipo de Full Stack realice peticiones HTTP asíncronas seguras desde navegadores externos sin bloqueos de red.

- Inyección Modular de Rutas: Utilización de APIRouter para desacoplar el servidor en submódulos operativos independientes, aislando el procesamiento transaccional del cálculo de métricas agregadas para el cuadro de mando.

## 2. Validación de Entrada (schemas.py)

Antes de que cualquier transacción llegue al motor de scoring, Pydantic valida automáticamente el contrato de datos entrante. Esto actúa como primera línea de defensa contra requests malformados o usuarios inválidos.

### Validación de Usuario Origen (nameOrig)
El campo nameOrig está sujeto a una validación por expresión regular estricta. Solo se aceptan identificadores que cumplan el formato C seguido de exactamente 9 dígitos numéricos (ej: C691771226). Cualquier request que no cumpla este patrón recibe un error 422 automático sin consumir recursos del pipeline de ML.

Esta decisión de diseño responde a dos razones:

- Técnica: Evita que el modelo aprenda patrones ligados a IDs de usuario específicos, garantizando que un usuario nuevo sin historial sea evaluado únicamente por el comportamiento de su transacción.

- De negocio: En producción real nunca se bloquea a un cliente nuevo por no tener historial previo.

```python
@field_validator('nameOrig')
@classmethod
def validate_user_id(cls, v):
    pattern = r'^[Cc]\d{9}$'
    if not re.match(pattern, v):
        raise ValueError('nameOrig inválido. Formato: C + 9 dígitos (ej: C123456789)')
    return v.upper()
```

## 3. Motor de Inferencia Híbrido (scoring.py)

El subsistema de scoring combina la predicción probabilística del modelo XGBoost con un sistema de reglas de negocio aditivas. Esto garantiza que señales individuales no obvias, que por sí solas no activarían el modelo, sean capturadas cuando se presentan en combinación.

### Carga Atómica de Artefactos (Pattern Singleton)

Los dos artefactos serializados se cargan una única vez al arrancar Uvicorn:

- xgb_fraud_pipeline.joblib: Pipeline completo que incluye el ColumnTransformer (StandardScaler + OneHotEncoder + TargetEncoder) y el clasificador XGBoost. Se carga como objeto pipeline.

- best_threshold.joblib: Valor escalar float (0.60) que define la frontera de decisión óptima. Se carga como objeto threshold.

```python
pipeline = joblib.load(PREP_PATH)   # pipeline completo
threshold = joblib.load(MODEL_PATH) # float escalar: 0.60
```

### Score Base del Modelo (predict_proba)

El pipeline recibe el DataFrame crudo de la transacción y ejecuta internamente la transformación y la predicción en un único paso, eliminando cualquier riesgo de inconsistencia entre el preprocesamiento de entrenamiento y el de inferencia:

```python
score_ml = float(pipeline.predict_proba(df_tx)[0][1])
```

### Sistema de Bonus Rules (apply_bonus_rules)

Sobre el score base del modelo se aplica un sistema de bonificaciones aditivas. Ninguna regla individual es suficiente para cambiar la decisión, pero su combinación sí puede elevar el score final hasta activar review o block:

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

Ejemplo de combinación:
