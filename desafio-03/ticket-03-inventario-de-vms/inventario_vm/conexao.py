"""Conexão SSH por paramiko (ADR 002) e política de chave de host (ADR 004).

Toda falha é classificada pelo tipo da exceção, nunca pelo texto (design D5). Nenhuma mensagem
daqui repete texto de exceção de terceiros nem o caminho da chave (PRD I2).
"""

import base64
import hashlib
import re
import socket
import time
from dataclasses import dataclass

import paramiko
from paramiko.ssh_exception import NoValidConnectionsError

from inventario_vm.erros import ErroDeUso, HostInalcancavel

TEMPO_TCP = 6
TEMPO_BANNER = 4
TEMPO_AUTENTICACAO = 4  # soma 14 s: dentro dos 15 s do PRD P7
LIMITE_TEMPO_LEITURA = 20.0
LIMITE_BYTES_LEITURA = 1024 * 1024
FORMATO_FINGERPRINT = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")


CLASSES_DE_CHAVE = (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey)


def carregar_chave(caminho: str) -> paramiko.PKey:
    """Carrega pela classe de cada tipo de chave.

    `PKey.from_path` não serve: com chave protegida ele levanta um TypeError genérico da
    biblioteca de criptografia, e só o carregador por classe distingue passphrase por tipo
    (PasswordRequiredException).
    """
    for classe in CLASSES_DE_CHAVE:
        try:
            return classe.from_private_key_file(caminho)
        except paramiko.PasswordRequiredException:
            raise ErroDeUso(
                "--chave: chave protegida por passphrase, o que não é suportado"
            ) from None
        except FileNotFoundError:
            raise ErroDeUso("--chave: arquivo não encontrado") from None
        except OSError:
            raise ErroDeUso("--chave: arquivo ilegível") from None
        except Exception:
            continue  # não é deste tipo; tenta o próximo
    raise ErroDeUso("--chave: formato de chave privada não reconhecido")


def validar_fingerprint(valor: str | None) -> str | None:
    if valor is None:
        return None
    if not FORMATO_FINGERPRINT.match(valor):
        raise ErroDeUso("--fingerprint: formato esperado é SHA256:<43 caracteres base64>")
    return valor


def fingerprint(chave: paramiko.PKey) -> str:
    digest = hashlib.sha256(chave.asbytes()).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


class ChaveDeHostDivergente(Exception):
    def __init__(self, esperado: str, apresentado: str):
        super().__init__()
        self.esperado = esperado
        self.apresentado = apresentado


class _PoliticaDeChaveDeHost(paramiko.MissingHostKeyPolicy):
    """Aceita e registra; com fingerprint esperado, recusa o que não bate (ADR 004).

    Nenhum known_hosts é carregado, então o paramiko consulta esta política em toda conexão,
    antes da autenticação.
    """

    def __init__(self, esperado: str | None):
        self.esperado = esperado
        self.algoritmo: str | None = None
        self.fingerprint: str | None = None

    def missing_host_key(self, client, hostname, key):
        self.algoritmo = key.get_name()
        self.fingerprint = fingerprint(key)
        if self.esperado is not None and self.fingerprint != self.esperado:
            raise ChaveDeHostDivergente(self.esperado, self.fingerprint)


@dataclass(frozen=True)
class ResultadoComando:
    codigo: int | None  # None quando a leitura foi interrompida por limite
    saida: str
    limite_excedido: str | None = None  # "tempo" ou "tamanho"


