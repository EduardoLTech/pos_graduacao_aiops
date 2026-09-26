"""Regras sobre as saídas brutas gravadas na VM do laboratório (Ubuntu 24.04.5, 2026-09-26).

Diferente de amostras.py, escritas à mão: aqui está o formato real que os comandos devolvem.
"""

import json
from pathlib import Path

import pytest

from inventario_vm import baseline, coleta, inventario, regras
from inventario_vm.conexao import ResultadoComando
from tests.amostras import SessaoFalsa

PASTA = Path(__file__).with_name("amostras_lab")
BASE = baseline.carregar()


def _avaliar(estado):
    brutas = json.loads((PASTA / f"{estado}.json").read_text(encoding="utf-8"))
    saidas = {n: ResultadoComando(v["codigo"], v["saida"], v["limite"]) for n, v in brutas.items()}
    resultado = inventario.montar(coleta.coletar(SessaoFalsa(saidas)))
    return resultado, {e["regra"]: e for e in regras.avaliar(BASE, resultado)}


def test_estado_conforme():
    resultado, por_regra = _avaliar("conforme")
    vereditos = {r: e["veredito"] for r, e in por_regra.items()}
    assert vereditos == {
        **dict.fromkeys(BASE.regras, "conforme"),
        "chaves_ssh.emitidas_por": "nao_verificado",
        "ssh.login_de_root": "nao_verificado",
    }
    assert regras.codigo_de_saida(list(por_regra.values())) == 4
    inv = resultado.inventario
    assert inv["so"] == {"distribuicao": "ubuntu", "versao": "24.04.5"}
    assert inv["ntp"] == {"sincronizado": True, "mecanismo": "chrony"}
    assert {"porta": 9100, "bind": "10.10.0.2", "processo": None, "conta": "node_exporter",
            "unidade": "node_exporter.service"} in inv["portas_em_escuta"]
    assert inv["chaves_ssh"] == [{"identificacao": "coleta@metacortex-platform", "conta": "coleta"}]
    assert "root" in inv["chaves_ssh_fontes_nao_lidas"]


def test_estado_com_desvios():
    resultado, por_regra = _avaliar("desvios")
    desvios = {r: e["severidade"] for r, e in por_regra.items() if e["veredito"] == "desvio"}
    assert desvios == {
        "swap.habilitado": "critico",
        "portas_em_escuta.publicas_permitidas": "critico",  # rpcbind abre a 111
        "portas_em_escuta.somente_rede_interna": "critico",
        "chaves_ssh.emitidas_por": "critico",
        "servicos.ativos": "alto",
        "servicos.proibidos": "alto",
        "ntp.sincronizado": "medio",
    }
    assert por_regra["ssh.login_de_root"]["veredito"] == "nao_verificado"
    assert por_regra["swap.habilitado"]["encontrado_texto"] == "true (1G)"
    assert por_regra["portas_em_escuta.somente_rede_interna"]["encontrado"] == [{"porta": 9100, "bind": "*"}]
    assert por_regra["portas_em_escuta.publicas_permitidas"]["encontrado_texto"] == "111 em 0.0.0.0, 111 em ::"
    assert "neo\x1b[2K | x | conforme |" in por_regra["chaves_ssh.emitidas_por"]["encontrado"]
    rpcbind = next(p for p in resultado.inventario["portas_em_escuta"] if p["porta"] == 111)
    assert (rpcbind["conta"], rpcbind["unidade"]) == ("root", "rpcbind.socket")
    assert resultado.inventario["ntp"]["mecanismo"] is None


@pytest.mark.parametrize("estado", ["conforme", "desvios"])
def test_toda_leitura_real_foi_reconhecida(estado):
    resultado, _ = _avaliar(estado)
    falhas = {n: l.motivo for n, l in resultado.evidencia.items() if l.status == "falha"}
    assert falhas == {}
