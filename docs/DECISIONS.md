# DECISIONS.md — Registro de Decisiones Técnicas

Sentinel · NovaPay Fraud Detection — Vertical Data Science  
Última actualización: Mayo 2026

Este documento registra las decisiones técnicas y de negocio tomadas por el equipo de Data Science durante el desarrollo del sistema de detección de fraude, junto con su justificación.

---

## 01 · EDA y calidad de datos

### Dataset base
**Decisión:** Usar el dataset sintético PaySim (UCI) como base de entrenamiento.  
**Justificación:** Es el dataset de referencia en la industria para detección de fraude en pagos móviles. Contiene patrones reales de fraude financiero con suficiente volumen (273k transacciones).

### Detección de sesgo geográfico
**Decisión:** Identificar y corregir el desbalance de fraude por país antes de entrenar.  
**Justificación:** El dataset original tenía un 100% de fraude en los países NG, CN, KH, CI y VE, lo que causaba que cualquier modelo aprendiera a bloquear esos países de forma determinista, independientemente del comportamiento financiero de la transacción.

### Balanceo de países de alto riesgo
**Decisión:** Generar transacciones legítimas sintéticas para países de alto riesgo hasta alcanzar un ratio de fraude del 25%, guardadas en `synthetic_fin_data_BALANCED.csv`.  
**Justificación:** Un ratio del 25% refleja mayor riesgo sin sesgo absoluto. El modelo aprende que esos países son zonas de mayor riesgo, pero que 3 de cada 4 transacciones son legítimas.  
**Alternativa descartada:** Eliminar ip_country como feature. Se descartó porque el país sigue siendo una señal de riesgo válida cuando se combina con otras features.

---

## 02 · Feature Engineering

### R1 — Features
**Decisión:** Usar features básicas: balances, amount, type, merchant_category, ip_country (OHE).  
**Justificación:** R1 está diseñado para detectar fraude obvio basado en señales externas y de comportamiento básico.

### R1 — Eliminación de is_high_risk_country e is_high_risk_category
**Decisión:** Eliminar estos flags binarios de las features del modelo R1.  
**Justificación:** Eran redundantes con ip_country y merchant_category ya presentes como OHE. Dominaban el 88% de la importancia del modelo, convirtiendo el resultado en una regla hardcodeada disfrazada de ML.

### R1 — ip_country: OHE en lugar de TargetEncoder
**Decisión:** Cambiar de TargetEncoder a OneHotEncoder para ip_country en R1.  
**Justificación:** El TargetEncoder embebía la probabilidad de fraude por país directamente en la feature. Con el dataset desbalanceado (100% fraude en países de riesgo), el encoder aprendía NG=fraude de forma determinista. El OHE permite que el modelo aprenda la relación entre país y fraude combinada con otras features.

### R2 — Features de comportamiento financiero
**Decisión:** Construir features derivadas: errores de balance, ratios de vaciado, flags de cuenta en cero, hora cíclica.  
**Justificación:** El fraude sigiloso no se detecta por país o categoría sino por inconsistencias en el comportamiento financiero. Estas features capturan patrones como vaciado de cuenta, discrepancias entre origen y destino, y actividad en horas inusuales.

### R2 — Hora cíclica (sin/cos)
**Decisión:** Transformar el step en hora del día con sin/cos en lugar de valor lineal.  
**Justificación:** La hora es una variable cíclica: la hora 23 y la hora 0 son contiguas. Una transformación lineal no captura esa continuidad. Sin/cos preserva la naturaleza cíclica del tiempo.

---

## 03 · Modelado

### Algoritmo: XGBoost
**Decisión:** Usar XGBoost como clasificador principal.  
**Justificación:** Mejor rendimiento en datos tabulares con clases desbalanceadas. Permite usar scale_pos_weight para compensar el desbalance sin técnicas de oversampling artificiales.

### No usar SMOTE
**Decisión:** No aplicar SMOTE para balancear clases.  
**Justificación:** SMOTE genera ejemplos sintéticos interpolando entre instancias existentes. En variables categóricas codificadas (OHE), la interpolación produce perfiles imposibles. Se prefiere scale_pos_weight.

