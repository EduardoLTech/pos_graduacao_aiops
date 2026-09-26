#!/usr/bin/env bash
# Roda cada frase de frases.tsv numa sessao limpa do claude -p e grava a transcricao.
#
# Uso (a partir de desafio-03/):
#   bash ticket-02-triagem-no-cluster/roteamento/rodar-matriz.sh <rodada> [ids...]
#   ex.: ... rodar-matriz.sh r2            (todas)
#        ... rodar-matriz.sh r3 05 07       (so algumas)
# Requer TRIAGEM_KUBECONFIG apontando para o kubeconfig de leitura.
#
# Cada sessao roda num diretorio temporario que so contem .claude/skills com as duas
# skills. Na primeira rodada, feita a partir de desafio-03/, uma sessao achou este
# frases.tsv e leu a rota esperada: o gabarito nao pode estar ao alcance do agente.
# --max-turns 3 basta para ver qual skill carrega: o disparo acontece no primeiro turno.
# As permissoes sao as das duas skills somadas, para nao favorecer nenhuma.
# No maximo 3 sessoes em paralelo: com 10, o npx do MCP estourava o timeout de conexao.
# Bash so para os scripts da skill de manifests: na rodada 2, comandos de leitura
# (ls, find, which) passaram sem pedir permissao, e um kubectl pelo shell leria com o
# kubeconfig pessoal, nao com o de leitura. As rodadas 2 e 3 rodaram antes desta negacao.
set -u
R="$1"; shift
T="$(pwd)/ticket-02-triagem-no-cluster"
DIR="$T/roteamento"
mkdir -p "$DIR/$R"
CAIXA="$(mktemp -d)"
trap 'rm -rf "$CAIXA"' EXIT
mkdir -p "$CAIXA/.claude"
cp -r .claude/skills "$CAIXA/.claude/"
export MCP_TIMEOUT="${MCP_TIMEOUT:-120000}" T DIR R CAIXA
export PERM="Skill,Read,Grep,Glob,mcp__kubernetes__kubectl_get,mcp__kubernetes__kubectl_describe,mcp__kubernetes__kubectl_logs,mcp__kubernetes__list_api_resources,mcp__kubernetes__ping,Bash(python *conferir_manifests.py*),Bash(python *inspecionar_imagem.py*)"

uma() {  # <id> <frase>
  cd "$CAIXA" && claude -p "$2" \
    --mcp-config "$T/laboratorio/mcp-kubernetes-leitura.json" --strict-mcp-config \
    --permission-mode default --allowedTools "$PERM" \
    --disallowedTools "Write,Edit,PowerShell,Bash(kubectl *),Bash(helm *),Bash(ls *),Bash(find *),Bash(which *),Bash(cat *)" \
    --max-turns 3 --output-format stream-json --verbose > "$DIR/$R/$1.jsonl" 2>"$DIR/$R/$1.err" < /dev/null
}
export -f uma

tail -n +2 "$DIR/frases.tsv" | while IFS=$'\t' read -r id frase _; do
  if [ $# -gt 0 ] && [[ ! " $* " =~ " $id " ]]; then continue; fi
  printf '%s\0%s\0' "$id" "$frase"
done | xargs -0 -n 2 -P 3 bash -c 'uma "$0" "$1"'
find "$DIR/$R" -name '*.err' -empty -delete
