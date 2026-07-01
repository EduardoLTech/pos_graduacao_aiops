# Checkpoint 06 — Endurecendo a NetworkPolicy do Sentinel

> Playbook de IA Operacional da Aegis — Segurança. Transforma uma NetworkPolicy
> permissiva (allow-all disfarçado) na versão endurecida com default-deny, e a
> submete a um ciclo de verificação e refino antes de aprovar para produção.

## 1. Decisões de método

**A dor.** Um manifesto de NetworkPolicy do namespace `sentinel-prod` chegou
permissivo demais — `podSelector: {}` pegando todos os pods e regras `- {}`
liberando qualquer ingress e qualquer egress. Um erro desses expõe o produto core.
Antes de virar item do playbook, esse tipo de artefato crítico precisa **nascer
endurecido e passar por verificação** — não sair na primeira tentativa.

**Framework — RISE (Role-Input-Steps-Expectation)** para o elo de geração. A tarefa
é procedural e parte de um **input concreto** (manifesto + regras do padrão + mapa
de serviços) para um **artefato de saída bem definido** (YAML aplicável). O `Role`
fixa a régua de menor privilégio; o `Input` cola manifesto/spec/mapa; o `Steps`
força a ordem diagnóstico → fluxos → seletores → default-deny → DNS → montagem; o
`Expectation` vira o critério de pronto. Descartados: **BAB** (não é narrar uma
transformação de estado antes/depois), **CARE** (o valor não está num exemplo
colado, e sim na **conformidade com a spec**), **RTF/TAG** (curtos demais para um
artefato com tantas invariantes de segurança).

**Técnica — Chain-of-Verification, variante factor-revise.** O enunciado pede que a
IA **critique a própria saída, levante as perguntas de verificação que um revisor de
segurança faria e melhore a cada rodada**. Isso é exatamente o ciclo CoVe: gerar →
planejar verificações → **executar as verificações isoladas** → revisar. O ponto
não-óbvio é o **isolamento**: a auditoria roda numa conversa nova, sem a
justificativa de quem gerou o manifesto — senão o modelo confirma o que ele mesmo
escreveu (viés de confirmação). A pergunta aqui é **binária/de conformidade**
(*allow-all é errado*), o que é território do CoVe e não do self-refine (que
responde *“está bom o suficiente?”*). Do self-refine o laço herda só a disciplina de
**critérios explícitos** e **teto de rodadas** (máx. 3).

**Estrutura da entrega — três prompts parametrizáveis** (um por elo do ciclo), todos
em `seguranca/endurecer-networkpolicy/`:

| Elo | Prompt | Papel |
|-----|--------|-------|
| Geração | [`prompt.md`](seguranca/endurecer-networkpolicy/prompt.md) | RISE → **v1** endurecida |
| Verificação | [`prompt-verificacao.md`](seguranca/endurecer-networkpolicy/prompt-verificacao.md) | CoVe plan+execute (isolado) → **achados** |
| Refino | [`prompt-refino.md`](seguranca/endurecer-networkpolicy/prompt-refino.md) | CoVe revise → **v2** + changelog |

**Parametrização.** Geração: `{{manifesto}}`, `{{regras_padrao}}`,
`{{mapa_servicos}}`, `{{namespace}}` (opc.), `{{provedor}}` (opc.). Verificação:
`{{manifesto_candidato}}` + regras/mapa. Refino: `{{manifesto_anterior}}`,
`{{achados_verificacao}}` + regras/mapa. Trocando manifesto + regras + mapa, o mesmo
ciclo endurece a política de qualquer namespace.

**Meta-prompting.** Os três prompts foram gerados dirigindo o modelo forte
(`claude-opus-4-8`) e curados à mão: cortei redundância, fixei o formato de saída
(YAML aplicável + tabela fluxo→regra + changelog), e blindei os edge cases de
segurança (labels só do mapa; DNS explícito; comentário por regra; zero allow-all).
Recomendado executar com `claude-sonnet-4-6`.

## 2. Entregável — prompts parametrizáveis

> O conteúdo integral dos três prompts está em
> `seguranca/endurecer-networkpolicy/` para não duplicar a fonte da verdade (DRY de
> prompt). Abaixo, o essencial de cada elo.

- **Geração (RISE)** — recebe o manifesto permissivo + regras + mapa e emite a v1
  com default-deny explícito, ingress/egress mínimos e um comentário por regra;
  critério de pronto proíbe qualquer `- {}`/`podSelector: {}` aberto e exige que todo
  seletor use label/porta do mapa (ou marque `⚠ label ausente`).
