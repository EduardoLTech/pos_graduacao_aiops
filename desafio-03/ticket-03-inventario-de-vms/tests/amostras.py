"""Saídas brutas de um host Ubuntu 24.04, no formato dos comandos da coleta.

Escritas à mão a partir do formato documentado dos comandos; a tarefa 4.4 as substitui por
saídas gravadas no laboratório.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from inventario_vm.coleta import LEITURAS, PREFIXO
from inventario_vm.conexao import ResultadoComando


def chave_publica(comentario: str | None = None, opcoes: str | None = None) -> str:
    publica = ed25519.Ed25519PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
    ).decode()
    linha = publica if comentario is None else f"{publica} {comentario}"
    return f"{opcoes} {linha}" if opcoes else linha


def b64(texto: str) -> str:
    return base64.b64encode(texto.encode()).decode()


def linha_de_chaves(conta: str, status: str, conteudo: str = "", arquivo="authorized_keys") -> str:
    return f"{b64(conta)} {arquivo} {status} {b64(conteudo) if status == 'lida' else '-'}"


OS_RELEASE = """PRETTY_NAME="Ubuntu 24.04.1 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.1 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
"""

UNIDADES = """chrony.service         loaded active running chrony, an NTP client/server
containerd.service     loaded active running containerd container runtime
dbus.socket            loaded active running D-Bus System Message Bus Socket
node_exporter.service  loaded active running Node Exporter
ssh.service            loaded active running OpenBSD Secure Shell server
ssh.socket             loaded active listening OpenBSD Secure Shell server socket
"""

SEM_SWAP = "Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n"
COM_SWAP = SEM_SWAP + "/swapfile                               file\t\t4194300\t\t0\t\t-2\n"

# Formato de `ss -Hltnpe`: o uid só aparece quando não é 0; o cgroup traz a unidade.
PORTAS = """LISTEN 0      4096   127.0.0.53%lo:53        0.0.0.0:* uid:991 ino:4335 sk:3 cgroup:/system.slice/systemd-resolved.service <->
LISTEN 0      4096      10.128.0.5:9100      0.0.0.0:* uid:999 ino:54098 sk:1014 cgroup:/system.slice/node_exporter.service <->
LISTEN 0      4096         0.0.0.0:22        0.0.0.0:* ino:56423 sk:9 cgroup:/system.slice/ssh.socket <->
LISTEN 0      4096            [::]:22           [::]:* ino:55858 sk:a cgroup:/system.slice/ssh.socket v6only:1 <->
"""

CONTAS = """root:x:0:0:root:/root:/bin/bash
systemd-resolve:x:991:991:systemd Resolver:/:/usr/sbin/nologin
node_exporter:x:999:999::/home/node_exporter:/usr/sbin/nologin
coleta:x:1002:1003::/home/coleta:/bin/bash
"""


def chaves_conforme() -> str:
    return "\n".join([
        linha_de_chaves("root", "sem_permissao"),
        linha_de_chaves("root", "sem_permissao", arquivo="authorized_keys2"),
        linha_de_chaves("coleta", "lida", chave_publica("coleta@metacortex-platform") + "\n"),
        linha_de_chaves("coleta", "ausente", arquivo="authorized_keys2"),
        "fim",
    ]) + "\n"


def saidas_conforme() -> dict[str, str]:
    return {
        "hostname": "construct-node-14\n",
        "os_release": OS_RELEASE,
        "kernel": "6.8.0-1015-gcp\n",
        "unidades": UNIDADES,
        "swap": SEM_SWAP,
        "portas": PORTAS,
        "contas": CONTAS,
        "chaves": chaves_conforme(),
        "sshd": "uid=1001 rc=255\n",
        "ntp": "0 8193\n",  # adjtimex: TIME_OK; status STA_PLL | STA_NANO
    }


class SessaoFalsa:
    """Responde a cada leitura da tabela com a saída dada, ou com o ResultadoComando dado."""

    chave_de_host = "ssh-ed25519 SHA256:" + "A" * 43

    def __init__(self, saidas: dict[str, object]):
        self._por_comando = {PREFIXO + LEITURAS[n]: v for n, v in saidas.items()}
        self.comandos: list[str] = []
        self.fechada = False

    def executar(self, comando: str) -> ResultadoComando:
        self.comandos.append(comando)
        valor = self._por_comando[comando]
        if isinstance(valor, ResultadoComando):
            return valor
        return ResultadoComando(0, valor)

    def fechar(self):
        self.fechada = True
