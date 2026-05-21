## APIs

Sentinel API permite detectar fraude en tiempo real sobre transacciones de NovaPay, devolviendo una decisión (**allow / review / block**) junto con score de riesgo y explicabilidad.

### Endpoints

| Método | Endpoint | Función |
|---|---|---|
| POST | `/fraud/decide` | Decisión de fraude |
| GET | `/fraud/queue` | Casos pendientes |
| POST | `/fraud/decide/explain` | Explicación del resultado |
| POST | `/fraud/decide/preview` | Simulación de umbrales |
| POST | `/fraud/challenge` | Acción recomendada |
| POST | `/fraud/feedback` | Feedback del analista |
| GET | `/health` | Estado de la API |
| GET | `/ready` | Estado del modelo |

### Ejecutar

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload