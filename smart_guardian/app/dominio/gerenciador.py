"""Gerenciador central: detecção, escada de alertas e cancelamento.

Aplica princípios de POO:
- Encapsulamento do estado de emergência
- Injeção de dependência (repositório + canal de mensageria)
- Strategy via CanalMensageria
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from threading import RLock

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.dominio.contato import Contato, NivelAlerta, StatusContato
from app.dominio.repositorio import RepositorioContatos
from app.servicos.whatsapp import CanalMensageria

logger = logging.getLogger(__name__)

_JOB_NIVEL_1 = "alerta_n1"
_JOB_NIVEL_2 = "alerta_n2"
_JOB_NIVEL_3 = "alerta_n3"

class GerenciadorAlertas:
    def __init__(
        self,
        repositorio: RepositorioContatos,
        canal: CanalMensageria,
        scheduler: BackgroundScheduler | None = None,
    ) -> None:
        self._repo = repositorio
        self._canal = canal
        self._scheduler = scheduler or BackgroundScheduler(timezone="UTC")
        if not self._scheduler.running:
            self._scheduler.start()

        self._lock = RLock()
        self._emergencia_ativa: bool = False
        self._inicio_deteccao: datetime | None = None

    # ---------- Cadastro e WhatsApp ----------
    def cadastrar(self, nome: str, telefone: str, nivel: NivelAlerta) -> Contato:
        contato = Contato(nome=nome, telefone=telefone, nivel=nivel)
        self._repo.salvar(contato)
        try:
            self._canal.enviar(
                contato.whatsapp_to,
                f"Olá {nome}! Cadastro no Smart Guardian como {nivel.value}. Responda *SIM* para ativar."
            )
        except Exception as e:
            logger.warning("Falha ao enviar mensagem de validação: %s", e)
        return contato

    def verificar_por_telefone(self, telefone: str, corpo: str) -> bool:
        if corpo.strip().upper() != "SIM":
            return False
        contato = self._repo.buscar_por_telefone(telefone)
        if not contato:
            return False
        contato.marcar_verificado()
        self._repo.salvar(contato)
        # Mantendo a mensagem que você gosta:
        self._canal.enviar(contato.whatsapp_to, f"Pronto, {contato.nome}! Cadastro ativado.")
        return True

    def processar_mensagem_whatsapp(self, telefone: str, corpo: str) -> str:
        comando = corpo.strip().upper()
        
        if comando == "PARAR":
            res = self.cancelar_emergencia(motivo=f"Cancelado por {telefone}")
            if res["status"] == "cancelada":
                return "Emergência cancelada. O monitoramento continua ativo."
            return "Nenhuma emergência ativa para cancelar."
        
        if self.verificar_por_telefone(telefone, corpo):
            return "Você será notificado em caso de emergência. Obrigado por confirmar!" 
            
        return "Comando não reconhecido."

    # ---------- Detecção e escada de alertas ----------
    def iniciar_emergencia(self) -> dict:
        with self._lock:
            if self._emergencia_ativa:
                return {"status": "ja_ativa"}

            self._emergencia_ativa = True
            self._inicio_deteccao = datetime.utcnow()
            s = get_settings()

            msg_cancelar = "\n\n(Digite 'PARAR' para cancelar esta emergência)"
            
            self._agendar(_JOB_NIVEL_1, s.alerta_nivel_1_seg, NivelAlerta.PRIMARIO,
                          "🚨 ALERTA: Criança detectada sozinha no veículo." + msg_cancelar)
            self._agendar(_JOB_NIVEL_2, s.alerta_nivel_2_seg, NivelAlerta.EMERGENCIAL,
                          "⚠️ NÍVEL 2: A criança continua sozinha. Aja agora!" + msg_cancelar)
            self._agendar(_JOB_NIVEL_3, s.alerta_nivel_3_seg, NivelAlerta.CRITICO,
                          "🆘 CRÍTICO: Acionando contatos de segurança!" + msg_cancelar)
            
            # LOGS DE MONITORAMENTO NO SERVIDOR
            logger.info(">>> EMERGÊNCIA INICIADA: Sistema detectou criança sozinha.")
            return {"status": "iniciada"}

    def cancelar_emergencia(self, motivo: str = "resgate_confirmado") -> dict:
        with self._lock:
            if not self._emergencia_ativa:
                return {"status": "sem_emergencia"}
            
            for job_id in (_JOB_NIVEL_1, _JOB_NIVEL_2, _JOB_NIVEL_3):
                if self._scheduler.get_job(job_id):
                    self._scheduler.remove_job(job_id)
            
            self._emergencia_ativa = False
            self._inicio_deteccao = None
            logger.info(">>> EMERGÊNCIA CANCELADA: %s", motivo)
            return {"status": "cancelada"}

    def status(self) -> dict:
        return {
            "emergencia_ativa": self._emergencia_ativa,
            "inicio": self._inicio_deteccao
        }

    # ---------- Internos ----------
    def _agendar(self, job_id: str, segundos: int, nivel: NivelAlerta, msg: str) -> None:
        self._scheduler.add_job(
            self._disparar_nivel,
            "date",
            run_date=datetime.utcnow() + timedelta(seconds=segundos),
            args=[nivel, msg],
            id=job_id,
            replace_existing=True,
        )

    def _disparar_nivel(self, nivel: NivelAlerta, mensagem: str) -> None:
        logger.info("Executando disparo de nível: %s", nivel.value)
        
        ordem = [NivelAlerta.PRIMARIO, NivelAlerta.EMERGENCIAL, NivelAlerta.CRITICO]
        niveis_alvo = set(ordem[: ordem.index(nivel) + 1])

        destinatarios = [
            c for c in self._repo.listar() 
            if c.status == StatusContato.VERIFICADO and c.nivel in niveis_alvo
        ]
        
        if not destinatarios:
            logger.warning("Nenhum contato verificado para nível %s", nivel.value)
            return

        for c in destinatarios:
            try:
                logger.info("Enviando alerta para: %s", c.nome)
                self._canal.enviar(c.whatsapp_to, mensagem)
            except Exception as e:
                logger.error("Falha enviando alerta para %s: %s", c.telefone, e)