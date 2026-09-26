#!/usr/bin/env bash
# Cria o host de validação no GCP (ADR 005): rede própria, SSH só do IP do operador, VM sem
# conta de serviço e sem chaves SSH do projeto. Tem custo enquanto a VM existir.
# Uso: bash laboratorio/criar.sh --confirmo-custo
set -euo pipefail
source "$(dirname "$0")/lab.env"

IP_OPERADOR="${IP_OPERADOR:-$(curl -fsS https://api.ipify.org)}"
[[ "$IP_OPERADOR" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "IP do operador inválido: $IP_OPERADOR" >&2; exit 2; }

cat <<EOF
Vai criar no projeto $PROJETO:
  rede      $REDE (sub-rede $SUBREDE $FAIXA_SUBREDE em $REGIAO), sem regras padrão
  firewall  $FIREWALL: entrada tcp:22 só de $IP_OPERADOR/32
  VM        $VM ($TIPO_MAQUINA, $FAMILIA_IMAGEM, zona $ZONA), sem conta de serviço,
            block-project-ssh-keys=TRUE, enable-oslogin=FALSE
EOF
if [[ "${1:-}" != "--confirmo-custo" ]]; then
  echo "Nada foi criado. Rode de novo com --confirmo-custo." >&2
  exit 1
fi

if [[ ! -f "$CHAVES/admin" ]]; then
  ssh-keygen -q -t ed25519 -N "" -C "labadmin@laboratorio" -f "$CHAVES/admin"
fi

gcloud compute networks create "$REDE" --project "$PROJETO" --subnet-mode=custom
gcloud compute networks subnets create "$SUBREDE" --project "$PROJETO" \
  --network "$REDE" --region "$REGIAO" --range "$FAIXA_SUBREDE"
gcloud compute firewall-rules create "$FIREWALL" --project "$PROJETO" \
  --network "$REDE" --direction INGRESS --action ALLOW --rules tcp:22 \
  --source-ranges "$IP_OPERADOR/32"

gcloud compute instances create "$VM" --project "$PROJETO" --zone "$ZONA" \
  --machine-type "$TIPO_MAQUINA" \
  --image-family "$FAMILIA_IMAGEM" --image-project "$PROJETO_IMAGEM" \
  --boot-disk-size 10GB \
  --subnet "$SUBREDE" \
  --no-service-account --no-scopes \
  --shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring \
  --metadata "block-project-ssh-keys=TRUE,enable-oslogin=FALSE,enable-guest-attributes=TRUE,ssh-keys=$USUARIO_ADMIN:$(cat "$CHAVES/admin.pub")"

ip_externo > "$ESTADO/ip"
echo "IP externo: $(cat "$ESTADO/ip")"

# Chave de host pelo canal do GCP (guest attributes), nunca por confiança na primeira conexão.
echo "Aguardando o agente publicar as chaves de host..."
for _ in $(seq 1 36); do
  if gcloud compute instances get-guest-attributes "$VM" --project "$PROJETO" --zone "$ZONA" \
       --query-path=hostkeys/ --format='value(key,value)' > "$ESTADO/hostkeys" 2>/dev/null \
     && [[ -s "$ESTADO/hostkeys" ]]; then
    break
  fi
  sleep 5
done
[[ -s "$ESTADO/hostkeys" ]] || { echo "As chaves de host não foram publicadas em 3 min." >&2; exit 1; }

ip="$(cat "$ESTADO/ip")"
: > "$ESTADO/known_hosts"
while read -r tipo chave; do
  echo "$ip $tipo $chave" >> "$ESTADO/known_hosts"
done < "$ESTADO/hostkeys"
grep ' ssh-ed25519 ' "$ESTADO/known_hosts" | cut -d' ' -f2- | ssh-keygen -lf - \
  | awk '{print $2}' > "$ESTADO/fingerprint"
echo "Fingerprint Ed25519 do host: $(cat "$ESTADO/fingerprint")"

echo "Aguardando SSH da conta administrativa..."
for _ in $(seq 1 24); do
  if ssh -i "$CHAVES/admin" -o UserKnownHostsFile="$ESTADO/known_hosts" \
       -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -o BatchMode=yes \
       -o ConnectTimeout=5 "$USUARIO_ADMIN@$ip" true 2>/dev/null; then
    echo "Pronto. Próximo passo: bash laboratorio/preparar-conforme.sh"
    exit 0
  fi
  sleep 5
done
echo "SSH da conta administrativa não respondeu em 2 min." >&2
exit 1
