"""Camada de abstração da Twilio. Usa Strategy para permitir um fake em testes."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.config import get_settings

logger = logging.getLogger(__name__)


class CanalMensageria(ABC):
    @abstractmethod
    def enviar(self, para: str, mensagem: str) -> str: ...


class WhatsAppTwilio(CanalMensageria):
    """Implementação real usando Twilio Sandbox/Produção."""

    def __init__(self) -> None:
        s = get_settings()
        if not (s.twilio_account_sid and s.twilio_auth_token):
            raise RuntimeError(
                "Credenciais Twilio ausentes. Preencha TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN no .env"
            )
        self._client = Client(s.twilio_account_sid, s.twilio_auth_token)
        self._from = s.twilio_whatsapp_from

    def enviar(self, para: str, mensagem: str) -> str:
        """Envia mensagem WhatsApp. `para` deve ser 'whatsapp:+55...'."""
        try:
            msg = self._client.messages.create(
                from_=self._from, to=para, body=mensagem
            )
            logger.info("WhatsApp enviado sid=%s para=%s", msg.sid, para)
            return msg.sid
        except TwilioRestException as e:
            # Códigos comuns no Sandbox:
            # 63007 -> número não associado ao Sandbox (precisa enviar "join <code>")
            # 63016 -> fora da janela de 24h (precisa template aprovado)
            # 21610 -> destinatário fez opt-out
            logger.error("Falha Twilio code=%s msg=%s", e.code, e.msg)
            raise


class WhatsAppFake(CanalMensageria):
    """Para testes locais sem custo. Apenas guarda em memória."""
    def __init__(self) -> None:
        self.enviadas: list[tuple[str, str]] = []

    def enviar(self, para: str, mensagem: str) -> str:
        self.enviadas.append((para, mensagem))
        logger.info("[FAKE] -> %s | %s", para, mensagem)
        return f"FAKE-{len(self.enviadas)}"
