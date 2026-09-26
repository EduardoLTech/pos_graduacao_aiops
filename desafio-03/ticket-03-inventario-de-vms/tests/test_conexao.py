"""Conexão real até onde dá sem host: recusa local, nome inválido e política de chave de host."""

import socket
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from inventario_vm import conexao
from inventario_vm.erros import ErroDeUso, HostInalcancavel


@pytest.fixture
def chave(tmp_path):
    caminho = tmp_path / "id"
    caminho.write_bytes(ed25519.Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH,
        serialization.NoEncryption(),
    ))
    return conexao.carregar_chave(str(caminho))


def _porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_conexao_recusada(chave):
    porta = _porta_livre()
    inicio = time.monotonic()
    with pytest.raises(HostInalcancavel, match="conexão recusada"):
        conexao.conectar("127.0.0.1", porta, "coleta", chave, None)
    assert time.monotonic() - inicio < 15


def test_nome_que_nao_resolve(chave):
    with pytest.raises(HostInalcancavel, match="não resolve"):
        conexao.conectar("host-inexistente.invalid", 22, "coleta", chave, None)


def test_servico_que_nao_fala_ssh(chave):
    servidor = socket.socket()
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(1)
    porta = servidor.getsockname()[1]
    try:
        with pytest.raises(HostInalcancavel, match="não respondeu como servidor SSH"):
            conexao.conectar("127.0.0.1", porta, "coleta", chave, None)
    finally:
        servidor.close()


def test_formato_do_fingerprint():
    assert conexao.validar_fingerprint(None) is None
    valido = "SHA256:" + "a" * 43
    assert conexao.validar_fingerprint(valido) == valido
    for invalido in ("SHA256:curto", "MD5:" + "a" * 43, "a" * 50):
        with pytest.raises(ErroDeUso, match="--fingerprint"):
            conexao.validar_fingerprint(invalido)


def test_politica_registra_e_recusa_divergente(chave):
    fp = conexao.fingerprint(chave)
    assert fp.startswith("SHA256:") and len(fp) == 50

    politica = conexao._PoliticaDeChaveDeHost(None)
    politica.missing_host_key(None, "h", chave)
    assert (politica.algoritmo, politica.fingerprint) == ("ssh-ed25519", fp)

    politica = conexao._PoliticaDeChaveDeHost("SHA256:" + "B" * 43)
    with pytest.raises(conexao.ChaveDeHostDivergente):
        politica.missing_host_key(None, "h", chave)

    conexao._PoliticaDeChaveDeHost(fp).missing_host_key(None, "h", chave)


def test_arquivo_que_nao_e_chave(tmp_path):
    caminho = tmp_path / "texto"
    caminho.write_text("isto não é uma chave")
    with pytest.raises(ErroDeUso, match="formato"):
        conexao.carregar_chave(str(caminho))
