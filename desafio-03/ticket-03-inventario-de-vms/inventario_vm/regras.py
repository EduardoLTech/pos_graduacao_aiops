"""Avaliação pura das regras do baseline (PRD P2–P4, P16–P27, I3, I4)."""

import ipaddress
import re

from inventario_vm.baseline import SEVERIDADES, Baseline
from inventario_vm.coleta import LIDA, Leitura
from inventario_vm.inventario import Resultado

CONFORME = "conforme"
DESVIO = "desvio"
NAO_VERIFICADO = "nao_verificado"

_REDES_INTERNAS = [
    ipaddress.ip_network(r)
    for r in (
        "127.0.0.0/8", "::1/128",
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
        "fc00::/7",
        "169.254.0.0/16", "fe80::/10",
    )
]


class _NaoVerificado(Exception):
    def __init__(self, motivo: str, encontrado=None, texto: str | None = None):
        super().__init__(motivo)
        self.motivo = motivo
        self.encontrado = encontrado
        self.texto = texto


def avaliar(baseline: Baseline, resultado: Resultado) -> list[dict]:
    """Uma entrada por regra, na ordem do baseline.

    `encontrado` vai com tipo para o JSON (booleano, lista, texto do host); `encontrado_texto`
    é a frase para o Markdown e não sai no JSON (relatorio.para_json).
    """
    entradas = []
    for regra in baseline.regras:
        esperado = baseline.esperado[regra]
        try:
            conforme, encontrado, texto = _AVALIADORES[regra](esperado, resultado, baseline)
        except _NaoVerificado as e:
            entradas.append({
                "regra": regra, "esperado": esperado, "encontrado": e.encontrado,
                "veredito": NAO_VERIFICADO, "motivo": e.motivo, "encontrado_texto": e.texto,
            })
            continue
        entrada = {"regra": regra, "esperado": esperado, "encontrado": encontrado}
        if conforme:
            entrada["veredito"] = CONFORME
        else:
            entrada["veredito"] = DESVIO
            entrada["severidade"] = baseline.severidade[regra]
        entrada["encontrado_texto"] = texto
        entradas.append(entrada)
    return entradas


def resumir(conformidade: list[dict]) -> dict:
    resumo = {CONFORME: 0, DESVIO: 0, NAO_VERIFICADO: 0}
    por_severidade = dict.fromkeys(SEVERIDADES, 0)
    for entrada in conformidade:
        resumo[entrada["veredito"]] += 1
        if entrada["veredito"] == DESVIO:
            por_severidade[entrada["severidade"]] += 1
    return {**resumo, "por_severidade": por_severidade}


def codigo_de_saida(conformidade: list[dict]) -> int:
    vereditos = {e["veredito"] for e in conformidade}
    if DESVIO in vereditos:
        return 1
    if NAO_VERIFICADO in vereditos:
        return 4
    return 0


# --- apoio -------------------------------------------------------------------------------


def _exigir(resultado: Resultado, leitura: str, encontrado=None) -> None:
    evidencia: Leitura = resultado.evidencia[leitura]
    if evidencia.status != LIDA:
        raise _NaoVerificado(evidencia.motivo, encontrado)


def versao_numerica(texto: str) -> tuple[int, ...]:
    achado = re.match(r"\d+(?:\.\d+)*", texto or "")
    if not achado:
        raise _NaoVerificado("falha de coleta: versão não reconhecida", texto)
    return tuple(int(p) for p in achado.group(0).split("."))


def versao_maior_ou_igual(encontrada: str, minima: str) -> bool:
    a, b = versao_numerica(encontrada), versao_numerica(minima)
    tamanho = max(len(a), len(b))
    return a + (0,) * (tamanho - len(a)) >= b + (0,) * (tamanho - len(b))


def bind_interno(bind: str) -> bool:
    if bind in ("*", ""):
        return False
    try:
        endereco = ipaddress.ip_address(bind)
    except ValueError:
        return False
    if isinstance(endereco, ipaddress.IPv6Address) and endereco.ipv4_mapped:
        endereco = endereco.ipv4_mapped
    return any(endereco in rede for rede in _REDES_INTERNAS)


def _ativos(resultado: Resultado) -> list[dict]:
    return [s for s in resultado.inventario["servicos"] if s["estado"] == "active"]


def _publicas(r: Resultado) -> list[dict]:
    return [p for p in r.inventario["portas_em_escuta"] if not bind_interno(p["bind"])]


def _binds(portas: list[dict]) -> list[dict]:
    return [{"porta": p["porta"], "bind": p["bind"]} for p in portas]


def _texto_binds(portas: list[dict]) -> str:
    return ", ".join(f"{p['porta']} em {p['bind']}" for p in portas)


# --- regras ------------------------------------------------------------------------------
# Cada regra devolve (conforme, encontrado com tipo, frase para o Markdown ou None).


def _so_distribuicao(esperado, r, baseline):
    _exigir(r, "os_release")
    distribuicao = r.inventario["so"]["distribuicao"]
    return distribuicao == esperado, distribuicao, None