- **Verificação (CoVe, isolado)** — revisor de segurança independente que **planeja**
  as perguntas de auditoria (default-deny? sobrou allow-all? ingress/egress só o que
  a spec autoriza? seletores batem com o mapa? DNS tratado? comentário por regra?) e
  **executa** cada uma com `PASS/FAIL` + trecho do YAML como evidência; veredito
  `APROVADO` só sem nenhum FAIL.
- **Refino (CoVe revise)** — endereça **cada** achado sem regredir o que já passou,
  reemite o YAML completo e entrega o changelog `achado → correção`.

## 3. Execução (real, verificada)

> **Status: execução manual verificada.** Os três elos foram rodados em cadeia (v1
> na conversa de geração, verificação numa conversa nova isolada, refino de volta na
> conversa de geração). Outputs reais colados verbatim ao fim desta seção. Resultado
> resumido: **a v1 já passou na auditoria sem nenhum FAIL** — o ciclo convergiu em
> uma rodada e o refino declarou "sem alterações necessárias".

**Modelo de execução:** `claude-sonnet-4-6`.

### Como rodar o ciclo (v1 → verificação → v2)

**➊ Geração (conversa A).** Cole o corpo de `prompt.md` (do primeiro `#`, sem o
front-matter) e preencha:

- `{{namespace}}` = `sentinel-prod`
- `{{provedor}}` = `nenhum`
- `{{manifesto}}` =
  ```yaml
  # manifesto barrado pela revisão de segurança — permissivo demais
  apiVersion: networking.k8s.io/v1
  kind: NetworkPolicy
  metadata:
    name: sentinel-allow
    namespace: sentinel-prod
  spec:
    podSelector: {}          # aplica a todos os pods do namespace
    policyTypes:
      - Ingress
      - Egress
    ingress:
      - {}                   # libera QUALQUER origem
    egress:
      - {}                   # libera QUALQUER destino
  ```
- `{{regras_padrao}}` =
  ```
  NetworkPolicy para o namespace "sentinel-prod":
  - pods do Sentinel só aceitam tráfego de entrada do Relay (consumo de
    eventos) e do gateway de API da plataforma
  - pods do Sentinel só fazem saída para: Forge (warehouse, porta 5432),
    Cerebro (busca, porta 9200) e DNS interno
  - nada de "allow all" em ingress ou egress
  - política default-deny explícita no namespace
  - toda regra precisa de comentário dizendo qual fluxo legítimo ela libera
  ```
- `{{mapa_servicos}}` =
  ```
  Sentinel     → namespace sentinel-prod, pods com label app=sentinel
  Relay        → namespace relay-prod,    pods com label app=relay
  API gateway  → namespace edge,          pods com label app=api-gateway
  Forge        → namespace forge-prod,    pods com label app=forge,   porta 5432 (Postgres do warehouse)
  Cerebro      → namespace cerebro-prod,  pods com label app=cerebro, porta 9200 (Elasticsearch)
  DNS interno  → namespace kube-system,   pods com label k8s-app=kube-dns, porta 53
  ```

→ Capture a **v1** (manifesto + tabela fluxo→regra + lacunas).

**➋ Verificação (conversa NOVA, isolada — não traga o histórico da conversa A).**
Cole `prompt-verificacao.md`, preencha `{{manifesto_candidato}}` com a **v1** inteira
e `regras`/`mapa` com os mesmos blocos acima. → Capture os **achados** (perguntas +
tabela PASS/FAIL + veredito).

**➌ Refino (volte à conversa A).** Cole `prompt-refino.md`, preencha
`{{manifesto_anterior}}` com a v1, `{{achados_verificacao}}` com a saída do passo ➋,
e `regras`/`mapa`. → Capture a **v2** + changelog. Se a v2 ainda tiver FAIL, repita
➋–➌ (teto: 3 rodadas).

### ➊ v1 — geração (output real, verbatim)

