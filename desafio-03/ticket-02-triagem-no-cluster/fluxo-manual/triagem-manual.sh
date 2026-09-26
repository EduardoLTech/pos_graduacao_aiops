#!/usr/bin/env bash
# Fluxo manual de triagem dos tres chamados, na ordem em que foi feito, so com leitura.
# Cada comando tem equivalente direto numa ferramenta do mcp-server-kubernetes em modo
# so leitura (kubectl_get, kubectl_describe, kubectl_logs), e roda com o kubeconfig
# da ServiceAccount triagem-leitura: nenhum deles consegue escrever.
#
# Uso: bash triagem-manual.sh <kubeconfig-de-leitura> > saida-<data>.md
set -u
K="--kubeconfig $1"
passo() { echo; echo "\$ kubectl $*"; kubectl $K "$@" 2>&1; }

echo "# Triagem manual — $(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo; echo "## Chamado 1 — nyx-prod: a API do kube-news reinicia sozinha"
echo "Sintoma: reinicio. Entrada: o workload e o estado do container, nao os eventos."
passo -n nyx-prod get deploy,rs,pods -o wide
passo -n nyx-prod get pods -l app=nyx-api -o 'jsonpath={range .items[*]}{.metadata.name}{" restarts="}{.status.containerStatuses[0].restartCount}{" last="}{.status.containerStatuses[0].lastState.terminated.reason}{"/"}{.status.containerStatuses[0].lastState.terminated.exitCode}{" inicio="}{.status.containerStatuses[0].lastState.terminated.startedAt}{" fim="}{.status.containerStatuses[0].lastState.terminated.finishedAt}{"\n"}{end}'
passo -n nyx-prod get events --sort-by=.lastTimestamp
P=$(kubectl $K -n nyx-prod get pods -l app=nyx-api -o 'jsonpath={.items[0].metadata.name}')
passo -n nyx-prod logs "$P" --previous --tail=20
passo -n nyx-prod get deploy nyx-api -o 'jsonpath={.spec.template.spec.containers[0].resources}{"\n"}'
passo -n nyx-prod get limitrange,resourcequota
passo -n nyx-prod get pods -l app=nyx-postgres

echo; echo "## Chamado 2 — orion-stg: a loja parou depois de uma publicacao do Loom"
echo "Sintoma: deploy que nao troca. Entrada: rollout, revisao e o motivo de espera do container."
passo -n orion-stg get deploy,rs,pods -o wide
passo -n orion-stg get deploy orion-web -o 'jsonpath={.metadata.annotations.deployment\.kubernetes\.io/revision}{"\n"}{range .status.conditions[*]}{.type}={.status} {.reason}: {.message}{"\n"}{end}'
P=$(kubectl $K -n orion-stg get pods -l app=orion-web -o 'jsonpath={.items[0].metadata.name}')
passo -n orion-stg get pod "$P" -o 'jsonpath={.status.containerStatuses[0].state.waiting}{"\n"}'
passo -n orion-stg get pods -l app=orion-postgres

echo; echo "## Chamado 3 — nyx-stg: 503 para quem chama de fora"
echo "Sintoma: trafego. Entrada: Service e EndpointSlice, antes de qualquer pod."
passo -n nyx-stg get svc,deploy,pods -o wide
passo -n nyx-stg get endpoints nyx-api -o yaml
passo -n nyx-stg get endpointslices -l kubernetes.io/service-name=nyx-api -o 'jsonpath={range .items[*]}{.metadata.name}{" endpoints="}{.endpoints}{"\n"}{end}'
passo -n nyx-stg get svc nyx-api -o 'jsonpath={.spec.selector}{"\n"}'
passo -n nyx-stg get pods --show-labels
passo -n nyx-stg get pods -l app=nyx-api
echo; echo "Pista lateral: os pods da API tem reinicios. Estado e log do reinicio, para nao chutar o motivo."
passo -n nyx-stg get events --sort-by=.lastTimestamp
passo -n nyx-stg get pods -l app=nyxapi -o 'jsonpath={range .items[*]}{.metadata.name}{" restarts="}{.status.containerStatuses[0].restartCount}{" last="}{.status.containerStatuses[0].lastState.terminated.reason}{"/"}{.status.containerStatuses[0].lastState.terminated.exitCode}{" inicio="}{.status.containerStatuses[0].lastState.terminated.startedAt}{" fim="}{.status.containerStatuses[0].lastState.terminated.finishedAt}{"\n"}{end}'
for P in $(kubectl $K -n nyx-stg get pods -l app=nyxapi -o 'jsonpath={.items[*].metadata.name}'); do
  passo -n nyx-stg logs "$P" --previous --tail=25
done
passo -n nyx-stg get endpointslices -l kubernetes.io/service-name=nyx-postgres -o 'jsonpath={range .items[*]}{.metadata.name}{" enderecos="}{.endpoints[*].addresses}{"\n"}{end}'
