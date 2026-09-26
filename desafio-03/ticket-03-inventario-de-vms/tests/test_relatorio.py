import json

from inventario_vm import baseline, coleta, inventario, regras, relatorio
from tests.amostras import (
    COM_SWAP, SessaoFalsa, chave_publica, linha_de_chaves, saidas_conforme,
)

BASE = baseline.carregar()


def _relatorio(**trocas):
    saidas = saidas_conforme()
    saidas.update(trocas)
    resultado = inventario.montar(coleta.coletar(SessaoFalsa(saidas)))
    conformidade = regras.avaliar(BASE, resultado)
    host = {"endereco": "10.42.7.14", "hostname": resultado.hostname,
            "coletado_em": "2026-08-12T09:14:02Z", "chave_de_host": "ssh-ed25519 SHA256:abc"}
    return relatorio.montar(host, resultado.inventario, conformidade, regras.resumir(conformidade))


def _secoes(md):
    return md.split("\n## ")


def test_esqueleto_do_markdown_de_host_sem_desvio():
    md = relatorio.para_markdown(_relatorio(), 1)
    linhas = md.splitlines()
    assert linhas[0] == "# Inventário — construct-node-14 (10.42.7.14)"
    assert linhas[1] == "Coletado em 2026-08-12 09:14 UTC · baseline v1 · chave de host ssh-ed25519 SHA256:abc"
    titulos = [l for l in linhas if l.startswith("## ")]
    assert titulos == ["## Desvios", "## Não verificado", "## Conforme"]
    assert _secoes(md)[1].strip() == "Desvios\n\nNenhum."
    assert "| ssh.login_de_root | exige privilégio que o usuário da coleta não tem |" in md


def test_desvios_em_ordem_de_severidade_com_acento():
    md = relatorio.para_markdown(_relatorio(swap=COM_SWAP, kernel="5.15.0-118-generic\n"), 1)
    desvios = [l for l in _secoes(md)[1].splitlines() if l.startswith("| ") and "Severidade" not in l]
    assert desvios == [
        "| crítico | swap.habilitado | false | true (4G) |",
        "| médio | kernel.versao_minima | 6.5 | 5.15.0-118-generic |",
    ]


def test_json_e_markdown_do_mesmo_relatorio():
    rel = _relatorio(swap=COM_SWAP)
    dado = json.loads(relatorio.para_json(rel))
    assert dado["host"]["coletado_em"] == "2026-08-12T09:14:02Z"
    assert set(dado) == {"host", "inventario", "conformidade", "resumo"}
    swap = next(e for e in dado["conformidade"] if e["regra"] == "swap.habilitado")
    assert swap["severidade"] == "critico"


def test_comentario_hostil_nao_altera_a_estrutura():
    hostil = "neo\x1b[2K\n| x | conforme |\x9b‮"
    conteudo = chave_publica(hostil.replace("\n", " ")) + "\n"
    # A quebra de linha real divide a linha no authorized_keys; o \n aqui chega pelo nome da conta.
    chaves = "\n".join([linha_de_chaves("root\nfalso | conta", "lida", conteudo), "fim"])
    rel = _relatorio(chaves=chaves)
    md = relatorio.para_markdown(rel, 1)

    desvios = _secoes(md)[1].splitlines()
    linhas_de_tabela = [l for l in desvios if l.startswith("|")]
    assert len(linhas_de_tabela) == 3  # cabeçalho, separador e a linha de chaves
    linha = linhas_de_tabela[2]
    assert "\x1b" not in md and "\x9b" not in md and "‮" not in md
    assert "\\x1b[2K" in linha and "\\| x \\| conforme \\|" in linha
    assert linha.count(" | ") == 3  # quatro colunas, nenhuma a mais

    texto_json = relatorio.para_json(rel)
    assert not any(c in texto_json for c in "\x1b\x9b‮")
    dado = json.loads(texto_json)
    assert dado["inventario"]["chaves_ssh"][0]["conta"] == "root\nfalso | conta"


def test_celula_longa_e_cortada():
    assert relatorio.neutralizar("a" * 500).endswith("… (cortado)")


def test_gravar_json_em_erro_nao_toca_o_arquivo(tmp_path, monkeypatch):
    destino = tmp_path / "saida.json"
    destino.write_text("anterior", encoding="utf-8")

    def quebra(_rel):
        raise RuntimeError("falha")

    monkeypatch.setattr(relatorio, "para_json", quebra)
    try:
        relatorio.gravar_json({}, str(destino))
    except RuntimeError:
        pass
    assert destino.read_text(encoding="utf-8") == "anterior"
    assert list(tmp_path.iterdir()) == [destino]
