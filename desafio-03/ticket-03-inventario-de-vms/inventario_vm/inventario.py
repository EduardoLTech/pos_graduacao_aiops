"""Interpretação pura das saídas brutas em inventário (PRD P14, P24).

Recebe as leituras da coleta e devolve o inventário na forma do relatório e a evidência de cada
leitura já refinada: uma saída que não se reconhece vira falha de coleta, e o `sshd -T` sem root
vira falta de privilégio.
"""

import base64
import binascii
import re
import struct
from dataclasses import dataclass, field

from inventario_vm.coleta import FALHA, LIDA, MOTIVO_SEM_PRIVILEGIO, SEM_PRIVILEGIO, Leitura

TIPOS_DE_CHAVE = {
    "ssh-ed25519",
    "ssh-rsa",
    "ssh-dss",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
    "sk-ssh-ed25519@openssh.com",
    "sk-ecdsa-sha2-nistp256@openssh.com",
}
TIPOS_DE_CHAVE |= {t.removesuffix("@openssh.com") + "-cert-v01@openssh.com" for t in TIPOS_DE_CHAVE}

MECANISMOS_NTP = {
    "chrony.service": "chrony",
    "chronyd.service": "chrony",
    "systemd-timesyncd.service": "systemd-timesyncd",
    "ntp.service": "ntp",
    "ntpsec.service": "ntpsec",
    "openntpd.service": "openntpd",
}

FONTE_CONFIG_SSHD = "configuração efetiva do servidor SSH"
ARQUIVOS_PADRAO_DE_CHAVE = {".ssh/authorized_keys", ".ssh/authorized_keys2"}


class SaidaNaoReconhecida(ValueError):
    pass


@dataclass
class Resultado:
    hostname: str | None
    inventario: dict
    evidencia: dict[str, Leitura] = field(default_factory=dict)


def montar(leituras: dict[str, Leitura]) -> Resultado:
    evidencia: dict[str, Leitura] = {}

    def interpretar(nome, funcao, vazio):
        leitura = leituras[nome]
        if leitura.status != LIDA:
            evidencia[nome] = leitura
            return vazio
        try:
            valor = funcao(leitura.saida)
        except SaidaNaoReconhecida as e:
            evidencia[nome] = Leitura(FALHA, motivo=f"falha de coleta: {e}")
            return vazio
        evidencia[nome] = leitura
        return valor

    hostname = interpretar("hostname", _hostname, None)
    so = interpretar("os_release", _os_release, {"distribuicao": None, "versao": None})
    kernel = interpretar("kernel", _kernel, None)
    servicos = interpretar("unidades", _unidades, None)
    swap = interpretar("swap", _swap, {"habilitado": None, "tamanho": None})
    contas = interpretar("contas", _contas, None)
    portas = interpretar("portas", lambda s: _portas(s, contas), None)
    ntp_sinc = interpretar("ntp", _ntp, None)

    sshd = _sshd(leituras["sshd"])
    evidencia["sshd"] = sshd.evidencia
    chaves, fontes = _chaves(leituras["chaves"], sshd)
    evidencia["chaves"] = (
        leituras["chaves"] if leituras["chaves"].status != LIDA or chaves is not None
        else Leitura(FALHA, motivo="falha de coleta: saída de chaves não reconhecida")
    )

    mecanismo = None
    if servicos is not None:
        ativos = [MECANISMOS_NTP[s["nome"]] for s in servicos if s["nome"] in MECANISMOS_NTP]
        mecanismo = ativos[0] if ativos else None

    inventario = {
        "so": so,
        "kernel": {"versao": kernel},
        "servicos": servicos,
        "swap": swap,
        "portas_em_escuta": portas,
        "chaves_ssh": chaves,
        "chaves_ssh_fontes_nao_lidas": fontes,
        "ssh": {"login_de_root": sshd.login_de_root},
        "ntp": {"sincronizado": ntp_sinc, "mecanismo": mecanismo},
    }
    return Resultado(hostname, inventario, evidencia)


