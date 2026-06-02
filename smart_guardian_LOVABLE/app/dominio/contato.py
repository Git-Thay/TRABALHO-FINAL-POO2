"""Entidade de domínio Contato + Enums (POO: encapsulamento e identidade)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class NivelAlerta(str, Enum):
    """Define a prioridade do contato na escada de alertas."""
    PRIMARIO = "primario"        # T+2min
    EMERGENCIAL = "emergencial"  # T+5min
    CRITICO = "critico"          # T+8min


class StatusContato(str, Enum):
    PENDENTE = "pendente"     # aguardando "SIM" no WhatsApp
    VERIFICADO = "verificado"
    INATIVO = "inativo"


@dataclass
class Contato:
    """Entidade de domínio. Telefone deve vir em E.164 (ex: +5511999999999)."""
    nome: str
    telefone: str
    nivel: NivelAlerta
    status: StatusContato = StatusContato.PENDENTE
    id: str = field(default_factory=lambda: str(uuid4()))
    criado_em: datetime = field(default_factory=datetime.utcnow)
    verificado_em: datetime | None = None

    # ---- comportamento de domínio ----
    def marcar_verificado(self) -> None:
        self.status = StatusContato.VERIFICADO
        self.verificado_em = datetime.utcnow()

    def desativar(self) -> None:
        self.status = StatusContato.INATIVO

    @property
    def whatsapp_to(self) -> str:
        return f"whatsapp:{self.telefone}"
