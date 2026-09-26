#!/usr/bin/env bash
# Roda a sequência de evidência contra o laboratório já criado e grava tudo em
# laboratorio/.estado/evidencia/ (fora do git: tem IP e fingerprint reais).
#   1. host conforme: execução + repetição, com prova de que nada mudou no host (PRD I1)
#   2. host com desvios
#   3. host inalcançável: nome, sem resposta, chave recusada, fingerprint divergente, SSH parado
# O acesso administrativo só acontece entre as fases, nunca entre as duas execuções da fase 1.
# Uso, a partir da pasta do ticket: bash laboratorio/coletar-evidencia.sh
set -uo pipefail
source "$(dirname "$0")/lab.env"
cd "$LAB_DIR/.."

SAIDA="$ESTADO/evidencia"
rm -rf "$SAIDA"; mkdir -p "$SAIDA"
IP="$(cat "$ESTADO/ip")"
FP="$(cat "$ESTADO/fingerprint")"
FERRAMENTA=".venv/Scripts/inventario-vm"
[[ -x "$FERRAMENTA" ]] || FERRAMENTA=".venv/bin/inventario-vm"
[[ -f "$CHAVES/estranha" ]] || ssh-keygen -q -t ed25519 -N "" -C x -f "$CHAVES/estranha"

adm() {
  ssh -i "$CHAVES/admin" -o UserKnownHostsFile="$ESTADO/known_hosts" -o StrictHostKeyChecking=yes \
    -o IdentitiesOnly=yes -o BatchMode=yes "$USUARIO_ADMIN@$IP" "$@"
}

# executa <nome> <args da ferramenta...>: grava .md, .err, .json e .rc (código e tempo)
executa() {
  local nome="$1"; shift
  echo "anterior" > "$SAIDA/$nome.json"
  local inicio; inicio=$(date +%s%N)
  "$FERRAMENTA" "$@" --json "$SAIDA/$nome.json" > "$SAIDA/$nome.md" 2> "$SAIDA/$nome.err"
  local codigo=$?
  local ms=$(( ($(date +%s%N) - inicio) / 1000000 ))
  echo "codigo=$codigo tempo_ms=$ms" > "$SAIDA/$nome.rc"
  printf '%-28s código %s  %6s ms  %s\n' "$nome" "$codigo" "$ms" "$(head -c 110 "$SAIDA/$nome.err")"
}

COLETA=(--host "$IP" --usuario "$USUARIO_COLETA" --chave "$CHAVES/coleta" --fingerprint "$FP")
ACHAR='sudo find / -xdev \( -path /proc -o -path /sys -o -path /run -o -path /dev \) -prune -o -newer /run/marca-evidencia \( -type f -o -type d \) -print 2>/dev/null | sort'

echo "== fase 1: host conforme"
bash "$LAB_DIR/preparar-conforme.sh" > "$SAIDA/00-preparo-conforme.txt" 2>&1
for _ in $(seq 1 24); do  # não mede com o relógio ainda dessincronizado
  [[ "$(adm 'timedatectl show -p NTPSynchronized --value')" == yes ]] && break; sleep 5
done
# O timedatectl acima ativa o systemd-timedated, que sai sozinho ~30 s depois e apaga seus
# diretórios em /tmp: marcar antes disso poria na janela um efeito que não é da ferramenta.
sleep 35
# Controle: mesma janela e os mesmos acessos administrativos, sem a ferramenta. O que aparecer
# aqui é efeito do acesso por SSH, não de uma leitura.
adm 'sudo touch /run/marca-evidencia; date -u +%Y-%m-%dT%H:%M:%SZ' > "$SAIDA/00-controle-marca.txt"
sleep 64
adm "$ACHAR" > "$SAIDA/00-controle-arquivos-alterados.txt"
sleep 15
adm 'sudo touch /run/marca-evidencia; date -u +%Y-%m-%dT%H:%M:%SZ' > "$SAIDA/01-marca.txt"
# A sessão do administrador (user@<uid>.service) leva ~10 s para encerrar depois do logout;
# sem esperar, ela aparece nos serviços da primeira execução e não na segunda.
sleep 15
executa 01-conforme "${COLETA[@]}"
executa 02-repeticao "${COLETA[@]}"
sleep 35  # deixa terminar qualquer efeito atrasado antes de olhar o disco
adm "$ACHAR" > "$SAIDA/02-arquivos-alterados.txt"
# Serviços iniciados desde a marca: o login por SSH sobe a sessão do usuário (efeito do acesso,
# PRD I1); qualquer outro serviço seria efeito de uma leitura.
adm 'sudo journalctl --since "@$(stat -c %Y /run/marca-evidencia)" -q --no-pager -o short-iso | grep -E "systemd\[[0-9]+\]: (Starting|Started) " || true' \
  > "$SAIDA/02-servicos-iniciados.txt"
PYTHON=".venv/Scripts/python"; [[ -x "$PYTHON" ]] || PYTHON=".venv/bin/python"
"$PYTHON" "$LAB_DIR/gravar_leituras.py" conforme --anonimizar  # amostras reais dos testes

echo "== fase 2: host com desvios"
bash "$LAB_DIR/preparar-desvios.sh" > "$SAIDA/03-preparo-desvios.txt" 2>&1
executa 03-desvios "${COLETA[@]}"
"$PYTHON" "$LAB_DIR/gravar_leituras.py" desvios --anonimizar

echo "== fase 3: host inalcançável"
executa 04-nome-nao-resolve --host "$VM.invalid" --usuario "$USUARIO_COLETA" --chave "$CHAVES/coleta"
executa 05-sem-resposta --host "$IP" --porta 2222 --usuario "$USUARIO_COLETA" --chave "$CHAVES/coleta"
executa 06-chave-recusada --host "$IP" --usuario "$USUARIO_COLETA" --chave "$CHAVES/estranha" --fingerprint "$FP"
executa 07-fingerprint-divergente --host "$IP" --usuario "$USUARIO_COLETA" --chave "$CHAVES/coleta" \
  --fingerprint "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
# SSH parado com religamento agendado: sem ele, parar o SSH tiraria o acesso para religá-lo.
adm 'sudo systemd-run --quiet --on-active=60 systemctl start ssh.socket ssh.service && sudo systemctl stop ssh.socket ssh.service'
sleep 3
executa 08-ssh-fora-do-ar "${COLETA[@]}"
for _ in $(seq 1 18); do adm true 2>/dev/null && break; sleep 5; done
adm true && echo "SSH religado."
