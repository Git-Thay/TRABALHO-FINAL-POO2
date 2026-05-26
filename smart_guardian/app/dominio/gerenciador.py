"""Gerenciador central: detecção, escada de alertas e cancelamento.

Aplica princípios de POO:
- Encapsulamento do estado de emergência
- Injeção de dependência (repositório + canal de mensageria)
- Strategy via CanalMensageria
"""
from __future__ import annotations

import logging
from datetime import datetime
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
    """Mantém o estado de emergência e dispara a escada via APScheduler."""

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

    # ---------- Cadastro / verificação ----------
    def cadastrar(self, nome: str, telefone: str, nivel: NivelAlerta) -> Contato:
        contato = Contato(nome=nome, telefone=telefone, nivel=nivel)
        self._repo.salvar(contato)
        try:
            self._canal.enviar(
                contato.whatsapp_to,
                f"Olá {nome}! Você foi cadastrado(a) no Smart Guardian como contato "
                f"de nível {nivel.value}. Responda *SIM* para ativar.",
            )
        except Exception as e:  # noqa: BLE001
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
        self._canal.enviar(
            contato.whatsapp_to,
            f"Pronto, {contato.nome}! Cadastro ativado. Você receberá alertas do Smart Guardian.",
        )
        return True

    # ---------- Detecção e escada ----------
    def iniciar_emergencia(self) -> dict:
        """Chamado quando a IA detecta `crianca_sozinha=True`."""
        with self._lock:
            if self._emergencia_ativa:
                return {"status": "ja_ativa", "inicio": self._inicio_deteccao}

            self._emergencia_ativa = True
            self._inicio_deteccao = datetime.utcnow()
            s = get_settings()

            self._agendar(_JOB_NIVEL_1, s.alerta_nivel_1_seg, NivelAlerta.PRIMARIO,
                          "🚨 ALERTA: criança detectada sozinha no veículo.")
            self._agendar(_JOB_NIVEL_2, s.alerta_nivel_2_seg, NivelAlerta.EMERGENCIAL,
                          "⚠️ NÍVEL 2: situação persiste há 5 minutos. Aja agora.")
            self._agendar(_JOB_NIVEL_3, s.alerta_nivel_3_seg, NivelAlerta.CRITICO,
                          "🆘 CRÍTICO: 8 minutos sem resgate. Acionando contatos críticos.")
            logger.info("Emergência iniciada em %s", self._inicio_deteccao)
            return {"status": "iniciada", "inicio": self._inicio_deteccao}

    def cancelar_emergencia(self, motivo: str = "resgate_confirmado") -> dict:
        """Interrompe a escada de alertas (rota de cancelamento da API)."""
        with self._lock:
            if not self._emergencia_ativa:
                return {"status": "sem_emergencia"}
            for job_id in (_JOB_NIVEL_1, _JOB_NIVEL_2, _JOB_NIVEL_3):
                job = self._scheduler.get_job(job_id)
                if job:
                    job.remove()
            self._emergencia_ativa = False
            inicio = self._inicio_deteccao
            self._inicio_deteccao = None
            logger.info("Emergência cancelada (%s)", motivo)
            return {"status": "cancelada", "motivo": motivo, "iniciada_em": inicio}

    def status(self) -> dict:
        return {
            "emergencia_ativa": self._emergencia_ativa,
            "inicio": self._inicio_deteccao,
            "jobs_agendados": [j.id for j in self._scheduler.get_jobs()],
        }

    # ---------- Internos ----------
    def _agendar(self, job_id: str, segundos: int, nivel: NivelAlerta, msg: str) -> None:
        from datetime import timedelta
        self._scheduler.add_job(
            self._disparar_nivel,
            "date",
            run_date=datetime.utcnow() + timedelta(seconds=segundos),
            args=[nivel, msg],
            id=job_id,
            replace_existing=True,
        )

    def _disparar_nivel(self, nivel: NivelAlerta, mensagem: str) -> None:
        """Envia a mensagem para todos os contatos do nível indicado (e inferiores)."""
        ordem = [NivelAlerta.PRIMARIO, NivelAlerta.EMERGENCIAL, NivelAlerta.CRITICO]
        niveis_alvo = set(ordem[: ordem.index(nivel) + 1])

        destinatarios = [
            c for c in self._repo.listar_verificados() if c.nivel in niveis_alvo
        ]
        if not destinatarios:
            logger.warning("Nenhum contato verificado para nível %s", nivel.value)
            return

        for c in destinatarios:
            try:
                self._canal.enviar(c.whatsapp_to, mensagem)
            except Exception as e:  # noqa: BLE001
                logger.error("Falha enviando alerta para %s: %s", c.telefone, e)
