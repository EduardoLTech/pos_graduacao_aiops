# Laboratório: cluster, identidade de leitura e MCP

## Cluster

`kind create cluster --name metacortex-lab` (kind v0.27.0, Kubernetes v1.32.2, nó único
x86_64). Os três ambientes estão em `../ambientes/`. O único desvio em relação ao
enunciado é a imagem do kube-news, explicado em `../ambientes/kustomization.yaml`.

```sh
kubectl kustomize ../ambientes > ../ambientes/renderizado.yaml
kubectl apply -f ../ambientes/renderizado.yaml
bash gerar-kubeconfig-leitura.sh kind-metacortex-lab ~/.kube/triagem-leitura.yaml 24h
export TRIAGEM_KUBECONFIG=~/.kube/triagem-leitura.yaml
```

## Como a triagem fica impedida de escrever

O enunciado pede o MCP "em modo não-destrutivo". Medido na versão 4.1.7
(`ferramentas-por-modo.txt`, gerado por `listar_ferramentas_mcp.py`), esse modo não
basta:

| Modo do mcp-server-kubernetes 4.1.7 | Ferramentas | Ainda escreve ou executa |
|---|---|---|
| sem restrição | 23 | tudo |
| `ALLOW_ONLY_NON_DESTRUCTIVE_TOOLS=true` | 18 | `kubectl_apply`, `kubectl_create`, `kubectl_patch`, `kubectl_scale`, `kubectl_rollout`, `exec_in_pod`, `port_forward`, `install_helm_chart`, `upgrade_helm_chart` |
| `ALLOW_ONLY_READONLY_TOOLS=true` | 8 | no cluster, nada. Localmente, `kubectl_context set` grava o contexto corrente no kubeconfig, o que é inócuo no kubeconfig isolado, que tem um contexto só |

"Não-destrutivo" só remove o que apaga. A triagem precisa de "não escreve", então a
garantia é feita em quatro camadas, da mais forte para a mais fraca:

1. **RBAC no apiserver** (`rbac-triagem.yaml`). O MCP autentica como a ServiceAccount
   `triagem/triagem-leitura`, com o ClusterRole `view` mais leitura de Node. Nenhum
   verbo de escrita, nem Secrets, `pods/exec` ou `pods/portforward`. Provado
   com `kubectl auth can-i` e com três tentativas reais de escrita (create configmap,
   scale deployment, patch service), todas recusadas pelo servidor com `Forbidden`
   (`prova-escrita.txt`). As quatro tentativas que o agente fez em `../limite-escrita/`
   também voltaram `Forbidden`. Vale mesmo que todas as
   outras camadas falhem.
2. **Kubeconfig isolado** (`gerar-kubeconfig-leitura.sh`). O MCP recebe só esse arquivo,
   via `KUBECONFIG`, e não o kubeconfig pessoal com contextos de EKS e GKE. O agente não
   tem para onde trocar de cluster. O token vence em 24 h.
3. **MCP em modo só leitura** (`mcp-kubernetes-leitura.json`). As ferramentas de
   escrita nem são registradas: o agente não as vê.
4. **Permissões da sessão e texto da skill.** `--allowedTools` lista só as ferramentas
   de leitura, `--disallowedTools` nega Bash e PowerShell (sem `kubectl` pelo shell), e o
   `SKILL.md` abre com o limite absoluto.

Nas execuções, o `resumir_transcricao.py` conta as chamadas a ferramentas de escrita.
Todas deram zero.

## Armadilhas do ambiente

- **Primeira subida do MCP.** O `npx -y mcp-server-kubernetes@4.1.7` levou 94 s na
  primeira execução, para baixar o pacote. O Claude Code desiste antes e marca o servidor
  como `failed` (`CONNECT_TIMEOUT`). Com o pacote em cache, a subida leva 4,6 s. Os
  scripts exportam `MCP_TIMEOUT=120000`.
- **Cache do npx corrompido.** Uma subida interrompida deixou o pacote `jose` pela metade
  no cache, e o servidor passou a morrer na partida com `ERR_MODULE_NOT_FOUND`. A solução
  foi apagar o diretório daquele pacote em `npm-cache/_npx/`.
- **Sessões em paralelo.** Com 10 sessões subindo o MCP ao mesmo tempo, várias estouraram
  o timeout. O roteamento roda com no máximo 3.
- **Travamento do nó (2026-09-25, ~23:30 UTC).** O kind inteiro parou por alguns minutos:
  o apiserver e o controller-manager reiniciaram e as probes do CoreDNS falharam. A VM
  do Docker tem 3,7 GiB. Os pods do nyx-stg caíram com `getaddrinfo nyx-postgres` e
  depois com liveness por timeout, e acumularam reinícios que nada têm a ver com o
  chamado. Antes das medições seguintes, os três namespaces foram recriados para voltar
  ao estado das primeiras execuções.
