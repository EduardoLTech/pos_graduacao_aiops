#!/usr/bin/env bash
# Regressao completa do script de conferencia, para comparar sistemas operacionais.
# Rodar a partir de ticket-01-padrao-de-manifests/:
#   bash fluxo-manual/07-verificacoes-pendentes/regressao.sh <titulo>
# Imprime: os 18 casos de 06-correcoes-medios e o codigo de saida de cada execucao
# e controle, com o resumo "Trivy: ..." que o script escreve.
set -u
SKILL="skill/manifests-metacortex"
SCRIPT="$SKILL/scripts/conferir_manifests.py"
PY="$(command -v python3 || command -v python)"

bash fluxo-manual/06-correcoes-medios/rodar-casos.sh "$SKILL" "$1 — casos de 06-correcoes-medios"
echo
echo "| Alvo | Código | Resumo |"
echo "|---|---|---|"
for alvo in \
  execucoes/01-escrita-fake-shop/manifests \
  execucoes/02-conferencia-nyx/nyx-barrado.yaml \
  execucoes/02-conferencia-nyx/nyx-corrigido.yaml \
  execucoes/03-escrita-encontros-tech/manifests \
  execucoes/04-escrita-fake-shop-stg/manifests \
  execucoes/05-conferencia-nyx-skill-atual/nyx-barrado.yaml \
  execucoes/05-conferencia-nyx-skill-atual/nyx-corrigido.yaml \
  fluxo-manual/05-correcoes-pos-revisao/values.yaml \
  fluxo-manual/05-correcoes-pos-revisao/list.yaml \
  fluxo-manual/05-correcoes-pos-revisao/so-service.yaml; do
  resumo="$("$PY" "$SCRIPT" "$alvo" 2>&1 | grep -m1 -E '^Trivy:|ERRO')"
  cod="$("$PY" "$SCRIPT" "$alvo" >/dev/null 2>&1; echo $?)"
  echo "| $alvo | $cod | $resumo |"
done
for alvo in nyx-barrado nyx-corrigido; do
  cod="$("$PY" "$SCRIPT" "execucoes/02-conferencia-nyx/$alvo.yaml" --sem-trivy >/dev/null 2>&1; echo $?)"
  echo "| $alvo --sem-trivy | $cod | barra vence incompleto: 1; sem barra: 3 |"
done
