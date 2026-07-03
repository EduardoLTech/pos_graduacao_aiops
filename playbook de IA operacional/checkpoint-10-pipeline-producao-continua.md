# Checkpoint 10 — O playbook em produção contínua

> Playbook de IA Operacional da Aegis — Avaliação / CI. O que separa um repositório de
> prompts de um sistema confiável é a garantia de que **nenhuma alteração entra sem passar
> pelos testes**. Aqui a biblioteca fecha o ciclo: cobertura de avaliação em **todos** os
> itens e um pipeline em GitHub Actions que roda a suíte a cada mudança e **barra a
> regressão** antes do merge.

---

## 1. Decisões de método

O CP08 deu rede determinística a três itens de saída estruturada; o CP09 deu um gate de
julgamento à causa-raiz. Faltavam **dois** itens de saída aberta sem teste — a decisão de
backpressure (`arquitetura/decisao-arquitetural-tradeoff`) e a cadeia de migração
(`data/migracao-incremental-encadeada`) — e faltava a automação que roda tudo isso sozinha.
Este checkpoint entrega as duas coisas.

### 1.1 Cobertura: fechar a pirâmide em todos os itens

Regra aplicada: **determinístico onde a saída tem forma verificável; juiz onde a saída é
aberta.** O resultado é 6 itens, 6 configs:

| Item | Domínio | Saída | Config | Camada |
|---|---|---|---|---|
| Nota de triagem padronizada | sre | estruturada | `sre/nota-triagem-padronizada/promptfooconfig.yaml` | determinística (CP08) |
| Triagem de pods | sre | estruturada | `sre/triagem-pods-kubernetes/promptfooconfig.yaml` | determinística (CP08) |
| Endurecer NetworkPolicy | seguranca | estruturada (YAML) | `seguranca/endurecer-networkpolicy/promptfooconfig.yaml` | determinística (CP08) |
| Análise de causa-raiz | sre | aberta | `sre/analise-causa-raiz/promptfooconfig.yaml` | **juiz** (CP09) |
| **Decisão com trade-offs (backpressure)** | arquitetura | aberta | `arquitetura/decisao-arquitetural-tradeoff/promptfooconfig.yaml` | **juiz (novo — CP10)** |
| **Migração faseada (cadeia, Elo 2)** | data | aberta | `data/migracao-incremental-encadeada/promptfooconfig.yaml` | **juiz (novo — CP10)** |

Os dois novos gates reusam a mecânica do CP09 sem inventar nada: **gerar com uma família,
julgar com outra** (`openrouter:openai/gpt-4o-mini` gera, `google:gemini-2.5-flash` julga —
anti self-preference), juiz a `temperature: 0`, rubrica de 4 critérios (0–2), corte ≥ 6 e
nenhum critério zerado, com o raciocínio do juiz **antes** do veredito no JSON. As rubricas
mudam com o **tipo** de tarefa:

- **Backpressure** — C1 múltiplos caminhos desenvolvidos (o método explorou ≥3 antes de
  decidir), C2 restrições inegociáveis respeitadas (o modo de falha mais grave: recomendar
  algo que **perde telemetry** ou **estoura o SLA de 60s** do alerting → C2=0), C3 trade-off
  honesto (preço de cada caminho, ancorado nos números), C4 recomendação com o porquê dela
  **e** o porquê das descartadas.
- **Migração (Elo 2)** — C1 faseamento incremental sem big-bang, C2 reversibilidade + gate
  por fase, C3 dependentes preservados na transição (Sentinel/Cerebro/billing não quebram),
  C4 ancoragem no diagnóstico (não inventa componentes). Testo o **Elo 2** porque é nele que
  moram os três atributos que a migração precisa garantir; ele roda **isolado**, recebendo
  um diagnóstico fixo (fixture do Elo 1) em `{{diagnostico}}`, para o gate não depender de
  encadear a cadeia inteira a cada alteração.

### 1.2 O gate: a regra que decide pass/fail

A ferramenta está dada (GitHub Actions); o desenho é a decisão. Cinco escolhas, cada uma
comparada com as alternativas na §4. Em resumo:

| Decisão | Escolha | Alternativa preterida |
|---|---|---|
| **Como rodar** | CLI em laço sobre os 6 configs | action oficial (1 config, 1 chave) |
| **O que barra o build** | qualquer assert falho (determinístico **e** juiz) | só determinístico; juiz consultivo |
| **Escopo por execução** | suíte inteira + cache | só os prompts alterados |
| **Latência/custo no gate** | medidos; barram apenas em endpoint estável de CI | latência como hard gate cru (rui­doso) |
| **Custo por PR / chaves** | cache + modelos baratos + concurrency; chaves em repo secrets | `--no-cache` em CI; chave no YAML (proibido) |

O gate é `promptfoo eval` por config; o **exit code** faz o trabalho — o `promptfoo` sai
com código ≠ 0 quando um assert reprova, o laço captura isso e o job termina em falha,
barrando o merge. Regressão = uma mudança que faz um assert que passava reprovar.

---

## 2. Entregável

### 2.1 O workflow — `.github/workflows/promptfoo.yml` (na raiz do repositório git)

O playbook é uma subpasta do repo `pos_graduacao_aiops` (ao lado de `apps/` e
`prompt_engineering/`); por isso o workflow mora na **raiz do git** e é escopado por `paths`
para a pasta do playbook — mudança em `apps/` não dispara a suíte de prompts. Núcleo:

```yaml
on:
  pull_request:
    paths: ["playbook de IA operacional/**", ".github/workflows/promptfoo.yml"]
  push:
    branches: [main]
    paths: ["playbook de IA operacional/**", ".github/workflows/promptfoo.yml"]

permissions:            # menor privilégio
  contents: read
  pull-requests: write

concurrency:            # só a última revisão do PR roda
  group: promptfoo-${{ github.ref }}
  cancel-in-progress: true

jobs:
  eval:
    env:
      GOOGLE_API_KEY:     ${{ secrets.GOOGLE_API_KEY }}
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4  { node-version: "22" }
      - uses: actions/cache@v4       # cache chaveado pelo conteúdo dos prompts+configs
      - run: npm install -g promptfoo@0.121.17   # versão fixa = gate reprodutível
      - run: |                        # laço sobre os 6 configs; exit != 0 barra o merge
          find . -name 'promptfooconfig.yaml' | sort | while read cfg; do
            promptfoo eval -c "$cfg" || fail=1
          done; exit ${fail:-0}
```

O arquivo completo (com o resumo em `$GITHUB_STEP_SUMMARY`, os `::group::` de log e o
tratamento de exit code) está versionado em `.github/workflows/promptfoo.yml`. O `find`
pega **só** os `promptfooconfig.yaml` da suíte — **não** o `promptfooconfig.calibracao.yaml`
(o banco de calibração do juiz do CP09, que não é gate).

### 2.2 Os dois configs de juiz novos

`arquitetura/decisao-arquitetural-tradeoff/{promptfooconfig.yaml, rubrica-juiz.md}` e
`data/migracao-incremental-encadeada/{promptfooconfig.yaml, rubrica-juiz.md}`, versionados
nas pastas dos itens, no mesmo formato do gate de causa-raiz (CP09).

### 2.3 Onde vão os secrets

`Settings → Secrets and variables → Actions` do repositório, dois secrets:
`GOOGLE_API_KEY` e `OPENROUTER_API_KEY`. Nunca no YAML. A `${{ secrets.* }}` injeta como
variável de ambiente do job; sem elas, os itens de juiz falham — que é o comportamento
correto (um gate não deve passar sem poder medir).

---

## 3. Execução

### 3.1 Verificado localmente agora (real)

**Validação estática dos 6 configs da suíte** (`promptfoo validate`, não consome modelo) —
exatamente o conjunto que o `find` do pipeline seleciona:

```
$ cd "playbook de IA operacional" && find . -name 'promptfooconfig.yaml' | sort
./arquitetura/decisao-arquitetural-tradeoff/promptfooconfig.yaml   → Configuration is valid.
./data/migracao-incremental-encadeada/promptfooconfig.yaml         → Configuration is valid.
./seguranca/endurecer-networkpolicy/promptfooconfig.yaml           → Configuration is valid.
./sre/analise-causa-raiz/promptfooconfig.yaml                      → Configuration is valid.
./sre/nota-triagem-padronizada/promptfooconfig.yaml                → Configuration is valid.
./sre/triagem-pods-kubernetes/promptfooconfig.yaml                 → Configuration is valid.
```

