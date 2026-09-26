import copy

import pytest
import yaml

from inventario_vm import baseline
from inventario_vm.erros import ErroDeUso


def _dado():
    return yaml.safe_load(baseline.CAMINHO_PADRAO.read_text(encoding="utf-8"))


def test_baseline_padrao_tem_11_regras_na_ordem_do_arquivo():
    b = baseline.carregar()
    assert b.versao == 1
    assert b.regras == (
        "so.distribuicao", "so.versao_minima", "kernel.versao_minima",
        "servicos.ativos", "servicos.proibidos", "swap.habilitado",
        "portas_em_escuta.publicas_permitidas", "portas_em_escuta.somente_rede_interna",
        "chaves_ssh.emitidas_por", "ssh.login_de_root", "ntp.sincronizado",
    )
    assert b.severidade["swap.habilitado"] == "critico"
    assert b.severidade["kernel.versao_minima"] == "medio"


@pytest.mark.parametrize("alterar, trecho", [
    (lambda d: d.update(versao=2), "versao 1"),
    (lambda d: d["esperado"]["so"].update(codinome="noble"), "regra desconhecida"),
    (lambda d: d["esperado"].pop("ntp"), "regra ausente"),
    (lambda d: d["esperado"]["swap"].update(habilitado="nao"), "swap.habilitado"),
    (lambda d: d["severidade"]["alto"].append("swap.habilitado"), "duas severidades"),
    (lambda d: d["severidade"]["medio"].remove("ntp.sincronizado"), "sem severidade"),
])
def test_baseline_invalido_e_erro_de_uso(alterar, trecho):
    dado = copy.deepcopy(_dado())
    alterar(dado)
    with pytest.raises(ErroDeUso, match=trecho):
        baseline.validar(dado)


def test_arquivo_inexistente(tmp_path):
    with pytest.raises(ErroDeUso, match="--baseline"):
        baseline.carregar(tmp_path / "nao-existe.yaml")


def test_yaml_quebrado(tmp_path):
    arquivo = tmp_path / "b.yaml"
    arquivo.write_text("versao: [1", encoding="utf-8")
    with pytest.raises(ErroDeUso, match="YAML"):
        baseline.carregar(arquivo)
