# Fluxo manual de triagem (2026-09-25)

A skill nasceu desta triagem, feita à mão nos três chamados antes de qualquer linha de
instrução. Cada comando está em `triagem-manual.sh`, e a saída real em
`saida-2026-09-25.md`. Todos rodaram com o kubeconfig da ServiceAccount de leitura
(`../laboratorio/`), então nenhum deles conseguiria escrever no cluster.

## O que cada chamado mostrou

| Chamado | Sintoma declarado | Onde a causa estava | Onde ela **não** estava |
|---|---|---|---|
| 1 · nyx-prod | "a API reinicia sozinha" | `containerStatuses[].lastState.terminated`: `OOMKilled`, exit 137, **2 a 3 s** depois de subir; o spec tem limite de 24Mi | nos **eventos** (`BackOff`, `Started` e readiness recusada) e nos **logs** (`--previous` vem vazio: o processo morre antes de escrever) |
| 2 · orion-stg | "o pod nunca trocou depois da publicação" | `state.waiting` do container: `ErrImagePull` → `NotFound` → `v1.14.2: not found`. Passados os 10 min do prazo, o Deployment passa a `Progressing=False ProgressDeadlineExceeded`; antes disso ele ainda mostra `Progressing=True` | no pod em si, que nunca rodou; e nos logs, que não existem |
| 3 · nyx-stg | "503 para quem chama de fora" | Service seleciona `app=nyx-api`, os pods têm `app=nyxapi`; o Endpoints vem **sem** o campo `subsets` e o EndpointSlice vem com `endpoints: null` | nos pods (2/2 prontos) e nos eventos, que só têm o `BackOff` da subida e nada sobre o Service (ver abaixo) |

O que funcionava ao lado, em todos os chamados, era o PostgreSQL do mesmo namespace:
pronto, sem reinício e, no nyx-stg, com o EndpointSlice apontando para o pod.

**Pista falsa no Chamado 3.** Os dois pods da API sobem com 2 reinícios. A saída gravada
mostra o motivo: `lastState` `Error/1` em 2 a 3 s, e o `logs --previous` dos dois termina
em `connect ECONNREFUSED 10.96.74.14:5432`. A API subiu antes de o PostgreSQL aceitar
conexão e caiu. Depois que o banco ficou pronto, os dois pods ficaram prontos e estáveis.
O defeito é real (a aplicação não espera o banco), mas não explica o 503. A triagem
precisa registrar isso como achado lateral, sem trocar de causa.

Numa instância anterior do mesmo ambiente, o log de um desses reinícios mostrava outra
coisa: `CREATE TABLE "Posts"` concorrente entre as duas réplicas, com violação de
unicidade em `pg_type`. Esse log não foi gravado, e os pods não existem mais. O caso
fica como registro de que o motivo do reinício muda de uma subida para outra, e por
isso a triagem não pode afirmar o motivo sem ler o log daquele reinício.

**Ambiente limpo.** A primeira passada deste fluxo rodou num namespace que ainda guardava
os eventos da aplicação literal (os pods da `kube-news:v1`, com `no match for platform`),
e eles contaminavam a leitura. Os três namespaces foram recriados só com a variante de
laboratório, e recriados de novo depois de um travamento do nó (`../laboratorio/`). A
`saida-2026-09-25.md` é a passada final, mais de 30 min depois da subida. Ela inclui os
eventos e os logs de reinício do nyx-stg, que as passadas anteriores não coletavam.

## O que isso ensinou sobre método

1. **Começar pelos eventos ou pelos logs falha em dois dos três chamados.** No 1, os
   eventos dizem só `BackOff` e o log vem vazio. No 3, os eventos só falam dos reinícios
   da subida, que são a pista falsa, e nenhum evento aponta para o Service. O que sempre
   respondeu foi o **estado** do objeto na camada certa: `containerStatuses` no 1 e no
   2, `EndpointSlice` no 3.
2. **O sintoma declarado escolhe a camada de entrada.** Reinício leva ao estado do
   container. Deploy que não troca leva ao rollout e ao motivo de espera. Tráfego leva
   ao Service e aos endereços. Começar pelo pod no Chamado 3 mostra tudo verde e manda a
   pessoa embora.
3. **Cruzar duas fontes é o que fecha a causa.** O estado diz o que aconteceu (morto por
   memória, tag inexistente, zero endereços) e o spec diz por quê (24Mi, a tag escrita,
   seletor contra rótulo). Uma fonte só dá o sintoma.
4. **Olhar ao lado evita o chute.** Com o banco pronto no mesmo namespace, "problema de
   banco" e "problema de nó" saem da lista sem investigação extra.
5. **Parar quando a causa explica todos os sintomas.** No Chamado 1, medir o consumo real
   do Node exigiria `metrics-server` ou `exec`. Isso é trabalho da correção, não da
   triagem.
6. **O texto do erro de pull já classifica a causa:** `not found` é tag ou imagem
   inexistente; `no match for platform` é arquitetura (foi o que derrubou a `kube-news:v1`
   na aplicação literal, `../ambientes/aplicacao-literal-2026-09-25.txt`);
   `unauthorized` ou `pull access denied` é credencial ou repositório privado.
7. **O motivo de um reinício só sai do log daquele reinício.** Com `Error/1`, o
   `logs --previous` tem a causa (aqui, `ECONNREFUSED` no banco). É uma leitura barata,
   e sem ela o motivo vira chute.
8. **"Não vem" é diferente de "vem vazio".** O Endpoints do Chamado 3 não traz `subsets`,
   e o EndpointSlice traz `endpoints: null`. Os dois querem dizer "nenhum pod casou o
   seletor", e a triagem precisa reconhecer as duas formas.

## O que o fluxo manual não cobriu

- O consumo real de memória do kube-news: não há `metrics-server` no kind, e `exec` está
  fora do papel de leitura.
- A história "o pod nunca trocou" do Chamado 2: no laboratório não havia uma revisão
  anterior rodando (revisão 1), então não existe réplica antiga servindo. Em produção,
  haveria.
- Pod em `Pending` por falta de recurso, `CreateContainerConfigError` e falha de probe
  de liveness: nenhum chamado reproduz esses casos. Eles entraram na skill como
  referência, sem teste.
