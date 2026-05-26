# 🧠 Módulo de Explicabilidad IA (Motor Llama 3)

Este documento detalla la integración del modelo de lenguaje de gran escala (LLM) en la API de NovaPay. El objetivo de este módulo es dotar al sistema de una capa de razonamiento humano que explique, de forma técnica y auditable, las decisiones de bloqueo tomadas por el modelo predictivo (XGBoost).

---

## 🏗️ 1. Arquitectura y Principios de Diseño

Para garantizar la estabilidad del servidor y mantener el código mantenible, el módulo de IA se ha diseñado bajo el principio de **Separación de Responsabilidades (SoC)**:

1.  **Cero Fricción para Web:** El endpoint es un simple `GET`. El frontend no necesita construir cuerpos JSON ni manejar cabeceras complejas.
2.  **Aislamiento del Motor (`src/llm_explainer.py`):** Toda la lógica de *prompt engineering*, parámetros de temperatura y conexión con la API de Groq reside en un módulo independiente. Si la IA falla, la pasarela de pagos sigue funcionando.
3.  **Privacidad por Diseño (Anonimización):** La API extrae los datos reales directamente desde PostgreSQL (Supabase) usando el ID de la transacción. Antes de enviar la información al LLM, los datos son anonimizados (GDPR compliance) ocultando los IDs reales de los clientes.

---

## 📡 2. Contrato del Endpoint (Documentación para Frontend)

**Ruta:** `GET /fraud/explain/{transaction_id}`

Este endpoint debe ser llamado **únicamente a demanda** (cuando un analista hace clic en "Explicar Fraude"). Genera una latencia de ~2-3 segundos debido a la inferencia del modelo masivo. No invocar en bucle.

### Petición HTTP (Fetch)
Solo se requiere concatenar el ID de la transacción al final de la URL:
```javascript
const response = await fetch(`http://TU_IP_AWS:8000/fraud/explain/${transaction_id}`);
```

### Respuesta Exitosa (200 OK)
Devuelve un JSON plano optimizado para impresión directa en el panel de UI.
```json
{
  "narrative": "La transacción presenta un riesgo debido a la discrepancia matemática en el balance, ya que el vaciado de cuenta (65365.1) no cuadra con el cambio en el balance de destino... Además, el país de la IP (Alemania) y la categoría (farmacia) no presentan indicadores de riesgo adicionales."
}
```

---

## ⚙️ 3. Configuración del Servidor y Despliegue

### Motor Utilizado
* **Proveedor:** Groq LPU (Procesamiento ultrarrápido).
* **Modelo:** `llama-3.3-70b-versatile` (Seleccionado por su alta capacidad de razonamiento lógico/matemático).
* **Temperatura:** `0.2` (Estricta para evitar alucinaciones).

### Variables de Entorno (`.env`)
Es absolutamente crítico que la variable se defina sin espacios en blanco tras el signo igual y sin comillas de ningún tipo, o el contenedor devolverá un Error 401.

```env
GROQ_API_KEY=gsk_tucadenadeletrasynumeros
```

### Dependencias Críticas (`requirements.txt`)
```text
groq
python-dotenv
```
*(Cualquier actualización en este archivo requiere ejecutar `docker build --no-cache` para purgar la memoria del contenedor).*

---

## 💻 4. Estructura del Código

### A. El Cerebro Aislado (`src/llm_explainer.py`)
Encargado de la orquestación del *System Prompt* y la comunicación con el proveedor de IA.

```python
import os
from groq import Groq

def analyze_fraud_with_llm(tx_data: dict) -> str:
    """
    Recibe datos anonimizados, inyecta el contexto en el prompt y 
    devuelve el análisis de Llama 3.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Error interno: El motor de IA no está configurado."

    client = Groq(api_key=api_key)

    system_prompt = (
        "Eres un auditor senior experto en fraude financiero bancario. "
        "Tu objetivo es explicar por qué el modelo predictivo ha calificado esta transacción con ese nivel de riesgo. "
        "Analiza las discrepancias matemáticas en los balances (ej: vaciados de cuenta, cuenta origen a cero que no cuadra con el importe), "
        "el país de la IP y la categoría del comercio. "
        "REGLAS ESTRICTAS: "
        "1. No saludes, no te despidas, no uses introducciones genéricas. "
        "2. Ve directo al análisis de los números. "
        "3. Responde en un solo párrafo de máximo 3 o 4 líneas. "
        "4. Usa un tono frío, técnico y profesional."
    )

    user_prompt = f"Analiza la siguiente transacción financiera anonimizada y justifica su riesgo:\n{tx_data}"

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile", 
            temperature=0.2, 
            max_tokens=150
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Error en la API de Groq: {e}")
        return "No se pudo generar la explicación debido a un error de conexión con el motor de IA."
```

### B. El Controlador (`api/routes/fraud.py`)
Endpoint simplificado y blindado contra inyecciones externas.

```python
from fastapi import APIRouter, HTTPException
from psycopg2.extras import RealDictCursor
from src.storage import get_connection
from src.llm_explainer import analyze_fraud_with_llm

router = APIRouter(prefix="/fraud", tags=["Fraud Detection"])

@router.get("/explain/{transaction_id}", summary="Explicación del fraude simplificada")
async def fraud_explain_simple(transaction_id: str):
    # 1. Extracción segura desde BD
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM "Transactions" WHERE transaction_id = %s', (transaction_id,))
        tx = cur.fetchone()
        cur.close()
        conn.close()
    except Exception:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos.")
    
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada.")

    # 2. Sanitización y preparación del payload
    anon_data = {
        "step_hours": tx["step"],
        "type": tx["type"],
        "amount": tx["amount"],
        "oldbalanceOrg": tx["oldbalanceOrg"],
        "newbalanceOrig": tx["newbalanceOrig"],
        "oldbalanceDest": tx["oldbalanceDest"],
        "newbalanceDest": tx["newbalanceDest"],
        "ip_country": tx["ip_country"],
        "merchant_category": tx["merchant_category"]
    }

    # 3. Inferencia
    explicacion = analyze_fraud_with_llm(anon_data)

    return {"narrative": explicacion}
```