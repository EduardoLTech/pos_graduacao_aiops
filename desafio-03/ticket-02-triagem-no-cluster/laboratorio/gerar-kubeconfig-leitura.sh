#!/usr/bin/env bash
# Gera um kubeconfig que so autentica como triagem/triagem-leitura (ClusterRole view).
# O MCP da triagem recebe este arquivo via KUBECONFIG, e nao o kubeconfig pessoal.
#
# Uso: bash gerar-kubeconfig-leitura.sh <contexto-admin> <arquivo-de-saida> [duracao]
#   contexto-admin  contexto que consegue criar token (ex.: kind-metacortex-lab)
#   duracao         validade do token (padrao 24h); vencido, e so gerar de novo
# O arquivo de saida contem credencial: grave-o fora do repositorio (ex.: ~/.kube/).
# No Windows o umask nao tem efeito e o arquivo fica legivel por outros usuarios da
# maquina; o risco e limitado porque o token so le e vence na duracao pedida.
set -euo pipefail
CTX="$1"; SAIDA="$2"; DURACAO="${3:-24h}"

kubectl --context "$CTX" apply -f "$(dirname "$0")/rbac-triagem.yaml" >/dev/null
SERVER="$(kubectl config view --raw -o jsonpath="{.clusters[?(@.name==\"$CTX\")].cluster.server}")"
CA="$(kubectl config view --raw -o jsonpath="{.clusters[?(@.name==\"$CTX\")].cluster.certificate-authority-data}")"
TOKEN="$(kubectl --context "$CTX" -n triagem create token triagem-leitura --duration "$DURACAO")"

umask 077
cat > "$SAIDA" <<EOF
apiVersion: v1
kind: Config
current-context: triagem-leitura
clusters:
  - name: laboratorio
    cluster: {server: "$SERVER", certificate-authority-data: "$CA"}
contexts:
  - name: triagem-leitura
    context: {cluster: laboratorio, user: triagem-leitura}
users:
  - name: triagem-leitura
    user: {token: "$TOKEN"}
EOF
echo "kubeconfig de leitura gravado em $SAIDA (token valido por $DURACAO)"
