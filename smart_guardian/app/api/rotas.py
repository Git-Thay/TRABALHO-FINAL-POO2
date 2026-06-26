"""Rotas FastAPI para o Smart Guardian."""
from __future__ import annotations

import logging
import numpy as np
import cv2
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.dominio.contato import NivelAlerta
from app.dominio.gerenciador import GerenciadorAlertas
from app.dominio.repositorio import RepositorioContatos
from app.ia.detector_yolo import DetectorYOLO

logger = logging.getLogger(__name__)
router = APIRouter()
detector = DetectorYOLO()

# --- Schemas ---
class CadastroIn(BaseModel):
    nome: str = Field(..., min_length=1, max_length=80)
    telefone: str 
    nivel: NivelAlerta

class ContatoOut(BaseModel):
    id: str
    nome: str
    telefone: str
    nivel: NivelAlerta
    status: str

# --- Dependências (Preenchidas via app/main.py) ---
def get_gerenciador() -> GerenciadorAlertas: raise NotImplementedError
def get_repositorio() -> RepositorioContatos: raise NotImplementedError

# --- Rotas de Contatos ---
@router.post("/contatos", response_model=ContatoOut, status_code=201)
def cadastrar_contato(payload: CadastroIn, ger: GerenciadorAlertas = Depends(get_gerenciador)):
    c = ger.cadastrar(payload.nome, payload.telefone, payload.nivel)
    return ContatoOut(id=c.id, nome=c.nome, telefone=c.telefone, nivel=c.nivel, status=c.status.value)

@router.get("/contatos", response_model=list[ContatoOut])
def listar_contatos(repo: RepositorioContatos = Depends(get_repositorio)):
    return [ContatoOut(id=c.id, nome=c.nome, telefone=c.telefone, nivel=c.nivel, status=c.status.value) for c in repo.listar()]

@router.delete("/contatos/{contato_id}", status_code=204)
def remover_contato(contato_id: str, repo: RepositorioContatos = Depends(get_repositorio)):
    if not repo.remover(contato_id): 
        raise HTTPException(404, "contato não encontrado")

# --- Webhook WhatsApp (Agora com cancelamento automático) ---
@router.post("/whatsapp/webhook")
async def whatsapp_webhook(From: str = Form(...), Body: str = Form(...), ger: GerenciadorAlertas = Depends(get_gerenciador)):
    telefone = From.replace("whatsapp:", "").strip()
    
    # Processa via gerenciador (verifica SIM ou PARAR)
    mensagem_resposta = ger.processar_mensagem_whatsapp(telefone, Body)
    
    xml = f"<Response><Message>{mensagem_resposta}</Message></Response>"
    return Response(content=xml, media_type="application/xml")

# --- Rotas de Monitoramento ---
@router.post("/deteccao/frame")
async def detectar_frame(frame: UploadFile = File(...), ger: GerenciadorAlertas = Depends(get_gerenciador)):
    dados = await frame.read()
    arr = np.frombuffer(dados, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    
    if img is None: 
        raise HTTPException(400, "imagem inválida")

    
    sozinha = detector.detectar_crianca_sozinha(img) 
    
    # LOGS DE MONITORAMENTO NO SERVIDOR
    if sozinha:
        logger.info("DETECÇÃO: Criança sozinha detectada!")
    else:
        logger.debug("DETECÇÃO: Ninguém detectado ou adulto presente.")

    status = ger.status()
    
    # Inicia emergência apenas se detectar criança sozinha
    if sozinha and not status["emergencia_ativa"]:
        logger.info(">>> EMERGÊNCIA INICIADA: Sistema detectou criança sozinha.")
        ger.iniciar_emergencia()
    
    return {"crianca_sozinha": bool(sozinha), "emergencia_ativa": status["emergencia_ativa"]}

@router.post("/emergencia/cancelar")
def cancelar_emergencia(motivo: str = "resgate_confirmado", ger: GerenciadorAlertas = Depends(get_gerenciador)):
    return ger.cancelar_emergencia(motivo=motivo)

@router.get("/emergencia/status")
def status_emergencia(ger: GerenciadorAlertas = Depends(get_gerenciador)):
    return ger.status()