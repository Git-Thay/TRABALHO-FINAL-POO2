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

class CadastroIn(BaseModel):
    nome: str = Field(..., min_length=1, max_length=80)
    # Validação relaxada para aceitar qualquer formato de telefone enviado pelo front
    telefone: str 
    nivel: NivelAlerta

class ContatoOut(BaseModel):
    id: str
    nome: str
    telefone: str
    nivel: NivelAlerta
    status: str

def get_gerenciador() -> GerenciadorAlertas: raise NotImplementedError
def get_repositorio() -> RepositorioContatos: raise NotImplementedError

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

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(From: str = Form(...), Body: str = Form(...), ger: GerenciadorAlertas = Depends(get_gerenciador)):
    telefone = From.replace("whatsapp:", "").strip()
    verificado = ger.verificar_por_telefone(telefone, Body)
    return Response(content="<?xml version='1.0' encoding='UTF-8'?><Response/>", media_type="application/xml")

@router.post("/deteccao/frame")
async def detectar_frame(frame: UploadFile = File(...), ger: GerenciadorAlertas = Depends(get_gerenciador)):
    import numpy as np
    
    # 1. Lê os bytes e transforma em array numérico 
    dados = await frame.read()
    arr = np.frombuffer(dados, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    
    if img is None: 
        raise HTTPException(400, "imagem inválida")

    # 2. Log para verificar o que a IA está recebendo
    logger.info(f"Frame recebido: {img.shape}")

    try:
        # 3. Executa a detecção
        sozinha = detector.detectar_crianca_sozinha(img)
        
        # 4. Log para ver a decisão da IA
        logger.info(f"IA detectou criança sozinha? {sozinha}")
        
    except Exception as e:
        logger.error(f"Erro na IA: {e}")
        raise HTTPException(503, str(e))

    if sozinha and ger.status() != "EMERGENCIA":
        ger.iniciar_emergencia()
        logger.info("Emergência iniciada via detecção.")
    
    return {"crianca_sozinha": bool(sozinha), "estado": ger.status()}

@router.post("/emergencia/cancelar")
def cancelar_emergencia(motivo: str = "resgate_confirmado", ger: GerenciadorAlertas = Depends(get_gerenciador)):
    return ger.cancelar_emergencia(motivo=motivo)

@router.get("/emergencia/status")
def status_emergencia(ger: GerenciadorAlertas = Depends(get_gerenciador)):
    return ger.status()