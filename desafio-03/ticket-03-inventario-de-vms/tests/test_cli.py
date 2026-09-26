import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from inventario_vm import cli, conexao
from inventario_vm.erros import HostInalcancavel
from tests.amostras import COM_SWAP, SessaoFalsa, saidas_conforme


@pytest.fixture
def chave(tmp_path):
    privada = ed25519.Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH,
        serialization.NoEncryption(),
    )
    caminho = tmp_path / "id_coleta_segredo"
    caminho.write_bytes(privada)
    return caminho


def _argv(chave, *extra):
    return ["--host", "10.42.7.14", "--usuario", "coleta", "--chave", str(chave), *extra]


def _rodar(capsys, argv):
    codigo = cli.main(argv)
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


@pytest.fixture
def host(monkeypatch):
    """Troca a conexão real por uma sessão falsa; devolve o dicionário de saídas para ajuste."""
    saidas = saidas_conforme()
    chamadas = {}

    def conectar(endereco, porta, usuario, chave, esperado):
        chamadas["conectou"] = True
        return SessaoFalsa(saidas)

    monkeypatch.setattr(conexao, "conectar", conectar)
    return saidas, chamadas


def test_execucao_com_desvio_gera_os_dois_formatos(capsys, tmp_path, chave, host):
    saidas, _ = host
    saidas["swap"] = COM_SWAP
    destino = tmp_path / "rel.json"
    codigo, out, err = _rodar(capsys, _argv(chave, "--json", str(destino)))
    assert codigo == 1
    assert err == ""
    dado = json.loads(destino.read_text(encoding="utf-8"))
    instante = dado["host"]["coletado_em"]
    assert f"Coletado em {instante.replace('T', ' ')[:16]} UTC" in out
    assert "| crítico | swap.habilitado |" in out
    assert not out.lstrip().startswith("{")


def test_sem_arquivo_json_so_markdown(capsys, tmp_path, chave, host, monkeypatch):
    monkeypatch.chdir(tmp_path)
    codigo, out, _ = _rodar(capsys, _argv(chave))
    assert codigo == 4
    assert out.startswith("# Inventário")
    assert [p.name for p in tmp_path.iterdir()] == [chave.name]


@pytest.mark.parametrize("argv_extra, trecho", [
    (["--fingerprint", "md5:aa"], "--fingerprint"),
    (["--porta", "0"], "--porta"),
    (["--json", "/nao/existe/rel.json"], "--json"),
])
def test_erro_de_uso_nao_conecta(capsys, chave, host, argv_extra, trecho):
    _, chamadas = host
    codigo, out, err = _rodar(capsys, _argv(chave, *argv_extra))
    assert codigo == 2
    assert out == ""
    assert trecho in err
    assert "conectou" not in chamadas


def test_parametro_obrigatorio_ausente(capsys, host):
    codigo, _, err = _rodar(capsys, ["--host", "h", "--chave", "k"])
    assert codigo == 2
    assert "--usuario" in err


def test_chave_com_passphrase(capsys, tmp_path, host):
    privada = ed25519.Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH,
        serialization.BestAvailableEncryption(b"segredo"),
    )
    caminho = tmp_path / "id_protegida"
    caminho.write_bytes(privada)
    codigo, _, err = _rodar(capsys, _argv(caminho))
    assert codigo == 2
    assert "passphrase" in err
    assert str(caminho) not in err and caminho.name not in err


def test_chave_inexistente_nao_mostra_o_caminho(capsys, tmp_path, host):
    caminho = tmp_path / "id_nao_existe"
    codigo, _, err = _rodar(capsys, _argv(caminho))
    assert codigo == 2
    assert "--chave" in err and caminho.name not in err


def test_host_inalcancavel_preserva_json_anterior(capsys, tmp_path, chave, monkeypatch):
    def conectar(*_a, **_k):
        raise HostInalcancavel("o host não respondeu em 6 s")

    monkeypatch.setattr(conexao, "conectar", conectar)
    destino = tmp_path / "rel.json"
    destino.write_text("anterior", encoding="utf-8")
    codigo, out, err = _rodar(capsys, _argv(chave, "--json", str(destino)))
    assert codigo == 3
    assert out == ""
    assert err == "host inalcançável: o host não respondeu em 6 s\n"
    assert destino.read_text(encoding="utf-8") == "anterior"


def test_conexao_perdida_na_coleta_nao_gera_relatorio(capsys, tmp_path, chave, monkeypatch):
    class Caindo(SessaoFalsa):
        def executar(self, comando):
            if len(self.comandos) == 3:
                raise HostInalcancavel("a conexão caiu durante a coleta")
            return super().executar(comando)

    sessao = Caindo(saidas_conforme())
    monkeypatch.setattr(conexao, "conectar", lambda *a, **k: sessao)
    destino = tmp_path / "rel.json"
    codigo, out, err = _rodar(capsys, _argv(chave, "--json", str(destino)))
    assert (codigo, out) == (3, "")
    assert "caiu durante a coleta" in err
    assert not destino.exists()
    assert sessao.fechada


def test_erro_interno_sem_stack_trace_nem_caminho(capsys, chave, monkeypatch):
    def conectar(*_a, **_k):
        raise RuntimeError(f"algo quebrou lendo {chave}")

    monkeypatch.setattr(conexao, "conectar", conectar)
    codigo, out, err = _rodar(capsys, _argv(chave))
    assert codigo == cli.ERRO_INTERNO
    assert err == "erro interno: RuntimeError\n"
    assert "Traceback" not in err


def test_conteudo_da_chave_nao_aparece_em_nenhuma_saida(capsys, tmp_path, chave, host):
    destino = tmp_path / "rel.json"
    _, out, err = _rodar(capsys, _argv(chave, "--json", str(destino)))
    tudo = out + err + destino.read_text(encoding="utf-8")
    for linha in chave.read_text().splitlines():
        if "-----" not in linha:
            assert linha not in tudo
    assert chave.name not in tudo