```
1. Diagnóstico

- podSelector: {} seleciona todos os pods do namespace, não só o Sentinel — escopo maior que o exigido pela spec.
- ingress: - {} é allow-all de entrada: qualquer origem, qualquer porta.
- egress: - {} é allow-all de saída: qualquer destino, qualquer porta.
- Não há default-deny explícito — a política atual é o oposto disso (allow-all mascarado de policy).
- Nenhum comentário por regra explicando o fluxo legítimo (e não haveria como, já que não há fluxo específico nenhum liberado).

2. Manifesto endurecido

# Documento 1: default-deny explícito para todo o namespace sentinel-prod.
# Cobre qualquer pod que não esteja coberto por uma policy mais específica —
# sem isso, pods fora do escopo do Sentinel ficariam sem nenhuma NetworkPolicy aplicada.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: sentinel-prod
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  # sem regras de ingress/egress => bloqueio total por padrão
---
# Documento 2: policy específica do Sentinel — libera apenas os fluxos legítimos
# declarados na spec, usando exatamente os labels/portas do mapa de serviços.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-allow
  namespace: sentinel-prod
spec:
  podSelector:
    matchLabels:
      app: sentinel
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # ingress: Relay (relay-prod, app=relay) → consumo de eventos do Sentinel
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: relay-prod
          podSelector:
            matchLabels:
              app: relay
    # ingress: API gateway (edge, app=api-gateway) → chamadas da plataforma ao Sentinel
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: edge
          podSelector:
            matchLabels:
              app: api-gateway
  egress:
    # egress: Sentinel → Forge (forge-prod, app=forge:5432) — escrita/leitura no warehouse
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: forge-prod
          podSelector:
            matchLabels:
              app: forge
      ports:
        - protocol: TCP
          port: 5432
    # egress: Sentinel → Cerebro (cerebro-prod, app=cerebro:9200) — consultas de busca
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: cerebro-prod
          podSelector:
            matchLabels:
              app: cerebro
      ports:
        - protocol: TCP
          port: 9200
    # egress: Sentinel → DNS interno (kube-system, k8s-app=kube-dns:53) — resolução de nomes,
    # obrigatória porque o default-deny de egress quebraria qualquer lookup DNS
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53

3. Mapa fluxo → regra

┌────────────────────────┬─────────┬──────────────────────────────────┬────────────────────────────────────┐
│     fluxo legítimo     │ direção │             seletor              │               porta                │
├────────────────────────┼─────────┼──────────────────────────────────┼────────────────────────────────────┤
│ Relay → Sentinel       │ ingress │ ns=relay-prod, app=relay         │ (sem porta declarada no mapa/spec) │
├────────────────────────┼─────────┼──────────────────────────────────┼────────────────────────────────────┤
│ API gateway → Sentinel │ ingress │ ns=edge, app=api-gateway         │ (sem porta declarada no mapa/spec) │
├────────────────────────┼─────────┼──────────────────────────────────┼────────────────────────────────────┤
│ Sentinel → Forge       │ egress  │ ns=forge-prod, app=forge         │ 5432/TCP                           │
├────────────────────────┼─────────┼──────────────────────────────────┼────────────────────────────────────┤
│ Sentinel → Cerebro     │ egress  │ ns=cerebro-prod, app=cerebro     │ 9200/TCP                           │
├────────────────────────┼─────────┼──────────────────────────────────┼────────────────────────────────────┤
│ Sentinel → DNS interno │ egress  │ ns=kube-system, k8s-app=kube-dns │ 53/UDP e 53/TCP                    │
└────────────────────────┴─────────┴──────────────────────────────────┴────────────────────────────────────┘

4. Lacunas

- ⚠ O mapa não especifica a porta de escuta do Sentinel para os fluxos de ingress (Relay e API gateway). As regras de ingress acima liberam a origem por label/namespace mas sem restrição de porta, o que é mais permissivo do que o ideal — se houver uma porta real (ex.: porta HTTP do Sentinel), ela deveria ser adicionada em ports para fechar o escopo.
- ⚠ O mapa declara "porta 53" para DNS sem especificar protocolo. Assumi TCP+UDP por ser a convenção padrão de DNS (uma consulta pode usar qualquer um dos dois), não uma invenção de porta/serviço novo — mas fica registrado como suposição, não como dado explícito do mapa.
```

### ➋ Verificação — auditoria isolada (output real, verbatim)

