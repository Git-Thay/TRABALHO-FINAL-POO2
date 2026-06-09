"""Endpoints FastAPI: cadastro, webhook Twilio, simulação de detecção e cancelamento."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.dominio.contato import NivelAlerta
from app.dominio.gerenciador import GerenciadorAlertas
from app.dominio.repositorio import RepositorioContatos

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------- Schemas ----------
class CadastroIn(BaseModel):
    nome: str = Field(..., min_length=1, max_length=80)
    telefone: str = Field(..., pattern=r"^\+\d{8,15}$", description="E.164, ex: +5511999999999")
    nivel: NivelAlerta

class ContatoOut(BaseModel):
    id: str
    nome: str
    telefone: str
    nivel: NivelAlerta
    status: str

# ---------- Dependências ----------
def get_gerenciador() -> GerenciadorAlertas: raise NotImplementedError
def get_repositorio() -> RepositorioContatos: raise NotImplementedError

# ---------- Rotas ----------
@router.post("/contatos", response_model=ContatoOut, status_code=201)
def cadastrar_contato(payload: CadastroIn, ger: GerenciadorAlertas = Depends(get_gerenciador)):
    c = ger.cadastrar(payload.nome, payload.telefone, payload.nivel)
    return ContatoOut(id=c.id, nome=c.nome, telefone=c.telefone, nivel=c.nivel, status=c.status.value)

@router.get("/contatos", response_model=list[ContatoOut])
def listar_contatos(repo: RepositorioContatos = Depends(get_repositorio)):
    return [ContatoOut(id=c.id, nome=c.nome, telefone=c.telefone, nivel=c.nivel, status=c.status.value) for c in repo.listar()]

@router.delete("/contatos/{contato_id}", status_code=204)
def remover_contato(contato_id: str, repo: RepositorioContatos = Depends(get_repositorio)):
    if not repo.remover(contato_id): raise HTTPException(404, "contato não encontrado")

# ---------- Webhook Twilio Corrigido ----------
@router.post("/whatsapp/webhook") 
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    ger: GerenciadorAlertas = Depends(get_gerenciador),
):
    telefone = From.replace("whatsapp:", "").strip()
    verificado = ger.verificar_por_telefone(telefone, Body)
    twiml = "<?xml version='1.0' encoding='UTF-8'?><Response/>"
    logger.info("webhook From=%s Body=%r verificado=%s", From, Body, verificado)
    return Response(content=twiml, media_type="application/xml")

# ---------- Detecção e Emergência ----------
@router.post("/deteccao/simular")
def simular_deteccao(crianca_sozinha: bool = True, ger: GerenciadorAlertas = Depends(get_gerenciador)):
    return ger.iniciar_emergencia() if crianca_sozinha else ger.cancelar_emergencia(motivo="simulacao_fim")

@router.post("/deteccao/frame")
async def detectar_frame(frame: UploadFile = File(...), ger: GerenciadorAlertas = Depends(get_gerenciador)):
    import numpy as np
    import cv2
    from app.ia.detector_yolo import DetectorYOLO

    dados = await frame.read()
    arr = np.frombuffer(dados, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None: raise HTTPException(400, "imagem inválida")

    detector = DetectorYOLO()
    try:
        sozinha = detector.detectar_crianca_sozinha(img)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))

    if sozinha: ger.iniciar_emergencia()
    return {"crianca_sozinha": sozinha, "estado": ger.status()}

@router.post("/emergencia/cancelar")
def cancelar_emergencia(motivo: str = "resgate_confirmado", ger: GerenciadorAlertas = Depends(get_gerenciador)):
    return ger.cancelar_emergencia(motivo=motivo)

@router.get("/emergencia/status")
def status_emergencia(ger: GerenciadorAlertas = Depends(get_gerenciador)):
    return ger.status()