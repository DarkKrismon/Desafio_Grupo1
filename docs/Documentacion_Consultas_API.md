# Arquitectura y Mapa de Endpoints de NovaPay API

Toda la API está montada bajo el prefijo global /api/v1. Las llamadas se dividen en tres grandes módulos operativos:

## 1. Módulo de Detección y Operaciones (routes/fraud.py)

Es el corazón transaccional del sistema. Controla la lógica de evaluación en tiempo real y la interacción con los analistas humanos.

- `POST /api/v1/fraud/decide` (Evaluación en Tiempo Real)
 - Qué hace: Recibe una transacción financiera desde el backend de Full Stack, calcula el nivel de riesgo y dictamina si la operación se aprueba, se bloquea o se envía a revisión manual. Si la transacción cae en estado de revisión (REVIEW), el script la añade automáticamente a una cola de almacenamiento temporal para que los analistas la examinen en su panel visual.

 - Qué recibe (Cuerpo JSON): Un objeto transaccional completo.

    JSON
    {
    "step": 162,
    "type": "CASH_OUT",
    "amount": 183806.32,
    "nameOrig": "C691771226",
    "oldbalanceOrg": 19391.0,
    "newbalanceOrig": 0.0,
    "nameDest": "C1416312719",
    "oldbalanceDest": 382572.19,
    "newbalanceDest": 566378.51,
    "merchant_category": "financial",
    "ip_country": "US"
    }

 - Qué devuelve (Respuesta JSON): 
 Un veredicto estructurado con el score numérico, el nivel de riesgo (LOW, MEDIUM, HIGH), la acción obligatoria (ALLOW, REVIEW, BLOCK), el tipo de fricción de seguridad recomendada (como verificación por SMS o Biometría) y la justificación técnica de la decisión.

    JSON
    {
    "transaction_id": "tx_1716324500_C691771226",
    "score": 0.85,
    "risk_level": "HIGH",
    "action": "BLOCK",
    "friction_recommended": "BIOMETRIC",
    "reason": "Importe supera percentil de riesgo y país con alta densidad de fraude."
    }

- `GET /api/v1/fraud/pending` (Cola de Trabajo de Analistas)
 - Qué hace: Consulta el almacenamiento interno y extrae todas las transacciones cuyo veredicto fue REVIEW y que aún están esperando que un analista humano dicte si eran fraude real o legítimas. El Frontend llamará a este endpoint de forma recurrente para pintar la tabla de casos pendientes.
 - Qué recibe: Nada (petición GET limpia).
 - Qué devuelve: Una lista ordenada de objetos de transacciones pendientes.

- `POST /api/v1/fraud/feedback` (Cierre del Bucle de Aprendizaje)
 - Qué hace: Permite que un analista humano, desde la interfaz web, guarde la resolución definitiva de una transacción sospechosa. Esto es crucial: guarda la "etiqueta real" de la operación, lo que os servirá en el futuro para reentrenar el modelo con los aciertos y fallos.
 - Qué recibe (Cuerpo JSON): El identificador único de la transacción y el veredicto real ($1$ si se confirmó fraude, $0$ si era una operación lícita).
 
    JSON
    {
    "transaction_id": "tx_1716324500_C691771226",
    "true_label": 1
    }

 - Qué devuelve: Un mensaje de confirmación de almacenamiento.


## 2. Módulo de Analítica Global (routes/stats.py)

- `GET /api/v1/stats/summary` (Métricas del Dashboard)
 - Qué hace: Llama al cargador de datos estático (data_loader.py) y extrae los indicadores acumulados del volumen histórico. Es la fuente de información que usará Full Stack para maquetar los gráficos principales de la aplicación.
 - Qué recibe: Nada.
 - Qué devuelve: Un informe resumido con el volumen total de operaciones procesadas, la tasa de fraude media, montos promedio, y los rankings de riesgo geográfico y comercial.

    JSON
    {
    "total_transactions": 500000,
    "fraud_rate": 0.0057,
    "avg_amount": 15420.50,
    "median_amount": 2300.10,
    "top_fraud_countries": ["US", "GB", "RU"],
    "top_fraud_categories": ["financial", "transfer", "electronics"]
    }


## 3. Módulo de Metadatos del Sistema (routes/meta.py)

- `GET /api/v1/meta/info` (Auditoría Técnica)
 - Qué hace: Expone el estado del software, el entorno de despliegue y las características técnicas del modelo predictivo que está cargado en memoria. Sirve para validar que la API en producción en AWS esté utilizando la versión matemática correcta.
 - Qué recibe: Nada.
 - Qué devuelve: El nombre de la aplicación, versión semántica, entorno activo y metadatos del pipeline.