```
Perguntas de verificação (Etapa A)

1. Existe uma NetworkPolicy de default-deny explícito cobrindo Ingress e Egress no namespace sentinel-prod?
2. Existe algum allow-all residual (- {} em ingress/egress, ou podSelector: {} associado a uma regra aberta) em qualquer documento?
3. O ingress da policy do Sentinel libera apenas Relay e API gateway — nenhuma origem extra?
4. Cada elemento de from/to combina namespaceSelector e podSelector no mesmo item de lista (semântica AND), e não como itens separados (o que criaria um OR mais permissivo)?
5. O egress libera apenas Forge (5432), Cerebro (9200) e DNS interno (53) — nenhum destino/porta extra, e nada aberto para a internet (ipBlock 0.0.0.0/0 ou equivalente)?
6. Cada seletor usa namespace, label e porta exatamente conforme o mapa de serviços (sem label inventado, sem porta trocada)?
7. A resolução DNS foi tratada como exceção ao default-deny de egress (UDP/TCP 53 para kube-dns)?
8. Toda regra de ingress/egress tem comentário explicando o fluxo legítimo que ela libera?
9. policyTypes inclui Ingress e Egress corretamente em ambos os documentos, e o podSelector de cada policy mira o alvo certo ({} para o deny-all, app: sentinel para o allow)?
10. As regras de ingress restringem porta de destino, ou a ausência de restrição de porta é coberta (não contradita) pela spec?

Resultado da auditoria (Etapa B)

#: 1
Pergunta: Default-deny explícito Ingress+Egress
PASS/FAIL: PASS
Evidência: Doc 1: podSelector: {} com policyTypes: [Ingress, Egress] e nenhuma chave ingress:/egress: preenchida
Correção exigida: —
────────────────────────────────────────
#: 2
Pergunta: Sem allow-all residual
PASS/FAIL: PASS
Evidência: Nenhuma ocorrência de - {} em from/to; podSelector: {} só aparece no doc de deny-all, sem regras associadas
Correção exigida: —
────────────────────────────────────────
#: 3
Pergunta: Ingress restrito a Relay + API gateway
PASS/FAIL: PASS
Evidência: Doc 2 ingress: tem só dois blocos from: relay-prod/app=relay e edge/app=api-gateway
Correção exigida: —
────────────────────────────────────────
#: 4
Pergunta: namespaceSelector+podSelector no mesmo item (AND)
PASS/FAIL: PASS
Evidência: Em cada bloco from/to, namespaceSelector e podSelector estão sob o mesmo - (mesmo item de lista), ex.: bloco Relay
  em ingress[0].from[0]
Correção exigida: —
────────────────────────────────────────
#: 5
Pergunta: Egress restrito a Forge/Cerebro/DNS, sem internet
PASS/FAIL: PASS
Evidência: Doc 2 egress: tem só 3 blocos to: forge-prod/app=forge:5432, cerebro-prod/app=cerebro:9200,
  kube-system/k8s-app=kube-dns:53; nenhum ipBlock presente
Correção exigida: —
────────────────────────────────────────
#: 6
Pergunta: Seletores batem com o mapa (ns/label/porta)
PASS/FAIL: PASS
Evidência: relay-prod+app=relay; edge+app=api-gateway; forge-prod+app=forge+5432; cerebro-prod+app=cerebro+9200;
  kube-system+k8s-app=kube-dns+53 — todos idênticos ao <mapa_servicos>
Correção exigida: —
────────────────────────────────────────
#: 7
Pergunta: DNS tratado como exceção ao default-deny de egress
PASS/FAIL: PASS
Evidência: Bloco final do egress: to: kube-system/k8s-app=kube-dns, ports: UDP/53, TCP/53, com comentário explicando a
  necessidade
Correção exigida: —
────────────────────────────────────────
#: 8
Pergunta: Toda regra tem comentário do fluxo legítimo
PASS/FAIL: PASS
Evidência: Cada bloco de ingress/egress tem comentário imediatamente acima (# ingress: Relay..., # ingress: API gateway..., #
  egress: Sentinel → Forge..., # egress: Sentinel → Cerebro..., # egress: Sentinel → DNS interno...); doc 1 também comentado
Correção exigida: —
────────────────────────────────────────
#: 9
Pergunta: policyTypes e podSelector corretos
PASS/FAIL: PASS
Evidência: Doc 1: podSelector: {} (alvo = todo o namespace, correto para deny-all); Doc 2: podSelector: matchLabels: app:
  sentinel (alvo = só o Sentinel); ambos com policyTypes: [Ingress, Egress]
Correção exigida: —
────────────────────────────────────────
#: 10
Pergunta: Ingress sem restrição de porta é coberto pela spec
PASS/FAIL: PASS (com ressalva)
Evidência: <regras_padrao> define a restrição de ingress só por origem ("só aceitam tráfego de entrada do Relay... e do
  gateway"), sem exigir porta; <mapa_servicos> não declara porta de escuta do Sentinel — não há norma violada, mas também não
  há como comprovar que a porta de destino está minimizada
Correção exigida: Documentar/declarar a porta de escuta do Sentinel no mapa de serviços e adicionar ports: nos blocos de
  ingress, para eliminar a superfície de qualquer porta aberta às origens autorizadas

Veredito

APROVADO para aplicar — nenhum FAIL. O único ponto residual (item 10) é uma lacuna de especificação, não uma violação do padrão vigente: nem <regras_padrao> nem <mapa_servicos> definem a porta de escuta do Sentinel, então não há base para reprovar a ausência de ports: nas regras de ingress. Fica registrado como recomendação de hardening para uma futura iteração do padrão, não como achado de reprovação.
```