### Métrica de optimización: F2-Score
**Decisión:** Optimizar el threshold usando F2-Score en lugar de F1.  
**Justificación:** En detección de fraude, un falso negativo (fraude no detectado) es más costoso que un falso positivo (transacción legítima bloqueada). El F2-Score penaliza más los falsos negativos al dar doble peso al recall.

### Threshold R1: 0.65
**Decisión:** Threshold de clasificación 0.65 para R1.  
**Justificación:** Valor óptimo calculado mediante búsqueda exhaustiva maximizando F2-Score sobre el test set. Precision 0.97, Recall 0.99, ROC-AUC 0.9999.

### Threshold R2: 0.90
**Decisión:** Threshold de clasificación 0.90 para R2.  
**Justificación:** El dataset balanceado tiene patrones más separables, el modelo asigna scores muy altos a fraudes claros. Un threshold alto reduce falsas alarmas manteniendo recall perfecto (0 fraudes perdidos).

---

## 04 · Sistema de scoring

### Arquitectura híbrida: ML + Bonus Rules
**Decisión:** Combinar el score del modelo con un sistema de bonus rules que suman al score final.  
**Justificación:** El modelo captura patrones aprendidos del entrenamiento. Las bonus rules permiten incorporar conocimiento de negocio explícito sin reentrenar, y detectar patrones nuevos no vistos en el entrenamiento.

### Umbrales de decisión fijos
**Decisión:** block >= 0.75, review >= 0.45, allow < 0.45.  
**Justificación:** Umbrales explícitos y documentados en el código. El threshold del joblib (0.45) se usaba incorrectamente como umbral de bloqueo cuando en realidad debería ser el inicio de review.

### Bonus rule: discrepancia de balance (+0.30)
**Decisión:** Añadir +0.30 al score cuando el cambio real del balance difiere en más del 50% del amount de la transacción.  
**Justificación:** Este patrón (amount alto pero balance casi sin cambio) no existe en el dataset de entrenamiento y el modelo no lo detecta. La regla captura fraudes de manipulación contable donde el dinero desaparece sin reflejarse en los balances. Se eligió +0.30 para garantizar que alcanza el umbral de review (0.45) incluso con score base bajo.

### Selección de modelo via variable de entorno
**Decisión:** Usar MODEL_VERSION=r1|r2 para seleccionar el pipeline al arrancar.  
**Justificación:** Permite correr ambos modelos en paralelo sin modificar el contrato de la API. El equipo de FullStack no necesita cambiar ningún JSON. La selección es transparente para los consumidores del endpoint.

---

## 05 · API

### Framework: FastAPI
**Decisión:** Usar FastAPI como framework para la API REST.  
**Justificación:** Validación automática con Pydantic, generación de documentación OpenAPI, soporte nativo para async y tipado estricto. Ideal para APIs de ML en producción.

### Validación de identificadores
**Decisión:** Validar nameOrig y nameDest con regex `^C\d{9}$` y min_length=10, max_length=10.  
**Justificación:** El formato C + 9 dígitos es el estándar del sistema. Sin validación, el endpoint aceptaba cualquier string, lo que producía predicciones sin sentido y era una superficie de ataque para fuzzing.

### Monto mínimo
**Decisión:** amount >= 10.0.  
**Justificación:** Decisión de negocio: no tiene sentido procesar transacciones por debajo de 10€. Evita ruido en el modelo y ataques con micro-transacciones.

### Monto máximo
**Decisión:** amount <= 1.000.000.000.  
**Justificación:** Límite de seguridad para evitar valores absurdos que llevarían al modelo a extrapolar fuera del rango de entrenamiento.

### Campos extra prohibidos
**Decisión:** `model_config = ConfigDict(extra="forbid")` en Transaction.  
**Justificación:** Evita que se pasen campos no documentados que podrían ser vectores de ataque o causar comportamientos inesperados en el pipeline.

### Rate limiting
**Decisión:** Limitar `/fraud/decide` a 30 requests por minuto.  
**Justificación:** Protección básica contra ataques de fuerza bruta y abuso del endpoint de decisión en tiempo real.
