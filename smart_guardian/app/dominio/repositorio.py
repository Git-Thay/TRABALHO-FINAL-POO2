"""Repositório em memória (pode ser trocado por SQLAlchemy sem afetar o domínio)."""
from __future__ import annotations
from threading import RLock
from typing import Iterable
from .contato import Contato, StatusContato

class RepositorioContatos:
    def __init__(self) -> None:
        self._dados: dict[str, Contato] = {}
        self._lock = RLock()

    def salvar(self, contato: Contato) -> Contato:
        with self._lock:
            self._dados[contato.id] = contato
            return contato

    def obter(self, contato_id: str) -> Contato | None:
        return self._dados.get(contato_id)

    def buscar_por_telefone(self, telefone: str) -> Contato | None:
        for c in self._dados.values():
            if c.telefone == telefone:
                return c
        return None

    def listar(self) -> list[Contato]:
        return list(self._dados.values())

    def remover(self, contato_id: str) -> bool:
        with self._lock:
            return self._dados.pop(contato_id, None) is not None