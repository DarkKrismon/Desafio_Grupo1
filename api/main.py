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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import fraud, meta


# ============================================================
# APP
# ============================================================
app = FastAPI(
    title="Sentinel API",
    description="Fraud DNA detection for adaptive threats - NovaPay",
    version="0.1.0",
)


# ============================================================
# MIDDLEWARE
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # en produccion: lista de dominios de NovaPay
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTERS
# ============================================================
app.include_router(meta.router)
app.include_router(fraud.router)


# ============================================================
# ROOT
# ============================================================
@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "Sentinel API",
        "version": app.version,
        "docs": "/docs",
    }
