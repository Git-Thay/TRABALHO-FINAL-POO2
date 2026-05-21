from fastapi import FastAPI
from app.api.rotas import router
import uvicorn

app = FastAPI(
    title="Smart Guardian API",
    description="Sistema de Monitoramento e Alertas para Prevenção de Esquecimento de Crianças em Veículos",
    version="1.0.0"
)

# Inclui todas as rotas (Cadastro de contatos, Webhook do WhatsApp e Simulação da IA)
app.include_router(router)

if __name__ == "__main__":
    print("[Sistema] Ligando o servidor Uvicorn na porta 8000...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)