#!/usr/bin/env bash
# Apaga tudo o que criar.sh criou. Uso: bash laboratorio/destruir.sh --confirmo
set -euo pipefail
source "$(dirname "$0")/lab.env"

echo "Vai apagar no projeto $PROJETO: VM $VM, firewall $FIREWALL, sub-rede $SUBREDE, rede $REDE."
if [[ "${1:-}" != "--confirmo" ]]; then
  echo "Nada foi apagado. Rode de novo com --confirmo." >&2
  exit 1
fi

apagar() {  # ignora só "não existe"; qualquer outro erro interrompe
  local saida
  if ! saida="$("$@" --project "$PROJETO" --quiet 2>&1)"; then
    grep -qi "not found\|was not found" <<<"$saida" || { echo "$saida" >&2; exit 1; }
  fi
}
apagar gcloud compute instances delete "$VM" --zone "$ZONA"
apagar gcloud compute firewall-rules delete "$FIREWALL"
apagar gcloud compute networks subnets delete "$SUBREDE" --region "$REGIAO"
apagar gcloud compute networks delete "$REDE"

rm -f "$ESTADO/ip" "$ESTADO/known_hosts" "$ESTADO/hostkeys" "$ESTADO/fingerprint"
echo "Laboratório destruído."
gcloud compute instances list --project "$PROJETO" --filter="name=$VM" --format='value(name)'
