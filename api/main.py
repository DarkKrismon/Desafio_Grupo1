"""
api/main.py
===========
Sentinel API - Deteccion de fraude para NovaPay.

Punto de entrada de la aplicacion FastAPI.
Se encarga de:
  - Crear la app
  - Configurar CORS
  - Montar los routers (meta + fraud)

Arrancar desde la raiz del proyecto DESAFIO_GRUPO1:
    uvicorn api.main:app --reload

Docs interactivas:
    http://localhost:8000/docs
"""


from fastapi.middleware.cors import CORSMiddleware
from api.routes import fraud, meta, stats

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.limiter import limiter

app = FastAPI(
    title="Sentinel API",
    description="Fraud DNA detection for adaptive threats - NovaPay",
    version="0.1.0",
)

# Ahora configura TODO sobre esta única app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router)
app.include_router(fraud.router)
app.include_router(stats.router)

@app.get("/", include_in_schema=False)
async def root():
    return {"service": "Sentinel API", "version": app.version, "docs": "/docs"}
