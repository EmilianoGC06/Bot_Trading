"""API del bot (FastAPI). Documentación interactiva en /docs.

Arranque: uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000

Todas las rutas, salvo /api/salud, exigen el encabezado X-API-Key con BOT_API_KEY.
La clave vive solo en el servidor (.env) y nunca se envía al LLM.
"""
from __future__ import annotations

import secrets

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .agente import Agente
from .config import Config, cargar
from .db import BD
from .llm import ClienteOllama, OllamaError
from .mexc import ClienteMEXC
from .modelo import cargar_predictor


def construir_agente(cfg: Config) -> Agente:
    return Agente(cfg, BD(cfg.db_path), ClienteMEXC(cfg.mexc_url),
                  ClienteOllama(cfg.ollama_url, cfg.ollama_modelo, cfg.ollama_timeout_s),
                  cargar_predictor(cfg.modelo_path))


def create_app(cfg: Config | None = None, agente: Agente | None = None) -> FastAPI:
    cfg = cfg or cargar()
    agente = agente or construir_agente(cfg)
    app = FastAPI(title="Bot de trading BTC/USDT con LLM local", version=__version__,
                  description="Agente académico en modo Paper: MEXC (datos públicos) + MLP + Ollama local.")
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_methods=["GET", "POST"], allow_headers=["X-API-Key", "Content-Type"])
    app.state.agente = agente

    def verificar_clave(x_api_key: str = Header(default="")) -> None:
        if not secrets.compare_digest(x_api_key.encode(), cfg.api_key.encode()):
            agente.bd.error("api", "Clave incorrecta o ausente en X-API-Key")
            raise HTTPException(status_code=401, detail="Clave incorrecta")

    auth = [Depends(verificar_clave)]

    @app.get("/api/salud")
    def salud():
        return {"ok": True, "version": __version__, "modo": cfg.modo}

    @app.get("/api/estado", dependencies=auth)
    def estado():
        return agente.resumen()

    @app.post("/api/control/{accion}", dependencies=auth)
    def control(accion: str):
        acciones = {"iniciar": agente.iniciar, "pausar": agente.pausar, "detener": agente.detener}
        if accion not in acciones:
            raise HTTPException(status_code=400, detail=f"Acción no válida: {accion}")
        return {"estado": acciones[accion]()}

    @app.post("/api/ciclo", dependencies=auth)
    def ciclo():
        if agente.estado == "DETENIDO":
            raise HTTPException(status_code=409, detail="El bot está detenido: inícialo antes de ejecutar un ciclo.")
        return agente.ciclo()

    @app.get("/api/llm", dependencies=auth)
    def llm():
        try:
            return agente.llm.info()
        except OllamaError as e:
            agente.bd.error("llm", e)
            raise HTTPException(status_code=503, detail=str(e))

    @app.get("/api/decisiones", dependencies=auth)
    def decisiones(n: int = 30):
        return agente.bd.decisiones(min(n, 500))

    @app.get("/api/ordenes", dependencies=auth)
    def ordenes(n: int = 30):
        return agente.bd.ordenes(min(n, 500))

    @app.get("/api/errores", dependencies=auth)
    def errores(n: int = 30):
        return agente.bd.errores(min(n, 500))

    @app.get("/api/patrimonio", dependencies=auth)
    def patrimonio(n: int = 365):
        return agente.bd.curva_patrimonio(min(n, 5000))

    return app

