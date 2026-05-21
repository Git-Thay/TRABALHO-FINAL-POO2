from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel, Field
from app.dominio.contato import Contato, NivelAlerta
from app.dominio.gerenciador import GerenciadorAlerta
from app.servicos.whatsapp import NotificadorWhatsApp

router = APIRouter()

notificador_global = NotificadorWhatsApp()
gerenciador_global = GerenciadorAlerta(notificador_global)

class ContatoRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=50)
    telefone: str = Field(..., description="Exemplo: 62999999999")
    nivel: int = Field(..., ge=1, le=3)

class DeteccaoRequest(BaseModel):
    detectou_crianca_sozinha: bool


@router.post("/contatos")
def cadastrar_contato(dados: ContatoRequest):
    try:
        nivel_enum = NivelAlerta(dados.nivel)
        novo_contato = Contato(nome=dados.nome, telefone=dados.telefone, nivel=nivel_enum)
        gerenciador_global.adicionar_contato(novo_contato)
        return {
            "mensagem": "Contato cadastrado com sucesso! Aguardando confirmação via WhatsApp.",
            "contato": novo_contato.obter_dados_resumidos()
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Nível de alerta inválido. Escolha entre 1, 2 ou 3.")

@router.get("/contatos")
def listar_contatos():
    try:
        # Se for um dicionário (ex: {telefone: objeto_contato})
        if isinstance(gerenciador_global.contatos, dict):
            contatos_do_sistema = gerenciador_global.contatos.values()
        # Se já for uma lista direta
        else:
            contatos_do_sistema = gerenciador_global.contatos

        lista = [c.obter_dados_resumidos() for c in contatos_do_sistema]
        return {"total": len(lista), "contatos": lista}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao listar: {str(e)}")

@router.post("/whatsapp/webhook")
def receber_resposta_whatsapp(From: str = Form(...), Body: str = Form(...)):
    telefone_remetente = From.replace("whatsapp:", "").strip()
    texto_recebido = Body.strip().upper()

    print(f"\n📥 [Webhook] Mensagem recebida de {telefone_remetente}: '{texto_recebido}'")

    if texto_recebido == "SIM":
        foi_atualizado = gerenciador_global.atualizar_status_verificacao(telefone_remetente)
        if foi_atualizado:
            return {"status": "sucesso", "mensagem": "Contato verificado com sucesso."}
        return {"status": "erro", "mensagem": "Número não encontrado no sistema."}
        
    return {"status": "ignorado", "mensagem": "Mensagem recebida não era um 'SIM'."}

@router.post("/ia/simular")
def simular_deteccao_ia(dados: DeteccaoRequest):
    """
    Rota que simula o envio de dados que a IA do YOLO fará.
    Permite ativar ou desativar o cronômetro manualmente para testes.
    """
    gerenciador_global.processar_deteccao(detectou_crianca_sozinha=dados.detectou_crianca_sozinha)
    
    status = "Emergência ATIVADA" if dados.detectou_crianca_sozinha else "Situação NORMALIZADA"
    return {
        "status": "sucesso",
        "acao": status,
        "detalhe": "Sinal enviado com sucesso para o gerenciador de alertas."
    }