O `promptfooconfig.calibracao.yaml` **não** aparece na lista — confirmando que o gate roda
a suíte e ignora o banco de calibração. O `.github/workflows/promptfoo.yml` foi parseado
com sucesso (js-yaml): 1 job `eval`, triggers `pull_request` + `push`, 5 steps.

As saídas reais de `promptfoo eval` dos itens já testados estão nos CP08 (determinísticos,
6/6 na nota, achados legítimos nos pods e na NetworkPolicy) e CP09 (juiz calibrado, Δ0
contra a nota humana). O pipeline apenas **automatiza** essas mesmas execuções.

### 3.2 Execução do pipeline em CI — execução verificada (GitHub Actions)

Rodado no GitHub Actions do repositório, no job `eval`, com os secrets `GOOGLE_API_KEY` e
`OPENROUTER_API_KEY` configurados. **Uma única execução** (`~6m 35s`) percorreu os 6 configs
na ordem do `find | sort`; **4 passaram e 2 reprovaram**, e o job terminou em `exit code 1`
— o gate barrando o merge. Placar real dessa execução:

| # | Config | eval ID | Resultado | Tokens | Duração |
|---|---|---|---|---|---|
| 1 | `arquitetura/decisao-arquitetural-tradeoff` (juiz **novo**) | `eval-n6T` | ✓ 1 passed (100%) | 8.088 (2.697 eval + 5.391 grading) | 23s |
| 2 | `data/migracao-incremental-encadeada` (juiz **novo**) | `eval-q58` | ✓ 1 passed (100%) | 7.934 (2.169 eval + 5.765 grading) | 24s |
| 3 | `seguranca/endurecer-networkpolicy` | `eval-ujx` | ✗ **2 failed (100%)** | 5.743 | **3m 57s** |
| 4 | `sre/analise-causa-raiz` (juiz) | `eval-WxV` | ✓ 1 passed (100%) | 12.277 (3.704 eval + 8.573 grading) | 26s |
| 5 | `sre/nota-triagem-padronizada` | `eval-oCl` | ✓ passou (sem linha `FAIL`) | — | 4s |
| 6 | `sre/triagem-pods-kubernetes` | `eval-nqA` | ✗ **1 failed (5/6, 83,33%)** | 11.660 | 5s |

**Os dois juízes NOVOS do CP10 nasceram verdes no pipeline** (a cobertura que este checkpoint
adicionou):

```
✓ Eval complete (ID: eval-n6T-2026-07-03T00:47:20)
Total Tokens: 8,088
  Eval: 2,697 (2,010 prompt, 687 completion)
  Grading: 5,391 (2,839 prompt, 611 completion)
Results:
  ✓ 1 passed (100%)      ← backpressure (decisao-arquitetural-tradeoff)
...
✓ Eval complete (ID: eval-q58-2026-07-03T00:47:44)
Total Tokens: 7,934
  Eval: 2,169 (1,524 prompt, 645 completion)
  Grading: 5,765 (2,792 prompt, 575 completion)
Results:
  ✓ 1 passed (100%)      ← migração (Elo 2)
```

O veredito real dos juízes bate com a rubrica: o backpressure recomendou "a **combinação
faseada** de priorizar o Sentinel e implementar uma **dead-letter queue** para garantir a
entrega de mensagens sem violar as restrições rígidas" (C2 = respeitou o SLA de 60s e o
zero-perda), e a migração produziu "Fase 1 — Troca de Ingestão" partindo do `forge-batch-
ingest` do diagnóstico (C1/C4). O `analise-causa-raiz` (juiz do CP09) também passou no CI,
cravando "a causa-raiz da degradação foi a saturação da heap da JVM" — 12.277 tokens, 26s.

**As duas reprovações são exatamente os modos de falha que o CP08 já documentava** — e é
importante que sejam, porque provam que o gate pega em CI o que o teste manual pegava:

