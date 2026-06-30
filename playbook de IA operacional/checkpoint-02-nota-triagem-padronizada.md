# Checkpoint 02 — Padronizando as notas de triagem

> Playbook de IA Operacional da Aegis — item nº 2 (domínio SRE).
> Um padrão único de nota de triagem, para que o plantão do turno seguinte leia tudo
> no mesmo formato. Pedido da Carol Danvers (Head of Product).

---

## 1. Decisões de método (o "porquê" antes do "o quê")

### A decisão central do checkpoint: como ensinar o padrão ao modelo

O enunciado deixa o método em aberto — "dá pra ensinar esse padrão de mais de uma
forma, e é essa escolha que você vai justificar". Há dois caminhos:

1. **Zero-shot / descrição em prosa** — descrever os cinco campos e as regras de
   formato por extenso e pedir para o modelo seguir.
2. **Few-shot / por exemplo** — mostrar as notas-modelo prontas e deixar o modelo
   inferir o padrão (*in-context learning*).

**Escolhi few-shot.** O padrão "bom" já está cristalizado em três notas-modelo que o
time consolidou — é desperdício re-descrevê-lo em prosa, e prosa deixa tom e formato à
interpretação do modelo, reproduzindo exatamente a dor que queremos matar (cada
execução/plantonista sai um pouco diferente). O few-shot mostra esse efeito no caso
gêmeo deste — **padronizar mensagem de commit**: sem nenhuma regra escrita, só com
exemplos, "o próprio modelo já entende isso analisando os exemplos"
(`tec-few-shot`). É *in-context learning*: os exemplos mudam o peso dos tokens e a saída
sai no formato exato, de forma repetível.

Cuidados que o few-shot impõe e que apliquei: **3 a 5 exemplos** (tenho 3), **qualidade e
nuance** em vez de repetição (um exemplo por sistema — Relay, Forge, Cerebro — cobrindo
causas diferentes) e **o melhor exemplo por último** (maior peso no fim do prompt).

### Framework: RTF como base + Example (CARE) como técnica

A tarefa é uma **transformação direta** — alerta cru entra, nota com **saída
previsível** (cinco rótulos fixos) sai. Esse é o caso de uso clássico do **R-T-F**
(Role · Task · Format): tarefa direta, formato previsível. Não há raciocínio
multi-etapa que justifique RISE/CoT, nem mudança de estado para BAB, nem um KPI de
negócio no centro para TAG.

| Componente | No nosso prompt |
|---|---|
| **Role** | Plantonista SRE abrindo a nota logo após o disparo |
| **Task** | Converter o `{{alerta}}` cru na nota padronizada |
| **Format** | O gabarito dos 5 campos + os 3 exemplos few-shot que o fixam |

Sobre o RTF aplico a **regra de combinação** (base simples + 1 elemento justificado):
o **Example do C-A-R-E**. O CARE existe justamente porque o RTF, descrevendo o formato
só em prosa, "entrega algo razoável, mas sem referência de qualidade, e o resultado
pode vir num formato diferente do esperado" (`fw-care`) — o diferencial do CARE é o
exemplo concreto do resultado pronto. Uso esse elemento (não o CARE inteiro: o
`Context` aqui é mínimo) como ponte natural para o few-shot.

**Por que não RISE+Example (como no Checkpoint 01)?** No 01 a tarefa era diagnóstica e
procedural (cruzar status × eventos × logs em passos) — pedia os `Steps` e o
`Expectation` do RISE. Aqui não há diagnóstico multi-etapa: o alerta já vem com a
pista, e o trabalho é **reformatar com consistência**. Forçar RISE seria peso morto;
a regra de ouro manda começar pelo framework mais simples que resolve.

### Parametrização (regra de método #1 do desafio)

Dado variável entra por **um parâmetro principal `{{alerta}}`** (colado na entrada —
sem agente, sem tool), mais um opcional **`{{contexto_extra}}`** (deploys conhecidos,
SLA, janela) que torna o item reusável para qualquer alerta dos quatro sistemas.

### Meta-prompting / CRAFT (regra de método #2)

Construído via **CRAFT** (humano no controle): dirigi um modelo forte com um meta-prompt
descrevendo a dor (notas heterogêneas atrapalham a passagem de turno), as três
notas-modelo e a separação explícita entre **formato de saída** (as notas prontas) e
**entradas** (os alertas crus) — o enunciado avisa para não misturar as duas listas. O
modelo gerou o rascunho; **a curadoria é minha** (ver §4). O meta-prompt não entra na
biblioteca — só o prompt final. **Criar com o modelo caro (Opus 4.8), executar com o
barato.**

### Versionamento/organização

Mesmo padrão de catálogo do item nº 1: **Markdown + front-matter**, organizado **por
domínio (`sre/`), não por técnica**, pasta por prompt com `prompt.md` + `README.md`.

---

## 2. Entregável — o prompt parametrizável

Caminho no repositório: `sre/nota-triagem-padronizada/prompt.md`