def _hostname(saida: str) -> str:
    valor = saida.strip()
    if not valor:
        raise SaidaNaoReconhecida("hostname vazio")
    return valor


def _os_release(saida: str) -> dict:
    campos = {}
    for linha in saida.splitlines():
        if "=" not in linha or linha.lstrip().startswith("#"):
            continue
        chave, _, valor = linha.partition("=")
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        campos[chave.strip()] = valor
    distribuicao = campos.get("ID")
    versao_id = campos.get("VERSION_ID")
    if not distribuicao:
        raise SaidaNaoReconhecida("os-release sem ID")
    versao = versao_id
    # VERSION costuma trazer a revisão pontual ("24.04.1 LTS (Noble Numbat)").
    primeira = campos.get("VERSION", "").split(" ")[0]
    if versao_id and primeira.startswith(versao_id + "."):
        versao = primeira
    return {"distribuicao": distribuicao, "versao": versao}


def _kernel(saida: str) -> str:
    valor = saida.strip()
    if not valor:
        raise SaidaNaoReconhecida("versão do kernel vazia")
    return valor


def _unidades(saida: str) -> list[dict]:
    servicos = []
    for linha in saida.splitlines():
        partes = linha.split()
        if not partes:
            continue
        if len(partes) < 4:
            raise SaidaNaoReconhecida("linha de systemctl sem as colunas esperadas")
        nome, _carga, ativo = partes[0], partes[1], partes[2]
        tipo = nome.rpartition(".")[2]
        if tipo not in ("service", "socket"):
            continue
        servicos.append({"nome": nome, "tipo": tipo, "estado": ativo})
    return sorted(servicos, key=lambda s: s["nome"])


def _swap(saida: str) -> dict:
    linhas = saida.splitlines()
    if not linhas or not linhas[0].startswith("Filename"):
        raise SaidaNaoReconhecida("/proc/swaps em formato inesperado")
    total_kib = 0
    for linha in linhas[1:]:
        partes = linha.split()
        if not partes:
            continue
        try:
            total_kib += int(partes[2])
        except (IndexError, ValueError):
            raise SaidaNaoReconhecida("/proc/swaps com tamanho ilegível") from None
    if total_kib == 0:
        return {"habilitado": False, "tamanho": None}
    return {"habilitado": True, "tamanho": formatar_tamanho(total_kib * 1024)}


def formatar_tamanho(total_bytes: int) -> str:
    """Inteiro na maior unidade K/M/G/T cujo valor arredondado dê ao menos 1 (PRD P14).

    Arredonda antes de comparar: o /proc/swaps desconta a página de cabeçalho, e 1 GiB de swap
    aparece como 0,99999 GiB — comparando antes, sairia "1024M".
    """
    for sufixo, expoente in (("T", 4), ("G", 3), ("M", 2), ("K", 1)):
        valor = round(total_bytes / 1024**expoente)
        if valor >= 1:
            return f"{valor}{sufixo}"
    return f"{total_bytes}B"


_PROCESSO = re.compile(r'users:\(\("((?:[^"\\]|\\.)*)"')
_UID = re.compile(r"(?:^|\s)uid:(\d+)(?:\s|$)")
_CGROUP = re.compile(r"(?:^|\s)cgroup:(\S+)")


def _contas(saida: str) -> dict[int, str]:
    """uid -> nome, de `getent passwd`."""
    contas = {}
    for linha in saida.splitlines():
        campos = linha.split(":")
        if len(campos) >= 3 and campos[2].isdigit():
            contas.setdefault(int(campos[2]), campos[0])
    if not contas:
        raise SaidaNaoReconhecida("getent passwd sem contas")
    return contas