1. **`networkpolicy` — reprovou por `latency`, não por conteúdo.** A geração travou no
   free-tier (o backoff do provedor), como os próprios logs de progresso mostram, estourando
   os 5s do teto de latência nos dois provedores:

   ```
   [CI Progress] Evaluation running for 2m 30s - Completed 1/2 tests (50%)
   [CI Progress] Evaluation running for 3m 30s - Completed 1/2 tests (50%)
   [Evaluation] ✓ Complete! 2/2 tests in 3m 56s
   ...
   Results:
     0 passed (0%)
     ✗ 2 failed (100%)
   Duration: 3m 57s (concurrency: 4)
   FAIL (100): ./seguranca/endurecer-networkpolicy/promptfooconfig.yaml
   ```

   É **a Decisão D em ato**: num runner + free-tier, a latência é weather do provedor, não
   regressão de prompt (o conteúdo da policy sai correto, como no CP08). Por isso a régua de
   regressão real se apoia em conteúdo + juízes, e a latência pede um endpoint estável para
   voltar a ser gate confiável.

2. **`triagem-pods` — reprovou 1/6 porque o gpt-4o-mini inventou problema no snapshot
   saudável.** No caso da Entrada 3 (tudo saudável), o Gemini deu `[PASS] Todos os pods estão
   saudáveis`, mas o gpt-4o-mini marcou um pod estável como falho:

   ```
   │ [PASS] Veredito: Todos │ [FAIL] 1 pod           │
   │ os pods estão          │ problemático, 3        │
   │ saudáveis.             │ saudáveis.             │
   │                        │ **`sentinel-worker-5b… │
   │                        │ — `Running` 🔴         │
   │                        │ - **Causa provável:**  │
   │                        │ o pod teve um reinício │
   │                        │ recente (1 vez em 3    │
   ...
   Results:
     ✓ 5 passed (83.33%)
     ✗ 1 failed (16.67%)
   FAIL (100): ./sre/triagem-pods-kubernetes/promptfooconfig.yaml
   ```

   A dupla-trava do assert do caso saudável (exige sinal de saúde **e** ausência de marcador
   de falha) pegou o gpt-4o-mini em CI — o mesmo achado do CP08, agora automatizado.

**O gate fechando a suíte — o job vermelho:**

```
FAIL (100): ./sre/triagem-pods-kubernetes/promptfooconfig.yaml
Regressão detectada: ao menos um prompt falhou a suíte. Barrando o merge.
Error: Process completed with exit code 1.
```

Esta é a evidência central: **itens reprovaram → o laço acumulou `fail=1` (capturando o exit
100 do `promptfoo`) → o step emitiu "Barrando o merge" → o job saiu com `exit code 1` → o
check do PR ficou vermelho.** Nenhum merge entra por cima disso. E note o ponto de desenho:
**o gate não distingue "prompt piorou" de "modelo fraco naquele item" ou "provedor lento" —
qualquer assert vermelho barra o merge**, que é o comportamento correto para um gate (e a
razão pela qual a Decisão D recomenda tirar a latência do caminho crítico com um endpoint
estável, para o vermelho significar sempre "qualidade caiu").

> **Estado do item:** workflow + cobertura entregues, validados estaticamente e **executados
> em CI** — os dois juízes novos aprovados (mais o de causa-raiz), e o build barrando o merge
> com `exit code 1` em uma suíte com item reprovado. Evidência real, copiada do log da
> execução, não presumida.

**Como reproduzir um vermelho cirúrgico** (para amarrar o vermelho a um assert específico, em
vez do fail natural de `networkpolicy`/`triagem-pods`): quebrar de propósito um prompt num
branch e abrir PR — ex.: remover o campo `ESCALAR PARA:` de `sre/nota-triagem-padronizada/prompt.md`
(o `regex ESCALAR PARA:.*@\w+` reprova), ou mandar `sre/analise-causa-raiz/prompt.md`
"responder só o STATUS sem raciocinar" (o juiz derruba C1, nota < 6). O mecanismo de gate é
o mesmo já comprovado acima.

---

## 4. Curadoria — justificativa estendida do gate (≥ 2 alternativas por decisão)

### Decisão A — Como rodar: CLI em laço × action oficial

A action `promptfoo/promptfoo-action@v1` recebe **um** `config` e documenta **uma** chave
(`openai-api-key`); seu forte é comentar o diff before/after de **um** prompt no PR. Este
repo tem **6 configs** em pastas diferentes e **dois** provedores (Google + OpenRouter).

- **Alternativa 1 — só a action:** teria que instanciar a action 6 vezes (uma por config) e
  ainda assim não injeta a `GOOGLE_API_KEY`/`OPENROUTER_API_KEY` do jeito que os itens
  pedem. Ganha o comentário visual; perde em cobrir a suíte real e os provedores.
- **Alternativa 2 (escolhida) — CLI em laço:** `npm i -g promptfoo` + `promptfoo eval` sobre
  os 6 configs, com as duas chaves no `env` do job. Cobre tudo de uma vez, controla o exit
  code (o gate) e não amarra a um provedor. Perde o comentário rico nativo — compensado pelo
  `$GITHUB_STEP_SUMMARY` (tabela de pass/fail por config, sempre visível no run).
- **Custo de cada uma:** a action é mais rápida de plugar mas quebra no multi-config/multi-
  provider; o CLI exige escrever o laço mas é o único que cobre o repo como ele é. Para um
  **item único** com before/after visual, a action volta a valer — fica anotada como camada
  opcional por-item, não como gate.

### Decisão B — O que barra o build: determinístico **e** juiz × só determinístico

- **Alternativa 1 — só asserts determinísticos barram; juiz é consultivo** (comenta a nota,
  não reprova). Vantagem: build 100% reprodutível, zero risco de falso-vermelho por
  flutuação do juiz. Custo: uma regressão de **qualidade** (a causa-raiz para de achar a
  causa, mas mantém o formato) **passa** — exatamente o que o CP09 existe para pegar. O gate
  ficaria cego para o que mais importa nos itens de saída aberta.
- **Alternativa 2 (escolhida) — determinístico + juiz, ambos hard gate**, com o juiz
  blindado contra flutuação: `temperature: 0`, corte **≥ 6 com margem** (a calibração do
  CP09 deu 8/8 na referência e 1/8 na fraca — Δ0 contra a nota humana, folga larga até o
  corte) e família cruzada (anti self-preference). Vantagem: pega regressão de forma **e** de
  qualidade. Custo: um juiz não-determinístico pode, num caso de fronteira (nota real ~6),
  oscilar e reprovar por ruído. Mitigação real: temp 0 + a margem do corte + as fixtures de
  calibração versionadas, que detectam se o juiz "descalibrou" antes de ele barrar trabalho
  bom. Se a flutuação virasse problema medido, o próximo passo seria média de N execuções do
  juiz ou `threshold` no assert — anotado, não necessário hoje.
- **Alternativa 3 — tudo consultivo (nunca barra):** vira relatório, não gate; descartada,
  porque o objetivo do checkpoint é justamente **impedir** o merge da regressão.

### Decisão C — Escopo: suíte inteira × só os prompts alterados

- **Alternativa 1 — só os configs cujo prompt mudou** (via `git diff`/`paths` filtrando por
  item). Vantagem: no pior caso é o mais rápido e barato. Custo: **risco de regressão-miss**.
  Uma mudança na `rubrica-juiz.md`, na fixture de diagnóstico ou no preço de um provider
  afeta itens cujo `prompt.md` não mudou — e o diff por prompt deixaria passar. Exige um mapa
  de dependências "qual arquivo afeta qual config" que é fácil de errar.
- **Alternativa 2 (escolhida) — suíte inteira, sempre, com cache.** O cache do promptfoo
  (chaveado pelo conteúdo de prompts+configs) faz o trabalho fino: **prompt intocado é
  servido do cache** (perto de zero token), **só o que mudou chama o modelo**. Ou seja,
  ganha-se a segurança de reavaliar tudo (zero regressão-miss) **pagando** basicamente só
  pelos itens que mudaram — o benefício de custo do "só alterados" sem o risco dele. Com 6
  configs, o overhead de listar todos é irrelevante.
- **Trade-off tempo × token × risco:** "só alterados" economiza tempo de _wall-clock_ no
  pior caso, mas terceiriza a corretude para um mapa de dependências frágil; "suíte + cache"
  gasta um pouco mais de tempo de orquestração e **elimina** o risco de deixar passar
  regressão indireta. Num repo pequeno, a corretude ganha fácil. Se a biblioteca crescer
  para dezenas de itens, revisita-se com um filtro por `paths` **por item** — mantendo o
  cache como freio de custo.

### Decisão D — Latência/custo como parte do gate

Os asserts `latency ≤ 5s` e `cost ≤ US$ 0,01` do CP08 são qualidade operacional — mas a
execução do CP08 mostrou que a **latência** medida num runner compartilhado batendo em
endpoint free-tier é **ruído** (o Gemini free-tier deu 233s de backoff numa geração que o
outro provedor fez em 13s; foi weather do provedor, não regressão de prompt).

- **Alternativa 1 — latência como hard gate cru:** honesto com o teto, mas encheria o CI de
  vermelhos que **não são regressão** (rate-limit do dia, runner lento). Um gate que fica
  vermelho por motivo alheio ao prompt treina o time a ignorar o vermelho — pior que não ter.
- **Alternativa 2 (escolhida) — conteúdo + juiz são o gate de regressão; latência/custo
  continuam medidos, mas o gate de merge exige um endpoint estável** (conta paga / provedor
  de CI sem rate-limit agressivo) para que a latência vire sinal de novo. Enquanto o CI roda
  em free-tier, a latência é lida como informativa (aparece no resumo) e a decisão de merge
  se apoia em conteúdo e qualidade. Custo: exige provisionar um endpoint estável para o CI —
  o preço de ter latência como gate confiável.
- **Alternativa 3 — remover latência/custo da suíte:** perderia a consciência de custo que o
  playbook trata como qualidade. Descartada: o teto fica no config (é parte do contrato do
  item); o que muda é **onde** ele barra (endpoint estável), não **se** existe.

### Decisão E — Custo por PR e guarda das chaves

- **Chaves — repo secrets (escolhido) × environment secrets × YAML.** Hardcode no YAML é
  vazamento imediato: descartado. Repo secrets (`secrets.GOOGLE_API_KEY`, etc.) é o padrão:
  injetadas como env, nunca logadas, fora do versionamento. **Environment secrets** (com
  required reviewers) seriam o passo extra se o gate gastasse muito por run e se quisesse
  aprovação humana antes de queimar token — hoje é overkill; anotado para quando o custo por
  PR justificar.
- **Custo por PR — controlado por quatro alavancas somadas:** (1) **cache** — o maior freio,
  só o que mudou chama o modelo; (2) **modelos baratos** — geração em `gpt-4o-mini`, juiz em
  `gemini-2.5-flash`, os mais leves de cada família; (3) **`concurrency: cancel-in-progress`**
  — vários pushes seguidos no mesmo PR só avaliam a última revisão; (4) **`paths`** — PRs que
  não tocam o playbook nem rodam a suíte. Alternativas consideradas: rodar o **topo caro da
  pirâmide** (os juízes) **só no push para a principal**, deixando os PRs com o determinístico
  — corta custo, mas atrasa o feedback de qualidade para depois do merge; e **nightly** em vez
  de por-PR — mais barato ainda, mas deixa a regressão viver até a noite. Ambas trocam custo
  por atraso na detecção; ficam como perfis de custo alternativos se a conta de token apertar.
  Uma regra de dev que **não** vai para o CI: o `--no-cache` (essencial em dev para medir
  latência/custo de verdade) **fica fora** do CI de propósito — no CI o cache é justamente o
  que barateia o PR.

### Fecho — o que este checkpoint fecha

Com os dois gates de juiz novos, **todos os 6 itens** têm avaliação: determinística onde a
saída é estruturada, por julgamento onde é aberta. O pipeline transforma o `promptfoo eval`
manual dos CP08/CP09 em **gate automático de merge** — e isso já rodou em CI (§3.2): os dois
juízes novos nasceram verdes e o build barrou o merge com `exit code 1` num item reprovado.
É a biblioteca deixando de ser texto versionado e virando **código de produção**: o playbook
que o time pega e confia porque nada entra sem passar pelos testes.

Dois pontos honestos que a execução em CI deixou registrados, sem varrer para baixo do
tapete: (1) o **endpoint estável** que devolve à latência o status de gate confiável
(Decisão D) — enquanto o CI roda em free-tier, o `triagem-pods`/`networkpolicy` podem
reprovar por weather do provedor, e é por isso que a régua de regressão real se apoia em
conteúdo + juízes; (2) os runners do GitHub emitem um **aviso de depreciação do Node 20**
(as actions `checkout`/`setup-node`/`cache` ainda o referenciam internamente) — é só aviso,
não quebra o job, e se resolve na próxima subida de major dessas actions.
