# Documentación Técnica · Módulo de Procesamiento de Datos y Machine Learning
NovaPay Fraud Shield · Operación Centinela Estado: Certificado para Producción (Ronda 1)

Vertical: Data Science & IA

## 1. Arquitectura de Ingesta y Gestión de Memoria (data_loader.py)
El sistema de datos opera bajo un patrón de persistencia desacoplada y carga optimizada en memoria para asegurar la compatibilidad con entornos de alta concurrencia en la nube.

### Mecanismo de Carga Eficiente (Lazy Loading)
- El dataset procesado (synthetic_fin_data_CLEAN.csv) se almacena localmente en el directorio de datos del proyecto.

- La carga de datos se ejecuta de forma perezosa (lazy loading), lo que significa que el archivo se lee del disco únicamente cuando un servicio externo o endpoint de la API solicita información por primera vez.

- Una vez leído, el objeto DataFrame se almacena en una variable global indexada (_df), evitando lecturas redundantes de almacenamiento E/S y manteniendo un tiempo de respuesta de microsegundos en peticiones subsiguientes.

### Subsistema de Analítica y Agregación
El cargador expone funciones de cálculo estadístico en tiempo real orientadas a nutrir el panel de control del equipo de Desarrollo Web Full Stack:

- Cálculo de Métricas Globales: Proporciona el volumen total de transacciones, la tasa bruta de fraude global, el importe medio y el importe mediano expresados en EUR.

- Gating de Importes Extremos: Extrae dinámicamente el percentil 95 (p95) de los montos de transacciones legítimas para parametrizar el umbral de transferencias inusualmente altas.

- Filtrado Operacional de Riesgo: Consolida listas ordenadas de los 10 países con mayor densidad de fraude y las 10 categorías de comercio con mayor vulnerabilidad, aislando identificadores sensibles antes de su exposición en la API.

## 2. Pipeline de Preprocesamiento y Transformación
La preparación de las características numéricas y categóricas se encuentra completamente automatizada mediante objetos Pipeline y combinadores de columnas de Scikit-Learn. Esto garantiza la reproducibilidad exacta de la matemática tanto en la fase de experimentación como en el servidor de producción, eliminando el riesgo de contaminación de datos (Data Leakage).

Transacción Cruda (JSON)
│
▼
┌────────────────────────────────────────────────────────┐
│               ColumnTransformer (Inferencia)           │
├───────────────────────────┬────────────────────────────┤
│    Variables Numéricas    │    Variables Categóricas   │
│ (amount, balances, etc.)  │  (type, merchant_category) │
│       │                   │       │                    │
│       ▼                   │       ▼                    │
│  StandardScaler()         │  OneHotEncoder()           │
│                           ├────────────────────────────┤
│                           │  ip_country                │
│                           │  (alta cardinalidad)       │
│                           │       │                    │
│                           │       ▼                    │
│                           │  TargetEncoder()           │
└───────────────────────────┴────────────────────────────┘
│
▼
Vector Matemático Unificado ──► XGBoost Classifier ──► Score de Fraude (0.0 - 1.0)

### Componentes de Transformación Estricta
- Normalización Numérica: Aplicación de StandardScaler sobre los importes financieros (amount), balances iniciales (oldbalanceOrg, oldbalanceDest) y balances finales (newbalanceOrig, newbalanceDest). Esto ajusta las distribuciones para que tengan media cero y varianza unitaria.

- Codificación Categórica: Las variables type y merchant_category se codifican mediante OneHotEncoder por su naturaleza nominal. La variable ip_country, al tener alta cardinalidad, se codifica mediante TargetEncoder con suavizado (min_samples_leaf=20, smoothing=10), aprendiendo la probabilidad de fraude asociada a cada país exclusivamente sobre los datos de entrenamiento para evitar data leakage.

## 3. Especificación del Modelo Predictivo (Ronda 1)
Tras evaluar múltiples arquitecturas supervisadas, incluyendo Regresión Logística y Random Forest, se determinó que la solución óptima para datos financieros tabulares es un clasificador basado en árboles de gradiente aumentado (Gradient Boosting).