def _portas(saida: str, contas: dict[int, str] | None) -> list[dict]:
    """Portas TCP em escuta (PRD P14, P24).

    `processo` só é legível para processos do próprio usuário; `conta` (dono do socket; o `ss`
    omite o uid quando é 0) e `unidade` (unidade systemd do cgroup) são legíveis sempre.
    """
    portas = {}
    for linha in saida.splitlines():
        partes = linha.split()
        if not partes:
            continue
        if len(partes) < 5 or partes[0] != "LISTEN":
            raise SaidaNaoReconhecida("linha de ss sem as colunas esperadas")
        local = partes[3]
        endereco, sep, porta = local.rpartition(":")
        if not sep or not porta.isdigit():
            raise SaidaNaoReconhecida("endereço local ilegível na saída de ss")
        endereco = endereco.strip("[]").split("%")[0]
        achado = _PROCESSO.search(linha)
        uid = _UID.search(linha)
        uid = int(uid.group(1)) if uid else 0
        cgroup = _CGROUP.search(linha)
        unidade = None
        if cgroup:  # /system.slice/node_exporter.service -> node_exporter.service
            unidade = cgroup.group(1).rstrip("/").rpartition("/")[2] or None
        entrada = {
            "porta": int(porta),
            "bind": endereco,
            "processo": achado.group(1) if achado else None,
            "conta": contas.get(uid) if contas is not None else None,
            "unidade": unidade,
        }
        chave = (entrada["porta"], endereco)
        if chave not in portas or portas[chave]["processo"] is None:
            portas[chave] = entrada
    return [portas[c] for c in sorted(portas)]


TIME_ERROR = 5
STA_UNSYNC = 0x0040


def _ntp(saida: str) -> bool:
    """Mesmo critério do systemd-timedated: sincronizado salvo TIME_ERROR ou STA_UNSYNC."""
    partes = saida.split()
    if len(partes) != 2 or not all(p.lstrip("-").isdigit() for p in partes):
        raise SaidaNaoReconhecida("adjtimex não devolveu retorno e status")
    retorno, status = int(partes[0]), int(partes[1])
    if retorno < 0:
        raise SaidaNaoReconhecida("adjtimex falhou")
    return retorno != TIME_ERROR and not status & STA_UNSYNC


@dataclass
class _Sshd:
    evidencia: Leitura
    login_de_root: str | None = None
    config: dict[str, str] | None = None


def _sshd(leitura: Leitura) -> _Sshd:
    if leitura.status != LIDA:
        return _Sshd(leitura)
    linhas = leitura.saida.splitlines()
    cabecalho = re.fullmatch(r"uid=(\d+) rc=(\d+)", linhas[0].strip()) if linhas else None
    if not cabecalho:
        return _Sshd(Leitura(FALHA, motivo="falha de coleta: saída de sshd -T não reconhecida"))
    uid, rc = int(cabecalho.group(1)), int(cabecalho.group(2))
    if rc == 127:
        return _Sshd(Leitura(FALHA, motivo="falha de coleta: sshd não encontrado"))
    if rc != 0:
        if uid != 0:
            return _Sshd(Leitura(SEM_PRIVILEGIO, motivo=MOTIVO_SEM_PRIVILEGIO))
        return _Sshd(Leitura(FALHA, motivo=f"falha de coleta: sshd -T terminou com código {rc}"))
    config: dict[str, str] = {}
    for linha in linhas[1:]:
        chave, _, valor = linha.strip().partition(" ")
        if chave:
            config.setdefault(chave.lower(), valor.strip())
    valor = config.get("permitrootlogin")
    if valor is None:
        return _Sshd(Leitura(FALHA, motivo="falha de coleta: sshd -T sem permitrootlogin"))
    return _Sshd(leitura, valor, config)