```markdown
---
nome: Nota de triagem padronizada (alertas)
dominio: sre
objetivo: Converter um alerta cru de qualquer sistema da Aegis (Relay, Forge,
  Sentinel, Cerebro) em uma nota de triagem no padrão único de plantão, com os
  cinco campos fixos, para que quem assume o turno seguinte leia tudo no mesmo formato.
quando_usar: O Sentinel dispara um alerta e o plantonista precisa abrir a nota de
  triagem padronizada, em vez de escrever cada um do seu jeito.
inputs:
  alerta: O alerta cru colado (linha de log / payload do disparo), com sistema,
    métrica, janela, tenant e qualquer pista de causa.
  contexto_extra: (opcional) observações do plantão, SLA, janela de manutenção,
    deploys recentes conhecidos.
modelo_recomendado: claude-sonnet-4-6 (execução); criado com claude-opus-4-8
versao: 1.0.0
framework: RTF (Role-Task-Format) + few-shot (Example do CARE)
tags: [sre, oncall, triagem, alertas, padronizacao, few-shot]
---

# Papel

Você é o plantonista SRE da Aegis abrindo a nota de triagem logo após um alerta
disparar. Você escreve rápido, mas no padrão único do time — porque quem assume o
próximo turno vai ler a sua nota e precisa entender o incidente em segundos.

# Tarefa

Transforme **um alerta cru** em **uma nota de triagem padronizada**. A nota tem
exatamente **cinco campos fixos, nesta ordem**, um por linha, com os rótulos em
maiúsculas:

ALERTA: <sistema> - <condição em uma frase>
IMPACTO: <quem/o quê é afetado e o quanto>
HIPÓTESE INICIAL: <causa provável, ancorada em um sinal do alerta>
AÇÃO IMEDIATA: <a primeira medida do plantão, concreta>
ESCALAR PARA: @<time-dono> se <condição/prazo>

# Entrada

O alerta abaixo foi colado pelo plantão. Trabalhe **somente** com o que está nele —
não invente métricas, tenants, horários ou deploys que não aparecem.

Contexto adicional: {{contexto_extra}}

<alerta>
{{alerta}}
</alerta>

# Regras

- **Cada campo ancorado no alerta.** Toda HIPÓTESE INICIAL precisa apontar para um
  sinal presente no alerta (deploy, pico de tenant, falha de job, saturação…). Se o
  alerta não der pista de causa, escreva `HIPÓTESE INICIAL: indeterminada — investigar
  <X>` em vez de chutar.
- **IMPACTO é consequência, não repetição da métrica.** Diga quem sente
  (tenants, dashboards, plantão), não só "métrica acima do limite".
- **ESCALAR PARA usa o time dono do sistema**: Relay → `@relay-core`; Forge →
  `@data-platform`; Cerebro → `@search-infra`; Sentinel → `@sentinel-core`. Se o dono
  não for claro, use `@oncall-lead`. Sempre acompanhe de uma condição/prazo de
  escalonamento.
- **AÇÃO IMEDIATA** é a primeira medida segura do plantão (rollback, escalar
  partição, pausar job…), não um plano de projeto.
- Português, conciso. **Saída só a nota** — sem preâmbulo, sem comentário extra.

# Exemplos do padrão (siga este formato e profundidade)

ALERTA: Relay - taxa de rejeição de ingestão acima de 2% por 5min
IMPACTO: ingestão de telemetry degradada para ~12% dos tenants
HIPÓTESE INICIAL: deploy do Relay às 09:14 reduziu o buffer de ingestão
AÇÃO IMEDIATA: rollback iniciado via Argo CD
ESCALAR PARA: @relay-core se a rejeição não cair em 10min

ALERTA: Forge - lag de ingestão acima de 15min
IMPACTO: dashboards do Sentinel atrasados para todos os tenants
HIPÓTESE INICIAL: pico de volume do tenant acme-corp saturou o consumer
AÇÃO IMEDIATA: aumento manual de partições do consumer do Relay
ESCALAR PARA: @data-platform se lag não estabilizar em 20min

ALERTA: Cerebro - latência de busca p99 acima de 4s
IMPACTO: investigação de incidentes lenta para o time interno
HIPÓTESE INICIAL: reindexação noturna não concluiu antes do horário comercial
AÇÃO IMEDIATA: pausar reindexação e priorizar shard quente
ESCALAR PARA: @search-infra se p99 não cair em 15min

# Agora gere a nota

Produza **apenas** a nota de triagem padronizada (os cinco campos) para o alerta da
seção `# Entrada`.
```

---

## 3. Execução

**Modelo de execução:** `claude-sonnet-4-6` (seguindo "criar caro, executar barato").
Execução **manual verificada** (prompt colado em chat, uma conversa nova por entrada).
Saída **real** do modelo para cada um dos **três alertas crus** (as *entradas* do
enunciado — não as notas-modelo).

### Entrada 1 — Sentinel, autoscaler no teto

Alerta: `autoscaler hit max replicas (60/60) on sentinel-api, queue depth on Relay
growing 2k/min, CPU avg 88%, tenant stark-industries sending 4x baseline volume after
onboarding new region`

```
ALERTA: Sentinel - autoscaler atingiu o teto de réplicas (60/60) no sentinel-api
IMPACTO: tenants do sentinel-api sob risco de degradação/fila crescente, com Relay acumulando backlog a 2k/min
HIPÓTESE INICIAL: tenant stark-industries enviando 4x o volume baseline após onboarding de nova região saturou a capacidade
AÇÃO IMEDIATA: aplicar rate limit no tenant stark-industries para conter o pico
ESCALAR PARA: @sentinel-core se a fila do Relay não estabilizar em 10min
```

### Entrada 2 — Relay, rejeição de ingestão pós-deploy

Alerta: `ingest reject rate 6% for 8min, tenant wakanda-systems, buffer saturated after
deploy 02:55`

```
ALERTA: Relay - taxa de rejeição de ingestão em 6% por 8min
IMPACTO: ingestão de telemetry do tenant wakanda-systems sendo descartada parcialmente
HIPÓTESE INICIAL: deploy das 02:55 saturou o buffer de ingestão
AÇÃO IMEDIATA: rollback do deploy das 02:55 via Argo CD
ESCALAR PARA: @relay-core se a rejeição não cair em 10min
```

### Entrada 3 — Forge, lag do consumer por falha de job

Alerta: `consumer lag 9min and climbing, batch forge-batch-ingest delayed after previous
job failure, downstream Sentinel starting to lag`

```
ALERTA: Forge - consumer lag em 9min e subindo
IMPACTO: dashboards do Sentinel começando a atrasar para os tenants
HIPÓTESE INICIAL: falha do job anterior atrasou o batch forge-batch-ingest
AÇÃO IMEDIATA: reprocessar/reiniciar o batch forge-batch-ingest após a falha
ESCALAR PARA: @data-platform se o lag não estabilizar em 20min
```

---

## 4. Curadoria (a "assinatura" no item)

- **Separei as duas listas, como o enunciado exige.** As três notas-modelo entram no
  prompt **só como exemplos de formato** (seção `# Exemplos do padrão`); os três alertas
  crus são as **entradas de execução**. O rascunho do meta-prompt tendia a tratar tudo
  como entrada — corrigi para que as notas-modelo nunca virassem dado a processar.