### ➌ Refino — aplicar achados (output real, verbatim)

```
A auditoria não registrou nenhum FAIL — veredito é APROVADO. O único ponto (item 10) é explicitamente classificado como "recomendação de hardening", não como achado de reprovação, e depende de um dado que não existe no mapa (porta de escuta do Sentinel). Não há base para alterar o manifesto sem inventar informação fora do mapa de serviços.

Sem alterações necessárias. O manifesto da versão anterior permanece válido e é o que deve ser aplicado.

Changelog achado → correção

┌────────────────┬────────────────┬───────────────────────────────────────────────────────────────────────────────────────┐
│   achado da    │    mudança     │                                      trecho novo                                      │
│   auditoria    │    aplicada    │                                                                                       │
├────────────────┼────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤
│ #1–#9 (todos   │ nenhuma — já   │ —                                                                                     │
│ PASS)          │ corretos       │                                                                                       │
├────────────────┼────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤
│ #10 (PASS com  │ nenhuma        │ ⚠ pendente: porta de escuta do Sentinel não consta em <mapa_servicos>; adicionar      │
│ ressalva)      │ mudança        │ ports: nos blocos de ingress exigiria inventar um dado fora do mapa, o que viola a    │
│                │ aplicada       │ regra "labels e portas vêm do mapa"                                                   │
└────────────────┴────────────────┴───────────────────────────────────────────────────────────────────────────────────────┘

Achados não endereçados

- ⚠ pendente: item 10 — recomendação de hardening (restringir porta de destino nas regras de ingress) requer que o mapa de serviços declare a porta em que os pods app=sentinel escutam. Sem esse dado, adicionar ports: seria adivinhação, proibida pelas regras da tarefa. Fica registrado para uma futura atualização do mapa/spec, não bloqueia a aplicação do manifesto atual.
```

## 4. Curadoria

**O que blindei na saída do meta-prompt.**
- **Zero allow-all** como invariante dura em geração *e* verificação: nenhuma regra
  `- {}` nem `podSelector: {}` acompanhado de regra aberta sobrevive.
- **Labels e portas só do mapa** — a regra anti-alucinação mais importante aqui:
  o modelo não pode inventar `app=…`, namespace ou porta; se faltar no mapa, marca
  `⚠ label ausente` em vez de chutar um seletor que abriria a rede errada.
- **Comentário por regra** exigido pelo padrão — é FAIL de auditoria mesmo quando a
  rede fica funcionalmente correta.
- **DNS explícito** como passo próprio: egress default-deny quebra resolução de nome,
  e esquecer a porta 53 é o erro silencioso mais comum — por isso virou passo no
  RISE e pergunta obrigatória na verificação.
- **Isolamento da verificação** (factor-revise): a auditoria roda em conversa nova,
  sem a justificativa de quem gerou — é o que impede o modelo de carimbar o próprio
  trabalho. Registrei isso como instrução operacional no README do item.

**Golden answer (referência de conformidade, para avaliar a execução real).** A v2
aprovada deve convergir para dois recursos — um **default-deny de namespace** e a
**política do Sentinel** com apenas os fluxos legítimos:

```yaml
# default-deny do namespace — nega todo ingress/egress não liberado explicitamente
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: sentinel-prod
spec:
  podSelector: {}            # todos os pods do namespace...
  policyTypes:
    - Ingress
    - Egress
  # ...sem regras ingress/egress: tudo negado por padrão
---
# política do Sentinel — libera apenas os fluxos legítimos
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-allow
  namespace: sentinel-prod
spec:
  podSelector:
    matchLabels:
      app: sentinel          # aplica só aos pods do Sentinel
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # ingress: Relay → consumo de eventos pelo Sentinel
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: relay-prod
          podSelector:
            matchLabels:
              app: relay
    # ingress: API gateway → tráfego da borda da plataforma
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: edge
          podSelector:
            matchLabels:
              app: api-gateway
  egress:
    # egress: Sentinel → Forge (Postgres do warehouse) porta 5432
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: forge-prod
          podSelector:
            matchLabels:
              app: forge
      ports:
        - protocol: TCP
          port: 5432
    # egress: Sentinel → Cerebro (Elasticsearch) porta 9200
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: cerebro-prod
          podSelector:
            matchLabels:
              app: cerebro
      ports:
        - protocol: TCP
          port: 9200
    # egress: Sentinel → DNS interno (kube-dns) porta 53
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

**Onde a verificação costuma pegar a v1** (o que a auditoria isolada existe para
achar — a confirmar contra o output real): (a) **DNS esquecido** no egress; (b)
**default-deny só implícito** (sem o recurso `default-deny-all` de namespace pedido
pela spec); (c) `namespaceSelector` **por nome** em vez de por label — o
`namespaceSelector` casa **labels de namespace**, então é preciso o rótulo
`kubernetes.io/metadata.name: <ns>` (automático em K8s ≥1.21) ou um label próprio; se
o modelo assumir que "namespace: relay-prod" vira seletor direto, a regra não casa —
um bom output marca isso como `⚠ label de namespace`; (d) **DNS só UDP**, deixando
cair TCP/53 (usado em respostas grandes/consultas TCP).

**Resultado da execução real (o que o teste confirmou).** O ciclo **convergiu em uma
rodada**: a v1 já saiu com os dois recursos (`default-deny-all` de namespace +
`sentinel-allow`), DNS em UDP **e** TCP/53, `namespaceSelector` por label
`kubernetes.io/metadata.name`, semântica AND (namespaceSelector+podSelector no mesmo
item de lista) e comentário por regra — batendo com a golden answer. A verificação
isolada rodou as 10 perguntas e deu **PASS em todas**, veredito `APROVADO`; o refino,
coerente com a regra do prompt ("se veio APROVADO, não invente mudança cosmética"),
declarou **"sem alterações necessárias"** e parou o laço.

**Divergência vs. previsão — e por que é um bom sinal.** Eu previa que a auditoria
pegaria DNS esquecido ou default-deny só implícito na v1; o modelo já acertou esses
pontos de saída. Isso **não** enfraquece o ciclo: (a) o modelo **verbalizou as duas
lacunas reais** (porta de escuta do Sentinel ausente no mapa; protocolo do DNS não
declarado) em vez de as esconder — exatamente o comportamento anti-alucinação que o
prompt exige; (b) a verificação **acrescentou** uma pergunta que eu não tinha
enumerado — a **semântica AND vs. OR** do par `namespaceSelector`/`podSelector`
(itens separados na lista viram OR e abrem a política), que é a pegadinha clássica de
NetworkPolicy — e a comprovou com o trecho do YAML; (c) o item 10 (ingress sem
restrição de porta) foi corretamente classificado como **lacuna de spec, não FAIL** —
o revisor não reprovou por um dado que o mapa não fornece nem inventou a porta, e o
refino se recusou a "adivinhar" ports. Um ciclo que aprova de primeira **com
evidência por item e sem forçar mudança cosmética** é o resultado desejado; o valor
do CoVe aqui é ter **comprovado** a conformidade da v1, não ter necessariamente
gerado uma v2. Se o padrão evoluir (declarar a porta de escuta do Sentinel), a mesma
cadeia reabre e a próxima rodada fecha o item 10 — o gancho já está registrado.

**Critério de aceite / ganchos de avaliação (3 perguntas).**
1. **Correção** — a v2 tem default-deny explícito nas duas direções e **nenhum**
   allow-all, e o egress libera **exatamente** Forge:5432, Cerebro:9200 e DNS:53
   (nada além)?
2. **Fidelidade ao mapa** — todo seletor usa label/namespace/porta do mapa, sem
   inventar rótulo?
3. **Processo** — as iterações estão registradas (v1 → achados com PASS/FAIL e
   evidência → v2 com changelog achado→correção), com o veredito final `APROVADO`?
