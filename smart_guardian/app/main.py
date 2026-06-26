"""Ponto de entrada FastAPI com persistência de dependências."""
from __future__ import annotations

import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api import rotas
from app.dominio.gerenciador import GerenciadorAlertas
from app.dominio.repositorio import RepositorioContatos
from app.servicos.whatsapp import CanalMensageria, WhatsAppFake, WhatsAppTwilio

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("smart_guardian")

# --- Instâncias Globais (Singleton) ---
# Isso garante que o mesmo banco (repositório) seja usado em todo o app
_REPO = RepositorioContatos()

def criar_app() -> FastAPI:
    app = FastAPI(
        title="Smart Guardian API",
        version="1.0.0",
        description="Monitoramento com YOLO + Twilio.",
    )

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    @app.get("/app")
    def read_index():
        return FileResponse("app/static/index.html")

    # Configuração do canal de mensagem
    canal: CanalMensageria
    if os.getenv("TWILIO_ACCOUNT_SID"):
        canal = WhatsAppTwilio()
        logger.info("Canal WhatsApp: Twilio")
    else:
        canal = WhatsAppFake()
        logger.warning("Canal WhatsApp: MODO FAKE")

    # Gerenciador único vinculado ao repositório único
    gerenciador = GerenciadorAlertas(_REPO, canal)

    # Injeção de dependência usando as instâncias globais
    app.dependency_overrides[rotas.get_repositorio] = lambda: _REPO
    app.dependency_overrides[rotas.get_gerenciador] = lambda: gerenciador

    app.include_router(rotas.router, prefix="/api")

    @app.get("/")
    def root():
        return {"app": "Smart Guardian", "docs": "/docs"}

    return app

app = criar_app()

if __name__ == "__main__":
    import uvicorn
    # A execução usa a string que aponta para o app nesta instância
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)