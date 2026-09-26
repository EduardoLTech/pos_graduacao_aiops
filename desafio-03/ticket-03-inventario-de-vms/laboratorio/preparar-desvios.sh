#!/usr/bin/env bash
# Leva o host conforme para o estado com desvios. Rode preparar-conforme.sh antes.
set -euo pipefail
source "$(dirname "$0")/lab.env"
[[ -f "$ESTADO/ip" ]] || { echo "Laboratório não criado (rode criar.sh)." >&2; exit 1; }

# Chaves só públicas, descartáveis: a parte privada nunca é usada.
for nome in pessoal hostil legado; do
  [[ -f "$CHAVES/$nome.pub" ]] || ssh-keygen -q -t ed25519 -N "" -C x -f "$CHAVES/$nome"
done
pessoal="$(cut -d' ' -f1,2 "$CHAVES/pessoal.pub") neo@laptop"
# Comentário hostil (PRD P28): sequência de controle do terminal e texto imitando tabela.
hostil="$(cut -d' ' -f1,2 "$CHAVES/hostil.pub") neo$(printf '\033')[2K | x | conforme |"

admin_sudo "$LAB_DIR/remoto/desvios.sh" \
  "USUARIO_COLETA=$USUARIO_COLETA" \
  "CHAVE_PESSOAL=$pessoal" \
  "CHAVE_HOSTIL=$hostil" \
  "CHAVE_LEGADO=$(cut -d' ' -f1,2 "$CHAVES/legado.pub") legado@fornecedor" | tee "$ESTADO/preparo-desvios.txt"
