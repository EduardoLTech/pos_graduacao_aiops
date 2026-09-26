"""Relatório em JSON e Markdown a partir do mesmo objeto (PRD P6, P15, P28, I7; design D7)."""

import json
import os
import tempfile
import unicodedata
from pathlib import Path

from inventario_vm.regras import DESVIO, NAO_VERIFICADO, CONFORME

ORDEM_SEVERIDADE = {"critico": 0, "alto": 1, "medio": 2}
SEVERIDADE_COM_ACENTO = {"critico": "crítico", "alto": "alto", "medio": "médio"}
TAMANHO_MAXIMO_CELULA = 200
_ESCAPES_VISIVEIS = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}


def montar(host: dict, inventario: dict, conformidade: list[dict], resumo: dict) -> dict:
    return {"host": host, "inventario": inventario, "conformidade": conformidade, "resumo": resumo}


# --- JSON --------------------------------------------------------------------------------


def _invisivel(c: str) -> bool:
    # Cc: controle (inclui C1, que alguns terminais interpretam); Cf: formatação invisível,
    # como inversão bidirecional.
    return unicodedata.category(c) in ("Cc", "Cf")


def para_json(relatorio: dict) -> str:
    # A frase de apresentação é só do Markdown; o JSON leva `encontrado` com tipo.
    conformidade = [
        {k: v for k, v in e.items() if k != "encontrado_texto"}
        for e in relatorio["conformidade"]
    ]
    texto = json.dumps({**relatorio, "conformidade": conformidade}, ensure_ascii=False, indent=2)
    # O json já escapa controles abaixo de 0x20 dentro de string; um \n cru restante só pode ser
    # estrutural (indentação). DEL, C1 e Cf passam crus com ensure_ascii=False: escapa-os aqui,
    # o que continua sendo JSON válido porque só ocorrem dentro de strings.
    return "".join(
        f"\\u{ord(c):04x}" if c != "\n" and _invisivel(c) else c for c in texto
    ) + "\n"


def gravar_json(relatorio: dict, destino: str) -> None:
    """Escreve num temporário do mesmo diretório e renomeia: falha não toca o destino."""
    caminho = Path(destino)
    fd, temporario = tempfile.mkstemp(prefix=".inventario-", suffix=".json", dir=caminho.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as arquivo:
            arquivo.write(para_json(relatorio))
        os.replace(temporario, caminho)
    except BaseException:
        Path(temporario).unlink(missing_ok=True)
        raise


# --- Markdown ----------------------------------------------------------------------------


def neutralizar(valor) -> str:
    """Texto seguro para uma linha de tabela no terminal (PRD P28)."""
    if valor is None:
        texto = "null"
    elif isinstance(valor, bool):
        texto = "true" if valor else "false"
    elif isinstance(valor, list):
        texto = ", ".join(str(v) for v in valor)
    else:
        texto = str(valor)
    partes = []
    for c in texto:
        if c in _ESCAPES_VISIVEIS:
            partes.append(_ESCAPES_VISIVEIS[c])
        elif _invisivel(c):
            partes.append(f"\\x{ord(c):02x}" if ord(c) < 0x100 else f"\\u{ord(c):04x}")
        elif c == "|":
            partes.append("\\|")
        else:
            partes.append(c)
    texto = "".join(partes)
    if len(texto) > TAMANHO_MAXIMO_CELULA:
        texto = texto[:TAMANHO_MAXIMO_CELULA] + "… (cortado)"
    return texto


def _encontrado(entrada: dict):
    texto = entrada.get("encontrado_texto")
    return texto if texto is not None else entrada["encontrado"]


def para_markdown(relatorio: dict, versao_baseline: int) -> str:
    host = relatorio["host"]
    conformidade = relatorio["conformidade"]
    instante = host["coletado_em"].replace("T", " ")[:16]
    linhas = [
        f"# Inventário — {neutralizar(host['hostname'])} ({neutralizar(host['endereco'])})",
        f"Coletado em {instante} UTC · baseline v{versao_baseline} · "
        f"chave de host {neutralizar(host['chave_de_host'])}",
        "",
        "## Desvios",
        "",
    ]
    desvios = [e for e in conformidade if e["veredito"] == DESVIO]
    # sorted é estável: dentro da mesma severidade, fica a ordem do baseline.
    desvios.sort(key=lambda e: ORDEM_SEVERIDADE[e["severidade"]])
    if desvios:
        linhas += ["| Severidade | Regra | Esperado | Encontrado |", "|---|---|---|---|"]
        linhas += [
            f"| {SEVERIDADE_COM_ACENTO[e['severidade']]} | {e['regra']} | "
            f"{neutralizar(e['esperado'])} | {neutralizar(_encontrado(e))} |"
            for e in desvios
        ]
    else:
        linhas.append("Nenhum.")

    linhas += ["", "## Não verificado", ""]
    nao_verificados = [e for e in conformidade if e["veredito"] == NAO_VERIFICADO]
    if nao_verificados:
        linhas += ["| Regra | Motivo |", "|---|---|"]
        linhas += [f"| {e['regra']} | {neutralizar(e['motivo'])} |" for e in nao_verificados]
    else:
        linhas.append("Nenhum.")

    linhas += ["", "## Conforme"]
    conformes = [e["regra"] for e in conformidade if e["veredito"] == CONFORME]
    linhas.append(" · ".join(conformes) if conformes else "Nenhum.")
    return "\n".join(linhas) + "\n"
