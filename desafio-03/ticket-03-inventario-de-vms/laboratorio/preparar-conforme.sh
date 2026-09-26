#!/usr/bin/env bash
# Coloca o host no estado conforme e cria o usuário de coleta com a chave da plataforma.
# Roda fora das janelas de medição: acesso administrativo entre duas execuções quebraria a
# prova de repetição (ADR 005).
set -euo pipefail
source "$(dirname "$0")/lab.env"
[[ -f "$ESTADO/ip" ]] || { echo "Laboratório não criado (rode criar.sh)." >&2; exit 1; }

if [[ ! -f "$CHAVES/coleta" ]]; then
  ssh-keygen -q -t ed25519 -N "" -C "$COMENTARIO_COLETA" -f "$CHAVES/coleta"
fi

admin_sudo "$LAB_DIR/remoto/conforme.sh" \
  "USUARIO_COLETA=$USUARIO_COLETA" \
  "CHAVE_COLETA=$(cat "$CHAVES/coleta.pub")" \
  "NODE_EXPORTER_VERSAO=$NODE_EXPORTER_VERSAO" | tee "$ESTADO/preparo-conforme.txt"
