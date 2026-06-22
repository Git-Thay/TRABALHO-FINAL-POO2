"""Testes unitários do gerenciador usando o canal fake."""
from app.dominio.contato import NivelAlerta, StatusContato
from app.dominio.gerenciador import GerenciadorAlertas
from app.dominio.repositorio import RepositorioContatos
from app.servicos.whatsapp import WhatsAppFake


def _novo_gerenciador():
    repo = RepositorioContatos()
    canal = WhatsAppFake()
    return GerenciadorAlertas(repo, canal), repo, canal


def test_cadastro_envia_mensagem_validacao():
    ger, repo, canal = _novo_gerenciador()
    c = ger.cadastrar("Ana", "+5511999999999", NivelAlerta.PRIMARIO)
    assert c.status == StatusContato.PENDENTE
    assert len(canal.enviadas) == 1
    assert "SIM" in canal.enviadas[0][1]


def test_verificacao_com_sim():
    ger, repo, canal = _novo_gerenciador()
    ger.cadastrar("Ana", "+5511999999999", NivelAlerta.PRIMARIO)
    ok = ger.verificar_por_telefone("+5511999999999", "sim")
    assert ok
    assert repo.buscar_por_telefone("+5511999999999").status == StatusContato.VERIFICADO


def test_cancelar_emergencia_remove_jobs():
    ger, *_ = _novo_gerenciador()
    ger.iniciar_emergencia()
    assert ger.status()["emergencia_ativa"]
    r = ger.cancelar_emergencia()
    assert r["status"] == "cancelada"
    assert not ger.status()["emergencia_ativa"]
