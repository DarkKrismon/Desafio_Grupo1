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

## 4. Motor de Perfilado de Cliente (client_profile.py)

El módulo de perfilado proporciona contexto histórico al analista en el momento 
de la revisión. A diferencia del motor de scoring, que es probabilístico y 
opera transacción a transacción, este módulo opera **a nivel de cliente** y 
devuelve agregaciones legibles que el analista usa para tomar la decisión final.

### Carga del Dataset Histórico (Pattern Singleton)

El dataset sintético de NovaPay se carga una sola vez en memoria al primer 
request mediante un singleton perezoso. Esto evita lecturas repetidas del CSV 
y mantiene la latencia del endpoint en el orden de milisegundos:

```python
_df_cache: Optional[pd.DataFrame] = None

def _load_dataset() -> pd.DataFrame:
    global _df_cache
    if _df_cache is None:
        _df_cache = pd.read_csv(_DATA_PATH)
    return _df_cache
```

Si el dataset cambia entre rondas (Ronda 2 del Red Team), basta con reiniciar 
uvicorn para forzar la recarga.

### Cálculo de Estadísticas Agregadas

A partir del histórico del cliente se calculan métricas estables:

| Métrica | Cálculo |
|---|---|
| total_transactions | Número de filas del cliente |
| total_volume | Suma de importes |
| avg_amount / max_amount | Estadísticos descriptivos del importe |
| fraud_rate_historical | Ratio isFraud=1 sobre el total del cliente |
| distinct_counterparties | nameDest únicos |
| most_used_type | Moda de la columna type |

### Sistema de Banderas Cualitativas (Risk Flags)

Sobre el histórico del cliente se evalúan reglas heurísticas que devuelven 
banderas legibles. Estas banderas **no compiten** con el score del modelo: 
son señales rápidas para que el analista entienda el caso de un vistazo.

| Bandera | Condición |
|---|---|
| new_client | El cliente tiene ≤ 3 transacciones registradas |
| previously_flagged | Alguna transacción del cliente está marcada como fraude |
| frequent_cash_out | Más del 50% de sus transacciones son CASH_OUT |
| high_velocity | Más de 0,5 transacciones por unidad de step |
| unusual_amount | Alguna transacción supera 5× su importe medio |
| concentrated_destination | Más del 70% del volumen va a un único destinatario |

### Decisión de Diseño: Lectura del CSV vs Base de Datos

En esta fase del proyecto la fuente del histórico es el CSV sintético generado 
por el Red Team. En un sistema en producción real este motor leería de una 
base de datos OLAP o un data warehouse con índices sobre nameOrig. La elección 
de CSV responde al alcance MVP y a que el dataset es estático durante cada 
ronda adversarial.

### Consideraciones de Privacidad

Los identificadores nameOrig y nameDest se exponen en claro al analista porque 
los datos son sintéticos. En un despliegue real, estos identificadores 
deberían tokenizarse o pseudonimizarse en el endpoint, y el acceso del 
analista registrarse en un log de auditoría conforme al principio de 
minimización de datos.