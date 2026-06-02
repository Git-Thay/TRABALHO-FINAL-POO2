"""Ponto de entrada FastAPI. Faz wiring (DI) das dependências."""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from app.api import rotas
from app.dominio.gerenciador import GerenciadorAlertas
from app.dominio.repositorio import RepositorioContatos
from app.servicos.whatsapp import CanalMensageria, WhatsAppFake, WhatsAppTwilio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("smart_guardian")


def criar_app() -> FastAPI:
    app = FastAPI(
        title="Smart Guardian API",
        version="1.0.0",
        description="Monitoramento de crianças em veículos com YOLO + WhatsApp (Twilio).",
    )

    repo = RepositorioContatos()

    canal: CanalMensageria
    if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"):
        canal = WhatsAppTwilio()
        logger.info("Canal WhatsApp: Twilio")
    else:
        canal = WhatsAppFake()
        logger.warning("Canal WhatsApp: FAKE (credenciais Twilio ausentes)")

    gerenciador = GerenciadorAlertas(repo, canal)

    # Sobrescreve as dependências do router
    app.dependency_overrides[rotas.get_repositorio] = lambda: repo
    app.dependency_overrides[rotas.get_gerenciador] = lambda: gerenciador

    app.include_router(rotas.router, prefix="/api")

    @app.get("/")
    def root():
        return {"app": "Smart Guardian", "docs": "/docs"}

    return app


app = criar_app()


if __name__ == "__main__":
    import uvicorn
    from app.config import get_settings
    s = get_settings()
    uvicorn.run("app.main:app", host=s.app_host, port=s.app_port, reload=True)