- **Generalização além dos exemplos (edge case real).** Os três modelos cobrem Relay,
  Forge e Cerebro — mas **nenhum cobre o Sentinel**, que é justamente a Entrada 1. Por
  isso fixei no prompt o **mapa sistema→time** (incluindo `@sentinel-core`) e o fallback
  `@oncall-lead`: sem isso, o modelo inventaria um handle para o Sentinel. É a diferença
  entre o few-shot copiar os exemplos e o few-shot **entender o padrão**.
- **Anti-alucinação ancorada no sinal.** Toda `HIPÓTESE INICIAL` aponta para algo que
  está no alerta (deploy 02:55, tenant 4x, falha do job anterior). Onde o alerta não dá
  pista, a regra força `indeterminada — investigar X` em vez de chute — mesma filosofia
  do item nº 1.
- **IMPACTO ≠ métrica repetida.** Reforcei que o impacto é a **consequência** (fila do
  Relay, dashboards atrasando, tenant afetado), não o restatement do número que disparou
  o alerta — é o que torna a nota útil para quem assume o turno.
- **Saída limpa.** "Apenas a nota, sem preâmbulo" — a nota é um artefato operacional
  colado no canal de plantão; comentário do modelo seria ruído.
- **Ganchos para os próximos checkpoints (avaliação):** item pronto para **rubrica**
  (5 campos presentes e na ordem? hipótese ancorada em sinal? time de escalonamento
  correto? impacto é consequência?) e **golden-answer** no promptfoo, comparando a saída
  contra as notas-modelo.

### Verificação da execução real (não foi simulação)

As saídas da §3 são a **execução manual verificada** no `claude-sonnet-4-6` (uma conversa
nova por entrada). O que o teste real confirmou:

- **Generalização passou no edge case.** Na Entrada 1 (Sentinel), sistema **ausente**
  dos exemplos few-shot, o modelo escolheu `@sentinel-core` corretamente a partir do
  mapa sistema→time — não copiou um handle dos exemplos nem inventou. Era o risco
  principal do few-shot e o prompt o cobriu.
- **Formato 100% aderente.** As três saídas vieram com os cinco campos, na ordem, sem
  preâmbulo — a regra "apenas a nota" segurou.
- **Anti-alucinação confirmada.** Nenhuma hipótese trouxe métrica/tenant que não estava
  no alerta; todas apontaram o sinal real (pico 4x, deploy 02:55, falha do job anterior).
- **Única divergência vs. minha previsão (esperada e benigna):** na Entrada 1 eu havia
  previsto AÇÃO IMEDIATA dupla (elevar `maxReplicas` **e** rate limit); o modelo optou
  pela medida única mais conservadora (rate limit no tenant que causou o pico). É uma
  escolha de plantão defensável — não exige mudança no prompt.
