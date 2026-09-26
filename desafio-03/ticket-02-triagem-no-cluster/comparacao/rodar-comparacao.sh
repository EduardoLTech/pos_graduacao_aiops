#!/usr/bin/env bash
# Roda os prompts dos chamados com e sem a skill de triagem, para comparar saida,
# custo e tempo. Mesmo MCP de leitura, mesmas ferramentas, mesmo prompt.
#   com: sessao num diretorio temporario com .claude/skills (as duas skills)
#   sem: diretorio temporario vazio, e a ferramenta Skill negada (cobre skills de usuario)
#
# Uso (a partir de desafio-03/):
#   bash ticket-02-triagem-no-cluster/comparacao/rodar-comparacao.sh <com|sem> <rodada> <chamado...>
#   ex.: ... rodar-comparacao.sh sem r1 01-chamado-1-nyx-prod 03-chamado-3-nyx-stg
# Requer TRIAGEM_KUBECONFIG apontando para o kubeconfig de leitura.
set -u
COND="$1"; R="$2"; shift 2
T="$(pwd)/ticket-02-triagem-no-cluster"
OUT="$T/comparacao/$COND-$R"
mkdir -p "$OUT"
CAIXA="$(mktemp -d)"
trap 'rm -rf "$CAIXA"' EXIT
export MCP_TIMEOUT="${MCP_TIMEOUT:-120000}"
LEITURA="Read,Grep,Glob,mcp__kubernetes__kubectl_get,mcp__kubernetes__kubectl_describe,mcp__kubernetes__kubectl_logs,mcp__kubernetes__list_api_resources,mcp__kubernetes__ping"
if [ "$COND" = com ]; then
  mkdir -p "$CAIXA/.claude" && cp -r .claude/skills "$CAIXA/.claude/"
  PERM="Skill,$LEITURA"; NEGA="Bash,PowerShell"
else
  PERM="$LEITURA"; NEGA="Skill,Bash,PowerShell"
fi
for c in "$@"; do
  ( cd "$CAIXA" && claude -p "$(cat "$T/execucoes/$c/prompt.txt")" \
    --mcp-config "$T/laboratorio/mcp-kubernetes-leitura.json" --strict-mcp-config \
    --permission-mode default --allowedTools "$PERM" --disallowedTools "$NEGA" \
    --output-format stream-json --verbose > "$OUT/$c.jsonl" 2>"$OUT/$c.err" < /dev/null ) &
done
wait
find "$OUT" -name '*.err' -empty -delete
