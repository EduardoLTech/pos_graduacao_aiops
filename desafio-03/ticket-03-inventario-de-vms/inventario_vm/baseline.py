"""Carga e validação do baseline.yaml (versão 1)."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from inventario_vm.erros import ErroDeUso

CAMINHO_PADRAO = Path(__file__).with_name("baseline.yaml")

# Regra -> tipo do valor esperado. A ordem do relatório vem do arquivo, não daqui.
REGRAS_CONHECIDAS = {
    "so.distribuicao": str,
    "so.versao_minima": str,
    "kernel.versao_minima": str,
    "servicos.ativos": list,
    "servicos.proibidos": list,
    "swap.habilitado": bool,
    "portas_em_escuta.publicas_permitidas": list,
    "portas_em_escuta.somente_rede_interna": list,
    "chaves_ssh.emitidas_por": str,
    "ssh.login_de_root": bool,
    "ntp.sincronizado": bool,
}
SEVERIDADES = ("critico", "alto", "medio")


@dataclass(frozen=True)
class Baseline:
    versao: int
    regras: tuple[str, ...]  # na ordem em que aparecem em `esperado`
    esperado: dict[str, object]
    severidade: dict[str, str]


def carregar(caminho: Path | None = None) -> Baseline:
    caminho = caminho or CAMINHO_PADRAO
    try:
        texto = Path(caminho).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise ErroDeUso("--baseline: arquivo inexistente ou ilegível") from None
    try:
        dado = yaml.safe_load(texto)
    except yaml.YAMLError:
        raise ErroDeUso("--baseline: YAML inválido") from None
    return validar(dado)


def validar(dado: object) -> Baseline:
    if not isinstance(dado, dict):
        raise ErroDeUso("--baseline: o documento não é um mapa")
    if dado.get("versao") != 1:
        raise ErroDeUso("--baseline: só a versao 1 é suportada")
    bloco = dado.get("esperado")
    if not isinstance(bloco, dict):
        raise ErroDeUso("--baseline: bloco 'esperado' ausente")

    esperado: dict[str, object] = {}
    for grupo, itens in bloco.items():
        if not isinstance(itens, dict):
            raise ErroDeUso(f"--baseline: grupo '{grupo}' não é um mapa")
        for chave, valor in itens.items():
            esperado[f"{grupo}.{chave}"] = valor

    desconhecidas = [r for r in esperado if r not in REGRAS_CONHECIDAS]
    if desconhecidas:
        raise ErroDeUso(f"--baseline: regra desconhecida: {', '.join(desconhecidas)}")
    ausentes = [r for r in REGRAS_CONHECIDAS if r not in esperado]
    if ausentes:
        raise ErroDeUso(f"--baseline: regra ausente: {', '.join(ausentes)}")
    for regra, tipo in REGRAS_CONHECIDAS.items():
        if not isinstance(esperado[regra], tipo):
            raise ErroDeUso(f"--baseline: valor de '{regra}' deveria ser {tipo.__name__}")

    bloco_sev = dado.get("severidade")
    if not isinstance(bloco_sev, dict):
        raise ErroDeUso("--baseline: bloco 'severidade' ausente")
    severidade: dict[str, str] = {}
    for nivel, regras in bloco_sev.items():
        if nivel not in SEVERIDADES:
            raise ErroDeUso(f"--baseline: severidade desconhecida: {nivel}")
        for regra in regras or []:
            if regra not in REGRAS_CONHECIDAS:
                raise ErroDeUso(f"--baseline: regra desconhecida em severidade: {regra}")
            if regra in severidade:
                raise ErroDeUso(f"--baseline: regra com duas severidades: {regra}")
            severidade[regra] = nivel
    sem_sev = [r for r in esperado if r not in severidade]
    if sem_sev:
        raise ErroDeUso(f"--baseline: regra sem severidade: {', '.join(sem_sev)}")

    return Baseline(versao=1, regras=tuple(esperado), esperado=esperado, severidade=severidade)
