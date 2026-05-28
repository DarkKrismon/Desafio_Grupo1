import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def analyze_fraud_with_llm(tx_data: dict) -> str:
    """
    Recibe un diccionario con los datos anonimizados de la transacción,
    se conecta a Groq (Llama 3) y devuelve una explicación de máximo 3 líneas.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Error interno: El motor de IA no está configurado (Falta GROQ_API_KEY)."

    # Inicializamos el cliente aquí para asegurar que coge la variable de entorno actual
    client = Groq(api_key=api_key)

    system_prompt = (
        "Eres un auditor senior experto en fraude financiero bancario. "
        "Tu objetivo es explicar por qué el modelo predictivo ha calificado esta transacción con ese nivel de riesgo (bajo, medio, alto). "
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
            model="llama3-8b-8192", 
            temperature=0.2, 
            max_tokens=150
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error CRÍTICO en la API de Groq: {error_msg}")
        
        if "429" in error_msg or "rate limit" in error_msg.lower():
            return "El motor de IA está saturado por demasiadas peticiones. Espera un minuto."
        
        return "No se pudo generar la explicación debido a un error de conexión con el motor de IA."
    


if __name__ == "__main__":
    print("Iniciando prueba de conexión con Groq / Llama 3...")
    
    # Simulamos una transacción fraudulenta (Vaciado de cuenta)
    transaccion_falsa = {
        "step_hours": 12,
        "type": "TRANSFER",
        "amount": 45000.0,
        "oldbalanceOrg": 45000.0,
        "newbalanceOrig": 0.0,
        "oldbalanceDest": 0.0,
        "newbalanceDest": 0.0,
        "ip_country": "KH",
        "merchant_category": "crypto",
        "fraud_probability": 0.94,
        "risk_level": "high"
    }
    
    respuesta = analyze_fraud_with_llm(transaccion_falsa)
    print("\n--- RESPUESTA DE LA IA ---")
    print(respuesta)
    print("--------------------------")