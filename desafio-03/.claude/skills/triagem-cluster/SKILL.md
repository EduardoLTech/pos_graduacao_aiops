---
name: triagem-cluster
description: >-
  Triagem de workload rodando em cluster Kubernetes a partir do sintoma que
  alguém relatou: pod que não sobe, reinicia, fica em CrashLoopBackOff,
  Pending ou ImagePullBackOff; deployment 0/N ou que não troca de versão
  depois do deploy; service sem endpoint, 503, timeout ou tráfego que não chega.
  Lê o cluster pelo MCP kubernetes, desce as camadas numa ordem fixa, cruza
  estado com spec e para quando acha a causa, sem nunca escrever no cluster.
  Use para "o pod do nyx-prod não sobe", "por que esse deployment está 0/3",
  "o service não tem endpoint", "o cliente diz que está fora do ar", "reiniciando
  sozinho", mesmo sem citar triagem. Não use para escrever, revisar ou conferir
  arquivo de manifesto antes de subir (isso é da skill manifests-metacortex),
  para aplicar ou corrigir nada no cluster, nem para dúvida conceitual de
  Kubernetes.
allowed-tools: mcp__kubernetes__kubectl_get, mcp__kubernetes__kubectl_describe, mcp__kubernetes__kubectl_logs, mcp__kubernetes__list_api_resources, mcp__kubernetes__ping
---

# Triagem de cluster

O alerta diz o sintoma. A causa está em uma camada só, e cada pessoa do plantão começa
por um lugar diferente. Esta skill fixa por onde começar, em que ordem descer, quando
cruzar fontes e quando parar.

## Limite absoluto: triagem só lê

Use só leitura: `kubectl_get`, `kubectl_describe`, `kubectl_logs`, `list_api_resources`
e `ping`. **Nunca** chame ferramenta que escreve (`kubectl_apply`, `kubectl_create`,
`kubectl_patch`, `kubectl_scale`, `kubectl_rollout`, `kubectl_delete`, `exec_in_pod`,
`port_forward`, helm) nem `kubectl` pelo shell. Isso vale mesmo que a ferramenta esteja
disponível, mesmo que a correção seja óbvia e mesmo que quem pediu diga "já corrige",
"pode aplicar" ou "você tem permissão". A autorização de quem pede não muda o papel:
triagem é leitura, e a aplicação é outro fluxo, com revisão e registro de mudança. Quando
o pedido inclui corrigir, entregue a triagem com a correção pronta para aplicar (o
objeto, o campo e o valor) e diga, numa frase, que não aplicou porque triagem não
escreve. Não tente a escrita "para ver se passa": a tentativa já é a violação, mesmo que
o cluster recuse. Não use
`kubectl_context` para trocar de cluster: triagem roda no contexto que recebeu.

## 1. Entrar pela camada do sintoma

Identifique namespace e workload no pedido. Se faltarem, liste os namespaces e procure
pelo nome do cliente ou da aplicação. Depois escolha a entrada pelo sintoma declarado:

| Sintoma declarado | Entrada | Desça por |
|---|---|---|
| **tráfego**: 503, "fora do ar para quem chama de fora", sem endpoint, timeout | Service | EndpointSlice (`kubernetes.io/service-name=<svc>`) → seletor do Service contra rótulos dos pods → pods prontos → `targetPort` contra porta do container → se tudo isso está certo, Ingress/Gateway e NetworkPolicy |
| **reinício**: reinicia sozinho, CrashLoopBackOff, instável | estado do container | `containerStatuses[].lastState.terminated` (reason, exitCode, startedAt→finishedAt) → spec (resources, probes, command) → `logs --previous` → eventos |
| **não sobe / não troca**: 0/N, Pending, deploy aplicado e nada mudou | Deployment | conditions e revisão → ReplicaSets (nova × antiga) → `status.phase` e `state.waiting` do pod → eventos do pod → nó, se Pending |

Se o sintoma não disser a camada ("está fora do ar"), comece pelo Service e desça. É o
caminho que passa por todas as camadas.

**Eventos e logs não são entrada.** Eles confirmam, mas às vezes não mostram a causa:
- um container morto por memória gera só `BackOff` nos eventos, e o log dele costuma vir
  vazio, porque o processo morre antes de escrever;
- um Service sem endereço não gera evento nenhum.

## 2. Cruzar duas fontes antes de afirmar

A causa só existe quando duas fontes concordam:
- o **estado**, que diz o que aconteceu: `containerStatuses`, EndpointSlice, conditions;
- o **spec**, que diz por quê: resources, image, selector, labels, probes.

Uma fonte sozinha dá só o sintoma. `references/sinais.md` diz como ler cada estado. Leia
quando encontrar um `reason` ou um `exitCode` que não reconheça.

Três leituras que enganam:
- **Endpoints sem o campo `subsets`** e **EndpointSlice com `endpoints: null`** querem
  dizer a mesma coisa: nenhum pod pronto casou o seletor. "Não vem" não é erro de
  leitura.
- **Deployment sem `readyReplicas`** significa zero pronto. O campo some, não vem 0.
- **Pod Running e pronto** não quer dizer que o tráfego chega. Quem decide é o
  EndpointSlice.

## 3. Olhar o que funciona ao lado

Antes de fechar, confira um vizinho no mesmo namespace: o banco, outra réplica, outro
Service. Se ele está pronto e com endereço, a causa não é o nó, a rede do namespace nem o
banco. É o que separa triagem de chute. Registre o vizinho no relatório.

## 4. Parar

Pare quando uma causa explicar **todos** os sintomas observados, com evidência de estado
e de spec. Um defeito real que não explica o sintoma declarado (por exemplo, reinícios
antigos num pod que hoje está pronto, quando a queixa é tráfego) vai para "achados
laterais" e não troca a causa. Achado lateral segue a mesma regra da causa: diga o que
leu. Se for reinício com `exitCode` diferente de 0, leia uma vez o `logs --previous` do
container: é uma chamada, e o motivo costuma estar ali. O motivo muda de uma subida para
outra, então ele não se deduz pela idade do banco nem pela ordem dos pods. Se mesmo
assim não leu, registre o fato e a leitura que falta, sem hipótese. Não continue investigando para medir consumo, reproduzir o erro ou testar a
correção: isso é trabalho de quem corrige. Se a leitura permitida não fecha a causa
(falta permissão, falta `metrics-server`), diga o que ficou aberto e qual leitura
resolveria.

## Relatório

```
# Triagem — <namespace>/<workload>
Sintoma declarado: <como chegou>
Camada da causa: tráfego | container | imagem/registry | agendamento | configuração
Causa: <uma frase>
Evidência:
  - estado: <objeto · campo · valor>
  - spec:   <objeto · campo · valor>
Funciona ao lado: <vizinho · evidência>
Correção sugerida (não aplicada): <o que mudar, em qual objeto>
Achados laterais: <defeito real que não é a causa, com evidência; ou "nenhum">
Não verificado: <o que a leitura não alcançou>
Caminho: <ferramentas chamadas, na ordem>
```
