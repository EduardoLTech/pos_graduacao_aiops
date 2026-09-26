"""Linha de comando: parâmetros, fluxo e códigos de saída (PRD P5–P7, P10; design D6).

Códigos: 0 conforme · 1 desvio · 2 erro de uso · 3 host inalcançável · 4 não verificado ·
5 erro interno (defeito da ferramenta; não é veredito sobre o host).
"""

import argparse
import logging
import sys
import threading
import warnings
from datetime import datetime, timezone
from pathlib import Path

from inventario_vm import baseline as mod_baseline
from inventario_vm import coleta, conexao, inventario, regras, relatorio
from inventario_vm.erros import ErroDeUso, HostInalcancavel

ERRO_INTERNO = 5


def _silenciar_bibliotecas() -> None:
    """Nenhum log, aviso ou traceback de terceiros chega ao stderr (PRD I2c)."""
    registro = logging.getLogger("paramiko")
    registro.addHandler(logging.NullHandler())
    registro.propagate = False
    registro.setLevel(logging.CRITICAL + 1)
    warnings.simplefilter("ignore")
    threading.excepthook = lambda _args: None


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # argparse cita o nome do parâmetro, não o valor
        raise ErroDeUso(message)


def _parser() -> argparse.ArgumentParser:
    p = _Parser(
        prog="inventario-vm",
        description="Inventário e drift de uma VM por SSH contra o baseline do parque.",
    )
    p.add_argument("--host", required=True, help="endereço da VM (IP ou nome)")
    p.add_argument("--usuario", required=True, help="usuário da conexão SSH")
    p.add_argument("--chave", required=True, help="caminho do arquivo da chave privada")
    p.add_argument("--porta", type=int, default=22, help="porta SSH (padrão 22)")
    p.add_argument("--fingerprint", help="fingerprint esperado da chave de host (SHA256:...)")
    p.add_argument("--json", dest="arquivo_json", help="arquivo onde gravar o relatório JSON")
    p.add_argument("--baseline", help="caminho do baseline.yaml (padrão: o que acompanha a ferramenta)")
    return p


def _validar_destino_json(arquivo: str | None) -> None:
    if arquivo is None:
        return
    pasta = Path(arquivo).resolve().parent
    if not pasta.is_dir():
        raise ErroDeUso("--json: o diretório do arquivo não existe")
    if Path(arquivo).is_dir():
        raise ErroDeUso("--json: o caminho é um diretório")


def executar(argv: list[str]) -> int:
    args = _parser().parse_args(argv)
    if not 1 <= args.porta <= 65535:
        raise ErroDeUso("--porta: fora do intervalo 1–65535")
    esperado = conexao.validar_fingerprint(args.fingerprint)
    base = mod_baseline.carregar(Path(args.baseline) if args.baseline else None)
    _validar_destino_json(args.arquivo_json)
    chave = conexao.carregar_chave(args.chave)

    sessao = conexao.conectar(args.host, args.porta, args.usuario, chave, esperado)
    try:
        coletado_em = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        leituras = coleta.coletar(sessao)
    finally:
        sessao.fechar()

    resultado = inventario.montar(leituras)
    conformidade = regras.avaliar(base, resultado)
    host = {
        "endereco": args.host,
        "hostname": resultado.hostname,
        "coletado_em": coletado_em,
        "chave_de_host": sessao.chave_de_host,
    }
    rel = relatorio.montar(host, resultado.inventario, conformidade, regras.resumir(conformidade))
    if args.arquivo_json:
        relatorio.gravar_json(rel, args.arquivo_json)
    sys.stdout.write(relatorio.para_markdown(rel, base.versao))
    sys.stdout.flush()
    return regras.codigo_de_saida(conformidade)


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    _silenciar_bibliotecas()
    try:
        return executar(sys.argv[1:] if argv is None else argv)
    except ErroDeUso as e:
        sys.stderr.write(f"erro de uso: {e}\n")
        return e.codigo
    except HostInalcancavel as e:
        sys.stderr.write(f"host inalcançável: {e}\n")
        return e.codigo
    except KeyboardInterrupt:
        sys.stderr.write("interrompido\n")
        return 130
    except Exception as e:
        # Só o tipo: o texto de uma exceção qualquer pode carregar caminho ou dado do host.
        sys.stderr.write(f"erro interno: {type(e).__name__}\n")
        return ERRO_INTERNO