def _so_versao_minima(esperado, r, baseline):
    _exigir(r, "os_release")
    so = r.inventario["so"]
    # Versão só se compara dentro da distribuição esperada (PRD P17).
    if so["distribuicao"] != baseline.esperado["so.distribuicao"]:
        raise _NaoVerificado("distribuição diferente da esperada", so["versao"])
    if so["versao"] is None:
        raise _NaoVerificado("falha de coleta: os-release sem VERSION_ID")
    return versao_maior_ou_igual(so["versao"], esperado), so["versao"], None


def _kernel_versao_minima(esperado, r, baseline):
    _exigir(r, "kernel")
    versao = r.inventario["kernel"]["versao"]
    return versao_maior_ou_igual(versao, esperado), versao, None


def _servicos_ativos(esperado, r, baseline):
    """encontrado: os nomes do baseline satisfeitos; os ausentes são a diferença."""
    _exigir(r, "unidades")
    ativos = {s["nome"] for s in _ativos(r)}
    satisfeitos = [
        nome for nome in esperado
        if f"{nome}.service" in ativos or f"{nome}.socket" in ativos
    ]
    ausentes = [n for n in esperado if n not in satisfeitos]
    if ausentes:
        return False, satisfeitos, "ausente: " + ", ".join(ausentes)
    return True, satisfeitos, None


def _servicos_proibidos(esperado, r, baseline):
    """encontrado: as unidades proibidas que estão ativas."""
    _exigir(r, "unidades")
    ativos = {s["nome"] for s in _ativos(r)}
    encontrados = [u for u in esperado if u in ativos]
    if encontrados:
        return False, encontrados, "ativo: " + ", ".join(encontrados)
    return True, encontrados, "nenhum ativo"


def _swap_habilitado(esperado, r, baseline):
    _exigir(r, "swap")
    swap = r.inventario["swap"]
    texto = f"true ({swap['tamanho']})" if swap["habilitado"] else None
    return swap["habilitado"] == esperado, swap["habilitado"], texto


def _portas_publicas_permitidas(esperado, r, baseline):
    """encontrado: as portas em bind público julgadas por esta regra, com o bind."""
    _exigir(r, "portas")
    # Porta listada em somente_rede_interna é julgada só por aquela regra: o mesmo bind não
    # vira dois desvios (PRD P22, como no exemplo do enunciado).
    internas = baseline.esperado["portas_em_escuta.somente_rede_interna"]
    publicas = [p for p in _publicas(r) if p["porta"] not in internas]
    fora = [p for p in publicas if p["porta"] not in esperado]
    if fora:
        return False, _binds(publicas), _texto_binds(fora)
    return True, _binds(publicas), _texto_binds(publicas) or "nenhuma porta em bind público"


def _portas_somente_rede_interna(esperado, r, baseline):
    """encontrado: os binds das portas listadas."""
    _exigir(r, "portas")
    listadas = [p for p in r.inventario["portas_em_escuta"] if p["porta"] in esperado]
    publicas = [p for p in listadas if not bind_interno(p["bind"])]
    if publicas:
        return False, _binds(listadas), _texto_binds(publicas)
    return True, _binds(listadas), _texto_binds(listadas) or "sem escuta"


def _chaves_emitidas_por(esperado, r, baseline):
    """encontrado: as identificações lidas (null para chave sem comentário)."""
    _exigir(r, "chaves")
    chaves = r.inventario["chaves_ssh"]
    fontes = r.inventario["chaves_ssh_fontes_nao_lidas"]
    identificacoes = [c["identificacao"] for c in chaves]
    sufixo = "@" + esperado
    fora = [i for i in identificacoes if not (i or "").endswith(sufixo)]
    if fora:
        return False, identificacoes, ", ".join(i or "(sem comentário)" for i in fora)
    lidas = f"{len(chaves)} chave(s) lida(s), todas da plataforma"
    if fontes:
        motivo = "fontes de chave não lidas: " + ", ".join(fontes)
        raise _NaoVerificado(motivo, identificacoes, lidas)
    return True, identificacoes, lidas


def _ssh_login_de_root(esperado, r, baseline):
    _exigir(r, "sshd")
    valor = r.inventario["ssh"]["login_de_root"]
    desligado = valor == "no"
    return desligado == (not esperado), valor, None


def _ntp_sincronizado(esperado, r, baseline):
    _exigir(r, "ntp")
    ntp = r.inventario["ntp"]
    texto = None
    if ntp["mecanismo"]:
        texto = f"{'true' if ntp['sincronizado'] else 'false'} ({ntp['mecanismo']})"
    return ntp["sincronizado"] == esperado, ntp["sincronizado"], texto


_AVALIADORES = {
    "so.distribuicao": _so_distribuicao,
    "so.versao_minima": _so_versao_minima,
    "kernel.versao_minima": _kernel_versao_minima,
    "servicos.ativos": _servicos_ativos,
    "servicos.proibidos": _servicos_proibidos,
    "swap.habilitado": _swap_habilitado,
    "portas_em_escuta.publicas_permitidas": _portas_publicas_permitidas,
    "portas_em_escuta.somente_rede_interna": _portas_somente_rede_interna,
    "chaves_ssh.emitidas_por": _chaves_emitidas_por,
    "ssh.login_de_root": _ssh_login_de_root,
    "ntp.sincronizado": _ntp_sincronizado,
}