class Sessao:
    def __init__(self, cliente: paramiko.SSHClient, algoritmo: str, fp: str):
        self._cliente = cliente
        self.chave_de_host = f"{algoritmo} {fp}"

    def _transporte_ativo(self) -> bool:
        transporte = self._cliente.get_transport()
        return transporte is not None and transporte.is_active()

    def executar(self, comando: str) -> ResultadoComando:
        """Executa um comando fixo com limite de tempo e tamanho (PRD P9).

        Conexão que cai no meio vira HostInalcancavel (PRD P8), não falha de leitura.
        """
        try:
            canal = self._cliente.get_transport().open_session(timeout=10)
            canal.settimeout(0.2)
            canal.exec_command(comando)
        except Exception:
            raise HostInalcancavel("a conexão caiu durante a coleta") from None

        prazo = time.monotonic() + LIMITE_TEMPO_LEITURA
        saida = bytearray()
        try:
            while True:
                if time.monotonic() > prazo:
                    canal.close()
                    return ResultadoComando(None, "", "tempo")
                while canal.recv_stderr_ready():
                    canal.recv_stderr(65536)  # descartado; só drena a janela
                try:
                    dado = canal.recv(65536)
                except socket.timeout:
                    if not self._transporte_ativo():
                        raise HostInalcancavel("a conexão caiu durante a coleta") from None
                    continue
                if not dado:
                    break
                saida += dado
                if len(saida) > LIMITE_BYTES_LEITURA:
                    canal.close()
                    return ResultadoComando(None, "", "tamanho")
            while not canal.exit_status_ready():
                if time.monotonic() > prazo:
                    canal.close()
                    return ResultadoComando(None, "", "tempo")
                if not self._transporte_ativo():
                    raise HostInalcancavel("a conexão caiu durante a coleta")
                time.sleep(0.05)
            codigo = canal.recv_exit_status()
        except HostInalcancavel:
            raise
        except Exception:
            raise HostInalcancavel("a conexão caiu durante a coleta") from None
        finally:
            canal.close()

        if codigo == -1 and not self._transporte_ativo():
            raise HostInalcancavel("a conexão caiu durante a coleta")
        return ResultadoComando(codigo, saida.decode("utf-8", errors="replace"))

    def fechar(self) -> None:
        self._cliente.close()


def conectar(
    endereco: str, porta: int, usuario: str, chave: paramiko.PKey, esperado: str | None
) -> Sessao:
    cliente = paramiko.SSHClient()
    politica = _PoliticaDeChaveDeHost(esperado)
    cliente.set_missing_host_key_policy(politica)
    try:
        cliente.connect(
            endereco,
            port=porta,
            username=usuario,
            pkey=chave,
            allow_agent=False,
            look_for_keys=False,
            timeout=TEMPO_TCP,
            banner_timeout=TEMPO_BANNER,
            auth_timeout=TEMPO_AUTENTICACAO,
        )
    except ChaveDeHostDivergente as e:
        cliente.close()
        raise HostInalcancavel(
            f"a chave de host não confere: esperado {e.esperado}, apresentado {e.apresentado}"
        ) from None
    except Exception as e:
        cliente.close()
        raise HostInalcancavel(_causa(e, porta)) from None
    return Sessao(cliente, politica.algoritmo, politica.fingerprint)


def _causa(erro: Exception, porta: int) -> str:
    """Traduz o tipo da exceção em causa legível. A ordem importa: subclasses primeiro."""
    if isinstance(erro, socket.gaierror):
        return "o nome do host não resolve"
    if isinstance(erro, paramiko.AuthenticationException):
        return "autenticação recusada: o host não aceitou a chave para este usuário"
    if isinstance(erro, NoValidConnectionsError):
        motivos = list(erro.errors.values())
        if motivos and all(isinstance(m, ConnectionRefusedError) for m in motivos):
            return f"conexão recusada na porta {porta}: nada escuta ali (SSH fora do ar?)"
        if motivos and all(isinstance(m, (TimeoutError, socket.timeout)) for m in motivos):
            return f"o host não respondeu em {TEMPO_TCP} s"
        return "não foi possível abrir conexão com o host"
    if isinstance(erro, ConnectionRefusedError):
        return f"conexão recusada na porta {porta}: nada escuta ali (SSH fora do ar?)"
    if isinstance(erro, (TimeoutError, socket.timeout)):
        return f"o host não respondeu em {TEMPO_TCP} s"
    if isinstance(erro, (paramiko.SSHException, EOFError)):
        return f"o serviço na porta {porta} não respondeu como servidor SSH"
    if isinstance(erro, OSError):
        return "falha de rede ao conectar (host ou rede inalcançável)"
    return "falha ao conectar"
