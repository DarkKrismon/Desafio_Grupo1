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


 # Características del Núcleo (main.py)

 - Prefijo Global y Versionado: Toda la superficie de exposición se encapsula bajo el prefijo único /api/v1, aislando los contratos de datos actuales de futuras iteraciones lógicas o evoluciones del sistema.

 - Control de Orígenes (CORS): Implementación de políticas de seguridad Cross-Origin Resource Sharing integradas de forma nativa en el middleware de FastAPI. Esto permite que el panel de control maquetado por el equipo de Full Stack realice peticiones HTTP asíncronas seguras desde navegadores externos sin bloqueos de red.

 - Inyección Modular de Rutas: Utilización de APIRouter para desacoplar el servidor en submódulos operativos independientes, aislando el procesamiento transaccional del cálculo de métricas agregadas para el cuadro de mando.

## 2. Motor de Inferencia y Puntuación Coherente (scoring.py)

  El subsistema de scoring procesa las transacciones entrantes de forma puramente predictiva, eliminando cualquier lógica basada en reglas estáticas manuales que puedan ser evadidas por el Red Team.

 # Integración del Pipeline de Machine Learning

 - Carga Atómica (Pattern Singleton): El pipeline de clasificación unificado (xgb_fraud_pipeline.joblib) se levanta en el ámbito global del módulo durante el arranque del proceso de Uvicorn. Esto garantiza que la carga de pesos y transformadores matemáticos ocurra una única vez, evitando la latencia extrema que supondría leer el disco en cada transacción.

 - Traducción Estricta de Tipos: El motor recibe el objeto transaccional validado por Pydantic, lo transforma en un vector estructurado mediante un DataFrame de Pandas en microsegundos y lo somete al ColumnTransformer preentrenado. Esto asegura que variables categóricas como el tipo de operación o el origen geográfico se codifiquen con la misma matriz matemática calculada en la fase de modelado.
 
 - Cálculo de Probabilidad Continua: El sistema ejecuta el método predict_proba(), abstrayendo un valor continuo estrictamente comprendido entre 0.0 (legitimidad absoluta) y 1.0 (certeza de fraude).


## 3. Sincronización del Umbral de Decisión y Fricción Operacional

 La API traduce la probabilidad numérica extraída por el modelo XGBoost en acciones operacionales inmediatas para el negocio de la fintech NovaPay, vinculando la matemática con la toma de decisiones financieras.

 # Umbralización Dinámica Calibrada

 El enrutador lee de forma síncrona el archivo best_threshold.joblib, fijando la frontera de decisión óptima calculada en el análisis de sensibilidad de Data Science. El flujo de control se rige bajo la siguiente matriz de criticidad:

 # Lógica de Fricción de Seguridad

 - Mitigación del Falso Positivo: Las operaciones con riesgo moderado no se rechazan de plano; se desvían a un estado de fricción intermedia (SMS) y se inyectan en la cola humana, protegiendo la experiencia del usuario legítimo.
 
 - Defensa Proactiva: Las transacciones que alcanzan o superan el umbral matemático óptimo desencadenan una orden de bloqueo inmediato (BLOCK), requiriendo biometría avanzada y salvaguardando los fondos de la plataforma antes de que el dinero salga del ecosistema.

 
## 4. Capa de Persistencia e Interfaz de Almacenamiento (storage.py)

 El estado operativo del sistema se gestiona mediante una capa intermedia de almacenamiento aislada, encargada de desacoplar las rutas de FastAPI del motor físico de la base de datos.

 # Gestión de la Cola de Analistas y Feedback
 
 - Aislamiento de Responsabilidades: Las rutas transaccionales nunca escriben ni consultan datos directamente. Invocan funciones de interfaz abstractas en storage.py (como save_pending_transaction o get_pending_transactions).
 
 - Bucle de Aprendizaje Cerrado: El almacén indexa las transacciones en estado de revisión bajo un identificador único estructural. Cuando un analista dicta una resolución definitiva desde la interfaz, el sistema actualiza el registro guardando el true_label (fraude real confirmado o falso positivo). Esto deja el terreno preparado para los scripts de reentrenamiento del modelo.
 
 - Arquitectura Conectiva: La lógica de almacenamiento está unificada bajo firmas de funciones estándar. Esto permite mutar el motor interno desde estructuras ligeras hacia bases de datos relacionales robustas en la nube sin necesidad de modificar una sola línea de código en las rutas de la API.
 
 
## 5. Estrategia de Contenedores y Despliegue en la Nube

 Para garantizar la inmutabilidad del sistema y eliminar el clásico problema de "funciona en mi máquina", el entorno se encuentra completamente empaquetado bajo tecnología de contenedores.
 
 # Especificación del Contenedor (Dockerfile)
 
 - Imagen Base Optimizada: Se utiliza python:3.11-slim, una distribución ligera basada en Debian que reduce la superficie de ataque y el peso del artefacto a menos de un tercio de una imagen estándar, optimizando el tiempo de despliegue en AWS.
 
 - Aislamiento de Dependencias: El proceso de construcción copia de forma aislada el archivo de requerimientos e instala las librerías matemáticas binarias (como NumPy, Pandas y XGBoost) utilizando los compiladores nativos del sistema mediante gcc.
 
 - Exposición y Ejecución: El contenedor expone de forma fija el puerto 8000 y delega la ejecución de la app al servidor de producción Uvicorn, configurando el host en 0.0.0.0 para permitir que el balanceador de carga de AWS redirija el tráfico de internet hacia el interior del contenedor.