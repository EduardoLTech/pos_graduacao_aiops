"""Leituras no host: comandos constantes, só leitura, sem privilégio (ADR 003, design D2–D4).

Nenhum comando daqui é montado com texto vindo do host (PRD I7). Cada leitura devolve um
desfecho — lida, sem privilégio ou falha — e a avaliação não sabe como ela foi feita.
"""

from dataclasses import dataclass
from typing import Protocol

from inventario_vm.conexao import ResultadoComando

LIDA = "lida"
SEM_PRIVILEGIO = "sem_privilegio"
FALHA = "falha"

MOTIVO_SEM_PRIVILEGIO = "exige privilégio que o usuário da coleta não tem"

# Idioma fixo na própria linha de comando: o servidor SSH não é obrigado a aceitar variável de
# ambiente enviada pelo cliente.
PREFIXO = "export LC_ALL=C LANG=C; "

# sshd -T só roda como root (lê as chaves de host). A falta de privilégio é reconhecida pelo
# uid da sessão, não pelo texto do erro (design D3).
SCRIPT_SSHD = (
    'u=$(id -u); if [ ! -x /usr/sbin/sshd ]; then echo "uid=$u rc=127"; exit 0; fi; '
    'out=$(/usr/sbin/sshd -T 2>/dev/null); rc=$?; echo "uid=$u rc=$rc"; '
    '[ "$rc" -eq 0 ] && printf "%s\\n" "$out"; exit 0'
)

# Percorre as contas no próprio host; conta e conteúdo saem em base64, então nome ou comentário
# hostil não quebra o formato nem entra em comando (design D4). Todas as contas entram: com
# shell nologin/false a chave ainda autentica (e abre túnel), e shell vazio é /bin/sh.
SCRIPT_CHAVES = r"""
getent passwd | while IFS=: read -r conta _ _ _ _ dir _; do
  c=$(printf %s "$conta" | base64 -w0)
  for nome in authorized_keys authorized_keys2; do
    f="$dir/.ssh/$nome"
    if [ -r "$f" ] && [ -f "$f" ]; then
      printf '%s %s lida %s\n' "$c" "$nome" "$(base64 -w0 < "$f")"
    elif [ -e "$f" ]; then
      printf '%s %s sem_permissao -\n' "$c" "$nome"
    elif [ -n "$dir" ] && [ ! -e "$dir" ] && [ -x "$(dirname "$dir")" ]; then
      printf '%s %s ausente -\n' "$c" "$nome"
    elif [ -x "$dir/.ssh" ] || { [ -x "$dir" ] && [ ! -e "$dir/.ssh" ]; }; then
      printf '%s %s ausente -\n' "$c" "$nome"
    else
      printf '%s %s sem_permissao -\n' "$c" "$nome"
    fi
  done
done
echo fim
"""

# Sincronização lida do kernel por adjtimex com struct zerada (modes=0: só leitura). O
# `timedatectl` daria o mesmo dado, mas ativa o systemd-timedated pelo D-Bus — sobe um serviço
# no host, contra o "só lê" (PRD I1). Imprime o retorno e o campo `status`, que em Linux de 64
# bits fica no deslocamento 40 da struct timex.
SCRIPT_NTP = (
    "python3 -c 'import ctypes,sys;"
    "b=ctypes.create_string_buffer(512);"
    "r=ctypes.CDLL(None).adjtimex(b);"
    "print(r,int.from_bytes(b.raw[40:44],sys.byteorder))'"
)

LEITURAS = {
    "hostname": "cat /proc/sys/kernel/hostname",
    "os_release": "cat /etc/os-release",
    "kernel": "uname -r",
    "unidades": (
        "systemctl list-units --type=service,socket --state=active "
        "--no-legend --plain --no-pager"
    ),
    "swap": "cat /proc/swaps",
    # -e traz uid do dono e cgroup (unidade systemd), legíveis por usuário comum mesmo quando
    # o processo (-p) não é.
    "portas": "ss -Hltnpe",
    "contas": "getent passwd",
    "chaves": SCRIPT_CHAVES,
    "sshd": SCRIPT_SSHD,
    "ntp": SCRIPT_NTP,
}


@dataclass(frozen=True)
class Leitura:
    status: str
    saida: str = ""
    motivo: str | None = None


class Executor(Protocol):
    def executar(self, comando: str) -> ResultadoComando: ...


def coletar(sessao: Executor) -> dict[str, Leitura]:
    return {nome: _ler(sessao, comando) for nome, comando in LEITURAS.items()}


def _ler(sessao: Executor, comando: str) -> Leitura:
    resultado = sessao.executar(PREFIXO + comando)
    if resultado.limite_excedido:
        return Leitura(FALHA, motivo=f"falha de coleta: limite excedido ({resultado.limite_excedido})")
    if resultado.codigo != 0:
        return Leitura(FALHA, motivo=f"falha de coleta: comando terminou com código {resultado.codigo}")
    return Leitura(LIDA, resultado.saida)