### Modelo Seleccionado: XGBoost Classifier
- Justificación Técnica: Su capacidad para segmentar de forma no lineal los desajustes de balances y su resiliencia natural ante la presencia de variables irrelevantes en las primeras etapas del reto.

- Tratamiento del Desbalanceo: Al ser el fraude un evento minoritario (3.01% del tráfico transaccional), el entrenamiento utiliza el parámetro scale_pos_weight calculado dinámicamente como el ratio entre transacciones legítimas y fraudulentas (≈32.27), penalizando severamente los falsos negativos durante el cálculo de la función de pérdida.

- Métricas de Evaluación Clave: El modelo se optimiza bajo la métrica F2-Score, que pondera el Recall el doble que la Precisión. Esto garantiza la máxima captura de transacciones fraudulentas, priorizando no dejar escapar fraude real sobre el coste de generar falsos positivos.

## 4. Parámetros Operativos e Integración de Modelos
El motor de Machine Learning no funciona bajo una clasificación rígida binaria; opera mediante una evaluación probabilística flexible calibrada para el negocio de la fintech NovaPay.

### Umbralización Óptima (Threshold Tuning)
- Punto de Corte Calibrado: El modelo exporta la probabilidad cruda de fraude (un rango continuo entre 0.0 y 1.0) mediante el método predict_proba().

- Configuración del Umbral: Se ha establecido y serializado un umbral de decisión óptimo fijado en 0.60, seleccionado maximizando F2-Score sobre el conjunto de test.

- Flujo de Decisiones de Negocio:

  Un score inferior a 0.45 se clasifica automáticamente como permitido (allow).

  Un score entre 0.45 y 0.60 desencadena un estado de revisión manual (review), inyectando la transacción directamente en la cola de análisis del Frontend.

  Un score igual o superior a 0.60 activa un bloqueo inmediato (block) para salvaguardar los fondos de la plataforma.

### Artefactos Serializados de Producción
Los componentes matemáticos se encuentran congelados en la carpeta models/ del repositorio en formato binario interoperable:

- xgb_fraud_pipeline.joblib: Contiene el pipeline completo que unifica los transformadores de columnas de Scikit-Learn junto con los pesos y la estructura de árboles entrenada de XGBoost.

- best_threshold.joblib: Almacena el valor numérico escalar del umbral calibrado (0.60) para su lectura dinámica por el módulo de scoring de la API.

## 5. Notas Técnicas de Cara a la Ronda 2 (Evolución Adversarial)
Durante el Análisis Exploratorio de Datos (EDA) de la Ronda 1, se detectó que el equipo ofensivo (Cyber) generó patrones elementales que no explotaban la totalidad de las columnas. De cara al despliegue evolutivo de la siguiente semana, se han registrado las siguientes directrices operativas:

- Activación de Codificadores de Contexto: En la Ronda 1, las variables merchant_category e ip_country mostraron un poder predictivo cercano a cero debido al diseño simplificado del ataque inicial. En la Ronda 2, en cuanto Ciberseguridad comience a camuflar el fraude alterando localizaciones o comercios, el pipeline de preprocesamiento incorporará estas variables con mayor peso en las fronteras de decisión.

- Inyección de Características de Error de Balance: Para la Ronda 2 se introducirán dos nuevas features derivadas de las columnas de balance: balance_error_orig = (oldbalanceOrg - amount) - newbalanceOrig y balance_error_dest = (oldbalanceDest + amount) - newbalanceDest. Cualquier valor distinto de cero indica una anomalía contable imposible en una transacción legítima, capturando fraudes sigilosos que arrancan con saldo cero en origen.

- Inyección de Características de Velocidad: Es mandatorio migrar hacia un análisis con memoria temporal que calcule ráfagas de transacciones acumuladas en ventanas móviles de tiempo por usuario, evitando el bypass de ataques automatizados por scripts.