def _chaves(leitura: Leitura, sshd: _Sshd) -> tuple[list[dict] | None, list[str]]:
    """Chaves lidas e fontes não lidas (PRD P14, P25; design D4)."""
    fontes: list[str] = []
    if sshd.config is None:
        fontes.append(FONTE_CONFIG_SSHD)
    else:
        comando = sshd.config.get("authorizedkeyscommand", "none")
        if comando.lower() != "none":
            fontes.append("AuthorizedKeysCommand")
        arquivos = set(sshd.config.get("authorizedkeysfile", "").split())
        if not arquivos <= ARQUIVOS_PADRAO_DE_CHAVE:
            fontes.append("AuthorizedKeysFile fora do padrão")

    if leitura.status != LIDA:
        return None, sorted(set(fontes + ["contas do host"]))

    linhas = leitura.saida.splitlines()
    if not linhas or linhas[-1].strip() != "fim":
        return None, sorted(set(fontes + ["contas do host"]))

    chaves = []
    for linha in linhas[:-1]:
        partes = linha.split(" ")
        if len(partes) != 4:
            return None, sorted(set(fontes + ["contas do host"]))
        conta_b64, _arquivo, status, conteudo_b64 = partes
        try:
            conta = base64.b64decode(conta_b64, validate=True).decode("utf-8", "replace")
            conteudo = (
                base64.b64decode(conteudo_b64, validate=True).decode("utf-8", "replace")
                if status == "lida" else ""
            )
        except binascii.Error:
            return None, sorted(set(fontes + ["contas do host"]))
        if status == "sem_permissao":
            fontes.append(conta)
        elif status == "lida":
            for identificacao in identificacoes(conteudo):
                chaves.append({"identificacao": identificacao, "conta": conta})
        elif status != "ausente":
            return None, sorted(set(fontes + ["contas do host"]))

    chaves.sort(key=lambda c: (c["conta"], c["identificacao"] is None, c["identificacao"] or ""))
    return chaves, sorted(set(fontes))


def identificacoes(conteudo: str) -> list[str | None]:
    """Comentário de cada chave válida de um authorized_keys, como o sshd o leria."""
    resultado = []
    for linha in conteudo.splitlines():
        chave = interpretar_linha_de_chave(linha)
        if chave is not None:
            resultado.append(chave)
    return [c if c else None for c in resultado]


def interpretar_linha_de_chave(linha: str) -> str | None:
    """Devolve o comentário ('' se não houver) ou None se a linha não for chave."""
    texto = linha.lstrip(" \t").rstrip("\r\n")
    if not texto or texto.startswith("#"):
        return None
    campos = _separar(texto)
    if campos is None:
        return None
    primeiro, resto = campos
    if primeiro not in TIPOS_DE_CHAVE:
        # Havia opções antes do tipo (from=, command=, cert-authority).
        campos = _separar(resto)
        if campos is None or campos[0] not in TIPOS_DE_CHAVE:
            return None
        primeiro, resto = campos
    tipo = primeiro
    campos = _separar(resto)
    if campos is None:
        return None
    blob, comentario = campos
    if not _blob_valido(tipo, blob):
        return None
    return comentario.strip()


def _separar(texto: str) -> tuple[str, str] | None:
    """Primeiro campo (respeitando aspas, como nas opções) e o resto sem o espaço separador."""
    texto = texto.lstrip(" \t")
    if not texto:
        return None
    i, aspas = 0, False
    while i < len(texto):
        c = texto[i]
        if c == "\\" and aspas and i + 1 < len(texto):
            i += 2
            continue
        if c == '"':
            aspas = not aspas
        elif c in " \t" and not aspas:
            break
        i += 1
    if aspas:
        return None
    return texto[:i], texto[i:].lstrip(" \t")


def _blob_valido(tipo: str, blob: str) -> bool:
    try:
        dado = base64.b64decode(blob, validate=True)
        (tamanho,) = struct.unpack(">I", dado[:4])
        return dado[4 : 4 + tamanho].decode("ascii") == tipo
    except (binascii.Error, struct.error, UnicodeDecodeError):
        return False
