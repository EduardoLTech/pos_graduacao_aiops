"""Ferramenta de ponta a ponta contra o servidor SSH em processo (PRD P7–P11, I2, I6)."""

import json
import time

import paramiko
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from inventario_vm import cli, conexao
from inventario_vm.coleta import LEITURAS, PREFIXO
from inventario_vm.erros import HostInalcancavel
from tests.amostras import saidas_conforme
from tests.servidor_ssh import ServidorSSH

POR_COMANDO = {PREFIXO + c: n for n, c in LEITURAS.items()}


def _gerar_chave(tmp_path, nome):
    privada = ed25519.Ed25519PrivateKey.generate()
    caminho = tmp_path / nome
    caminho.write_bytes(privada.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH,
        serialization.NoEncryption(),
    ))
    return caminho, paramiko.Ed25519Key.from_private_key_file(str(caminho))


@pytest.fixture
def cenario(tmp_path):
    caminho, chave = _gerar_chave(tmp_path, "id_coleta_segredo")
    saidas = saidas_conforme()
    especiais = {}

    def responder(comando):
        nome = POR_COMANDO[comando]
        if nome in especiais:
            return especiais[nome]
        return ("saida", saidas[nome], 0)

    servidor = ServidorSSH(chave, responder)
    yield servidor, caminho, chave, especiais
    servidor.fechar()


def _argv(servidor, caminho, *extra):
    return ["--host", "127.0.0.1", "--porta", str(servidor.porta), "--usuario", "coleta",
            "--chave", str(caminho), *extra]


def test_execucao_completa_com_fingerprint_que_confere(capsys, tmp_path, cenario):
    servidor, caminho, _, _ = cenario
    fp = conexao.fingerprint(servidor.chave_de_host)
    destino = tmp_path / "rel.json"
    codigo = cli.main(_argv(servidor, caminho, "--fingerprint", fp, "--json", str(destino)))
    saida = capsys.readouterr()
    assert (codigo, saida.err) == (4, "")
    dado = json.loads(destino.read_text(encoding="utf-8"))
    assert dado["host"]["chave_de_host"] == f"ssh-rsa {fp}"
    assert f"chave de host ssh-rsa {fp}" in saida.out
    assert len(dado["conformidade"]) == 11


def test_fingerprint_divergente(capsys, tmp_path, cenario):
    servidor, caminho, _, _ = cenario
    errado = "SHA256:" + "B" * 43
    destino = tmp_path / "rel.json"
    codigo = cli.main(_argv(servidor, caminho, "--fingerprint", errado, "--json", str(destino)))
    saida = capsys.readouterr()
    assert (codigo, saida.out) == (3, "")
    assert errado in saida.err and conexao.fingerprint(servidor.chave_de_host) in saida.err
    assert not destino.exists()


def test_chave_recusada(capsys, tmp_path, cenario):
    servidor, _, _, _ = cenario
    outra, _ = _gerar_chave(tmp_path, "id_outra")
    codigo = cli.main(_argv(servidor, outra))
    saida = capsys.readouterr()
    assert (codigo, saida.out) == (3, "")
    assert saida.err == "host inalcançável: autenticação recusada: o host não aceitou a chave para este usuário\n"


def test_leitura_lenta_estoura_o_limite_de_tempo(cenario, monkeypatch):
    servidor, _, chave, especiais = cenario
    monkeypatch.setattr(conexao, "LIMITE_TEMPO_LEITURA", 1.0)
    especiais["portas"] = ("dorme", 5)
    sessao = conexao.conectar("127.0.0.1", servidor.porta, "coleta", chave, None)
    try:
        inicio = time.monotonic()
        resultado = sessao.executar(PREFIXO + LEITURAS["portas"])
        assert time.monotonic() - inicio < 3
        assert resultado.limite_excedido == "tempo"
        # a sessão continua utilizável para as leituras seguintes
        assert sessao.executar(PREFIXO + LEITURAS["kernel"]).saida == "6.8.0-1015-gcp\n"
    finally:
        sessao.fechar()


def test_leitura_grande_demais(capsys, cenario):
    servidor, caminho, _, especiais = cenario
    especiais["unidades"] = ("grande", 2 * 1024 * 1024)
    codigo = cli.main(_argv(servidor, caminho))
    saida = capsys.readouterr()
    assert codigo == 4
    assert "| servicos.ativos | falha de coleta: limite excedido (tamanho) |" in saida.out


def test_conexao_derrubada_no_meio_da_coleta(capsys, tmp_path, cenario):
    servidor, caminho, _, especiais = cenario
    especiais["swap"] = ("derruba",)
    destino = tmp_path / "rel.json"
    codigo = cli.main(_argv(servidor, caminho, "--json", str(destino)))
    saida = capsys.readouterr()
    assert (codigo, saida.out) == (3, "")
    assert saida.err == "host inalcançável: a conexão caiu durante a coleta\n"
    assert not destino.exists()


def test_agente_de_chaves_nao_e_usado(tmp_path, cenario, monkeypatch):
    """Com a chave errada, nem um agente com a chave certa faz a autenticação passar (I6)."""
    servidor, _, chave_certa, _ = cenario

    class AgenteFalso:
        def get_keys(self):
            return [chave_certa]

    monkeypatch.setattr(paramiko.client, "Agent", AgenteFalso)
    _, errada = _gerar_chave(tmp_path, "id_errada")
    with pytest.raises(HostInalcancavel, match="autenticação recusada"):
        conexao.conectar("127.0.0.1", servidor.porta, "coleta", errada, None)


def test_nada_da_chave_em_nenhuma_saida(capsys, tmp_path, cenario):
    servidor, caminho, _, especiais = cenario
    textos = []
    for extra, ajuste in (
        ([], None),
        (["--fingerprint", "SHA256:" + "C" * 43], None),
        ([], ("swap", ("derruba",))),
    ):
        especiais.clear()
        if ajuste:
            especiais[ajuste[0]] = ajuste[1]
        destino = tmp_path / f"r{len(textos)}.json"
        cli.main(_argv(servidor, caminho, "--json", str(destino), *extra))
        saida = capsys.readouterr()
        textos.append(saida.out + saida.err + (destino.read_text("utf-8") if destino.exists() else ""))
    tudo = "".join(textos)
    for linha in caminho.read_text().splitlines():
        if "-----" not in linha:
            assert linha not in tudo
    assert caminho.name not in tudo and str(caminho.parent) not in tudo
