# Checkpoint 09 — Gate de qualidade com LLM-as-judge

> Playbook de IA Operacional da Aegis — Avaliação. O `promptfoo` determinístico do CP08
> trava formato, latência e custo — não pega **qualidade**. A RCA de causa-raiz
> (`sre/analise-causa-raiz/`) tem saída aberta, sem resposta única checável por regex:
> ganha aqui um **gate de julgamento** — um juiz LLM aplicando uma rubrica de 4 critérios
> e reprovando a análise que não chega à causa. É este eval que o CP10 põe no pipeline.

---

## 1. Decisões de método

### Onde o gate mora (e por que não em `devops/`)
O config vive **ao lado do prompt**, na pasta do item: `sre/analise-causa-raiz/promptfooconfig.yaml`.
A biblioteca já está organizada por **domínio de negócio** (`sre/`, `seguranca/`, `data/`,
`arquitetura/`), decisão tomada quando os prompts viraram catálogo — então o item de
causa-raiz é `sre/`, não uma pasta `devops/` genérica. O princípio "o teste viaja junto
com o prompt" pede exatamente isto: mudou o `prompt.md`, o `promptfooconfig.yaml` ao lado
revalida antes do merge. Três arquivos novos, todos autocontidos na pasta do item:

| Arquivo | Papel |
|---|---|
| `rubrica-juiz.md` | A "anatomia do juiz" — role + input + output avaliado + rubrica + instruções de saída JSON. É o `rubricPrompt`. |
| `promptfooconfig.yaml` | O **gate**: gera a RCA (gpt-4o-mini) e a submete ao juiz (Gemini) com a rubrica de 4 critérios, corte ≥ 6. |
| `promptfooconfig.calibracao.yaml` | O **banco de calibração**: injeta duas saídas fixas conhecidas (forte/fraca) no mesmo juiz para conferir contra a nota humana. |

### Determinístico + probabilístico, somados (não substituídos)
A avaliação por julgamento **não apaga** a camada determinística — ela se **soma**. O que é
estrutural e não muda (rótulos, latência, custo, regex) fica no assert determinístico,
rápido e barato; o que exige **interpretação** (a RCA chegou à causa? separou efeito de
origem?) fica no juiz. É a pirâmide de testes fechando: base determinística larga, topo de
julgamento estreito e caro. O gate do CP09 é o topo dessa pirâmide para a causa-raiz.

### A anatomia do juiz (os 4 blocos obrigatórios)
O `rubrica-juiz.md` segue a estrutura de um prompt bem-formado, na ordem que rende melhor
reasoning:
1. **Role / linha de avaliação** — SRE principal, avaliador **independente e cético**, que
   ignora verbosidade como proxy de qualidade e, na dúvida, arredonda para baixo (o gate
   existe para barrar, não para deixar passar).
2. **Input original + output avaliado** — o pacote de artefatos do incidente (`{{config}}`,
   `{{metricas}}`, `{{logs}}`) **e** a RCA sob avaliação (`{{ output }}`). Dar o input ao
   juiz é deliberado: o output sozinho perde o contexto do que foi pedido, e o juiz precisa
   dele para checar se cada elo tem sinal real.
3. **Rubrica** — os 4 critérios com âncoras 0/1/2 e a regra de decisão (o `value` do assert).
4. **Instruções de saída** — JSON estrito com **raciocínio ANTES do veredito**. A ordem
   importa: pedir o score primeiro faz o juiz cravar a nota antes de raciocinar; raciocínio
   antes → nota mais fundamentada. Saída em JSON (não markdown) porque é consumida por
   automação/CI.

### Escolha de modelos: geração ≠ juiz (anti self-preference)
O vício mais perigoso do LLM-as-judge é o **self-preference** — o juiz favorecer outputs da
própria família, porque foram treinados com a mesma mecânica. Mitigação: **gerar com uma
família e julgar com outra**. Uso os **dois provedores já em uso no repo** (os mesmos do
`nota-triagem-padronizada`), atribuindo os papéis para caírem em famílias distintas. **Quem
julga foi decidido pela calibração, não a priori** (ver §4): a primeira tentativa pôs o
gpt-4o-mini como juiz e ele **reprovou a RCA de referência** (rebaixou C1/C2); a calibração
mandou trocar o juiz. Configuração final:

- **Geração da RCA:** `openrouter:openai/gpt-4o-mini` — família **OpenAI**. Saída **aberta** →
  o raciocínio importa; `temperature: 0.2` para reduzir variância entre rodadas. O OpenRouter
  é o mesmo gateway do CP08 (uma `OPENROUTER_API_KEY` alcança gpt-4o-mini sem conta na OpenAI).
- **Juiz:** `google:gemini-2.5-flash` — família **Google**, diferente da OpenAI que gerou,
  resolvendo o self-preference; `temperature: 0` para um veredito reprodutível. Julgar uma
  cadeia causal é raciocínio aberto, então o thinking do juiz fica ligado (não se aplica
  `thinkingBudget: 0` aqui, ao contrário dos itens estruturados do CP08). Na calibração o
  Gemini se mostrou o juiz mais confiável dos dois para esta rubrica.

Os outros dois vícios ficam controlados: **position bias** não se aplica (avaliação pontual,
um só output — não é pairwise), e **verbosity bias** é atacado por instrução explícita no
role ("ignore o tamanho como proxy de qualidade").

### Parametrização preservada
O juiz é tão parametrizável quanto o prompt que ele avalia: recebe os mesmos
`{{config}}`/`{{metricas}}`/`{{logs}}`/`{{sistema}}`/`{{janela}}` por `vars`. Trocar o pacote
de artefatos (outro incidente) reusa o mesmo gate — a rubrica é do **tipo** de tarefa (RCA),
não deste incidente específico. Só as âncoras citam o caso do Cerebro como referência concreta.

---

## 2. Entregável

### 2.1 A rubrica (4 critérios, escala 0–2, corte ≥ 6)

Cada critério vale **0** (não atende), **1** (parcial) ou **2** (atende); total de **0 a 8**.

| # | Critério | 2 (atende) | 1 (parcial) | 0 (não atende) |
|---|---|---|---|---|
| **C1** | **Causa-raiz correta** | aponta a causa real — reindex travado saturando o heap compartilhado (→ circuit breaker, timeouts, queda de cache) — como **origem** da cadeia | cita heap/reindex mas mistura com o sintoma, ou não fecha a cadeia | para no sintoma ("busca lenta", "cache baixo") ou aponta causa errada |
| **C2** | **Correlação × causa** | separa **causa de consequência** (cache hit e latência de busca são **efeito** da pressão de heap) | separa em parte; trata ≥1 efeito como causa | confunde correlação com causa (culpa cache/busca como origem) |
| **C3** | **Ação proporcional** | mitigação que ataca a **origem** (conter/pausar/reagendar o reindex) + correção definitiva estrutural, dimensionada | parcial, ou só maquia o sintoma (subir timeout/heap sem tocar no reindex), ou não separa imediata de definitiva | ausente, incoerente ou que ignora a causa |
| **C4** | **Honestidade epistêmica** | reconhece o que os dados **não** permitem concluir, avalia hipótese alternativa e declara confiança | incerteza vaga, sem lacuna nem alternativa | fabrica certeza; inventa dado fora dos artefatos |

**Regra de decisão (o gate):** aprova (`pass=true`) **somente** se `total ≥ 6` **e nenhum
critério for 0**. Um critério zerado derruba a RCA mesmo com total alto — é o **peso crítico**:
uma análise que erra a causa (C1=0) não pode passar por ser bem-escrita nos outros três.

### 2.2 O `promptfooconfig.yaml` (juiz como gate)

Em `sre/analise-causa-raiz/promptfooconfig.yaml` (íntegra versionada lá). O núcleo:

```yaml
providers:
  - id: openrouter:openai/gpt-4o-mini    # GERAÇÃO da RCA (família OpenAI)
    config: { temperature: 0.2 }
defaultTest:
  options:
    provider:                            # JUIZ — família Google, diferente da geração (OpenAI)
      id: google:gemini-2.5-flash
      config: { temperature: 0 }
  assert:
    - type: llm-rubric
      rubricPrompt: file://rubrica-juiz.md   # anatomia do juiz (role+input+output+saída JSON)
      value: |                               # a rubrica de 4 critérios + regra de decisão
        C1. CAUSA-RAIZ CORRETA … C4. HONESTIDADE EPISTÊMICA …
        REGRA DE DECISÃO: pass=true só se total >= 6 E nenhum critério == 0.
      metric: qualidade-do-juiz
tests:
  - vars: { config: …, metricas: …, logs: … }   # pacote de artefatos do incidente
```

O juiz devolve JSON estrito — `raciocinio` → `criterios{nota,justificativa}` → `total` →
`pass` → `score` (= total/8) → `reason` —, o formato mínimo que o `promptfoo` consome
(`pass`/`score`/`reason`) mais o detalhe por critério para auditoria.

### 2.3 Validação estática (não consome modelo)

```
$ promptfoo validate -c sre/analise-causa-raiz/promptfooconfig.yaml            → Configuration is valid.
$ promptfoo validate -c sre/analise-causa-raiz/promptfooconfig.calibracao.yaml → Configuration is valid.
```

---

## 3. Execução (real, verificada)

**Modelos:** geração `openrouter:openai/gpt-4o-mini`; juiz `google:gemini-2.5-flash`. Rodado
com `--no-cache` (resposta cacheada poderia reusar um veredito antigo).

### 3.1 Pontuação humana de referência (minha calibração — curadoria, não é output de modelo)

Antes de confiar no juiz, pontuei eu mesmo as duas saídas do banco de calibração. Estes são
os **alvos** contra os quais o juiz é conferido (o juiz calibrado deve ficar a ≤ 1 ponto em
cada critério, aprovar a forte e reprovar a fraca):

| Saída | C1 | C2 | C3 | C4 | Total | Veredito humano |
|---|:--:|:--:|:--:|:--:|:--:|---|
| **`rca-forte.txt`** (a RCA de referência, execução real do item de causa-raiz) | 2 | 2 | 2 | 2 | **8** | **PASS** |
| **`rca-fraca.txt`** (só sintoma: culpa busca/cache, ação maquia, sem lacunas) | 0 | 0 | 1 | 0 | **1** | **FAIL** (C1/C2/C4 zerados) |

Justificativa das âncoras (forte): C1 — abre o veredito com "a causa-raiz é a sobrecarga de
escrita do reindex prolongado, **não** a degradação de busca em si"; C2 — seção "Sintoma ×
causa" explícita, e nota que o cache 74%→29% é *efeito* da eviction sob pressão de heap;
C3 — 🔴 pausar o reindex task [88123] (ataca o gatilho) separada da 🟢 timeout/isolamento
read-write; C4 — aponta que `indices.breaker.total.limit` **não está** no `cerebro.yaml` e
pede para coletá-lo, avalia a hipótese de pico externo e a descarta com evidência.
Justificativa (fraca): C1=0 trata "busca lenta / cache baixo" como causa; C2=0 inverte
efeito (cache) e origem; C3=1 subir timeout/heap é tangencialmente plausível mas **maquia o
sintoma** e ignora o reindex; C4=0 crava "o problema está resolvido" sem lacuna nem alternativa.

### 3.2 Saída real do juiz — execução manual verificada

**Comando (banco de calibração — só o juiz Gemini roda; o `echo` não gera RCA nova):**

```bash
cd "sre/analise-causa-raiz"
export GOOGLE_API_KEY="..."       # juiz (Gemini)
promptfoo eval -c promptfooconfig.calibracao.yaml --no-cache --output calib.json
```

**Saída real (segunda rodada, com o juiz já Gemini e o `rubrica-juiz.md` ajustado):**

```
✓ Eval complete (ID: eval-QKj-2026-07-02T17:02:46)

Total Tokens: 13.574
  Grading: 13.574 (6.597 prompt, 1.255 completion)

Results:
  ✓ 1 passed (50.00%)
  ✗ 1 failed (50.00%)
  0 errors (0%)
Duration: 16s (concurrency: 4)
```

Detalhe por caso (lido do `calib.json`, campo `gradingResult`):

```
===== RCA forte (referência) — esperado pass=true, total ~8
pass: true | score(0-1): 1 | total ~ 8
reason: All assertions passed

===== RCA fraca (só sintoma) — esperado pass=false, total ~1
pass: false | score(0-1): 0.125 | total ~ 1
reason: A RCA reprovou porque falhou em identificar a causa-raiz correta e tratou
efeitos como origens, resultando em um total de 1 ponto e múltiplos critérios com nota 0.
```

**Confere com a tabela humana da §3.1, dentro do corte de ±1 ponto:**

| Saída | Total humano | Total do juiz | Δ | Veredito humano | Veredito do juiz |
|---|:--:|:--:|:--:|---|---|
| `rca-forte.txt` | 8 | **8** (score 1.0) | 0 | PASS | **PASS** ✅ |
| `rca-fraca.txt` | 1 | **1** (score 0.125) | 0 | FAIL | **FAIL** ✅ |

O juiz **cravou** os dois extremos: aprovou a RCA de referência e reprovou a só-sintoma pela
razão certa ("falhou em identificar a causa-raiz e tratou efeitos como origens" = C1/C2
zerados). Calibrado, roda sozinho a cada alteração do prompt.

### 3.3 Gate ponta-a-ponta — execução real (gera RCA nova e a julga)

**Comando (as duas chaves: gpt-4o-mini gera, Gemini julga):**

```bash
export OPENROUTER_API_KEY="..."   # geração da RCA (gpt-4o-mini)
export GOOGLE_API_KEY="..."       # juiz (Gemini)
promptfoo eval -c promptfooconfig.yaml --no-cache --output gate.json
```

**Saída real:**

```
✓ Eval complete (ID: eval-a7b-2026-07-02T17:27:13)

Total Tokens: 12.067
  Eval: 3.696 (3.157 prompt, 539 completion)      ← geração da RCA (gpt-4o-mini)
  Grading: 8.371 (4.373 prompt, 603 completion)   ← juiz (Gemini)

Results:
  ✓ 1 passed (100%)
  0 failed (0%)
  0 errors (0%)
Duration: 26s (concurrency: 4)
```

Veredito do juiz (lido do `gate.json`):

```
pass: true | score: 1 (= 8/8) | latencyMs: 7683
reason: A RCA foi aprovada porque atingiu a pontuação máxima de 8, com todos os
critérios atendidos plenamente, e nenhum critério zerado.
```

RCA que o gpt-4o-mini gerou e que o juiz aprovou (`gate.json`, output do provider — verbatim):

```
**Veredito:** A causa-raiz da degradação no serviço Cerebro é a saturação da memória heap, levando a um comportamento de throttling e falhas nas buscas.

- **Linha do tempo**  
  - 08:00 → latência de busca em 850ms (métrica)  
  - 08:41 → início do throttling de indexação (log)  
  - 09:31 → uso de heap em 86% (log)  
  - 09:58 → fila de thread de escrita cheia, rejeitando requisições (log)  
  - **10:00 → latência de busca em 6700ms (métrica)** — ponto de virada.

- **Causa-raiz**  
  - **Gatilho:** reindexação noturna em andamento (config: `reindex_job.schedule: "0 2 * * *"`).  
  - **Propagação:** uso crescente de heap devido à reindexação, atingindo 94% às 10:00 (métrica: `heap_used_pct` em 94% às 10:00).  
  - **Efeito:** latência de busca elevada e resultados parciais (métrica: `search_p99_ms` em 6700ms às 10:00).

- **Sintoma × causa**  
  A latência alta de busca era um sintoma visível, enquanto a causa era a saturação da heap e o throttling de indexação.

- **Fatores contribuintes**  
  - Reindexação noturna em execução, aumentando a carga no sistema.  
  - Configuração de heap limitada a 8GB, que se mostrou insuficiente.  
  - Cache de consultas com taxa de acerto em queda, reduzindo a eficiência das buscas.

- **Ações**  
  - **🔴 Mitigação imediata:** interromper a reindexação em andamento para liberar recursos (parar o job de reindexação).  
  - **🟢 Correção definitiva:** aumentar a configuração de heap para 12GB e revisar a estratégia de reindexação para horários de menor carga.

- **Confiança e lacunas**  
  Nível de confiança: alto.  
  Hipótese alternativa: a degradação poderia ser causada por um aumento inesperado no volume de buscas, mas os dados de `indexed_docs_per_s` mostram uma carga estável.  
  O que coletar: monitorar o comportamento do sistema após a mitigação e revisar logs de reindexação para entender melhor o impacto no desempenho.
```

O gate rodou de ponta a ponta como roda em CI: **gerou** a RCA (gpt-4o-mini, ~3,7k tokens) e a
**julgou** (Gemini, ~8,4k tokens), aprovando com 8/8. Nota de trade-off custo/latência: a
chamada dupla (gerar + julgar) leva ~26s no total — bem acima dos 5s dos itens estruturados do
CP08 —, o que é esperado e aceitável: julgamento é caro por natureza e roda no merge, não no
plantão. Uma observação de rigor fica registrada na §4 (a RCA gerada é boa, mas mais rasa que a
de referência, e o juiz ainda assim deu 8/8).

---

## 4. Curadoria

**Como calibrei o juiz — e por que a calibração não foi ritual.** Calibração é confrontar o
juiz com a **verdade humana** antes de soltá-lo sozinho. Montei um banco com **os dois
extremos** — a RCA de referência (que sei correta, 8/8) e uma RCA só-sintoma que eu mesmo
escrevi (o modo de falha nº 1 do item: parar no sintoma). Injetei ambas via provider `echo`
(que não gera nada, só devolve o texto fixo), para o juiz gradar **saídas conhecidas** e eu
medir o desalinhamento. Alvo: ≤ 1 ponto por critério, forte aprovada, fraca reprovada.

**A primeira rodada reprovou — e reprovou o alvo errado.** Com **gpt-4o-mini como juiz**, a
`rca-fraca` foi corretamente a 0/8, mas a `rca-forte` levou **4/8 (FAIL)**, com o juiz
alegando C1/C2 baixos — justamente os critérios que aquela RCA acerta. Um juiz que reprova a
resposta de referência é um gate quebrado: deixaria passar lixo e barraria trabalho bom.
Duas causas, corrigidas em conjunto (a régua **não** se mexeu — mexi no juiz, como manda o
processo):

1. **Juiz fraco demais para a nuance.** Entre os dois provedores disponíveis, troquei o papel:
   **Gemini 2.5 Flash virou o juiz** (com thinking, é o mais confiável dos dois para aplicar a
   rubrica em português) e o **gpt-4o-mini passou a gerar** — mantendo geração e juiz em
   famílias distintas (self-preference intacto: OpenAI gera, Google julga).
2. **Minha própria instrução sabotava o juiz.** O `rubrica-juiz.md` dizia "na dúvida, escolha
   a nota menor"; com modelo pouco discriminativo, isso colapsou a escala e rebaixou tudo para
   1. Reescrevi para **"rigor não é rebaixar por precaução; elo com sinal real merece 2"** e
   acrescentei um bloco `<como_pontuar>` com âncoras concretas de quando cada critério vale
   2/1/0 (o few-shot que ancora a escala).

**A segunda rodada cravou:** `rca-forte` **8/8 PASS**, `rca-fraca` **1/8 FAIL** (§3.2), Δ zero
contra a nota humana nos dois. Registro isto porque **é o valor do checkpoint em ato**: o gate
existe para pegar RCA fraca, mas a *calibração* existe para pegar **juiz fraco** — e pegou,
antes de qualquer decisão de plantão depender dele. Um gate não calibrado que reprova o bom é
pior que gate nenhum.

Os pontos que já vinham endurecidos de saída e resistiram à calibração:

- **Peso crítico no C1/C2 via "nenhum critério zerado".** Sem essa regra, uma RCA
  bem-escrita e acionável que **erra a causa** poderia somar 6 com C1=0 e passar — exatamente
  o que o gate existe para impedir. Um critério zerado reprova, independente do total. É o
  equivalente ao *quality gate* de pipeline: achado crítico barra o merge sozinho.
- **Raciocínio antes do veredito.** A ordem das chaves do JSON (`raciocinio` primeiro, `pass`
  depois) não é cosmética: força o juiz a correlacionar RCA × evidência antes de cravar a
  nota. Invertido, ele decide cedo e racionaliza depois.
- **Anti-verbosidade no role.** A `rca-forte` é longa e a `rca-fraca` é curta — o risco real é
  o juiz premiar a longa **por ser longa**. O role manda ignorar o tamanho como proxy de
  qualidade. A calibração com uma fraca **curta** e uma forte **longa** é o teste direto desse
  viés (e o juiz passou: aprovou a longa pela substância, reprovou a curta pela substância —
  não pelo comprimento).
- **Juiz de outra família.** A RCA nasce no gpt-4o-mini (OpenAI); se o juiz também fosse
  OpenAI, o self-preference inflaria a nota. Gemini (Google) como juiz é a trava — e a família
  dividida é verificável no próprio config (geração `openrouter:openai/` × juiz `google:`).

**O limite honesto que permanece.** O gate é pontual (avalia um output por vez), não pairwise
— suficiente para "passa/reprova" a cada alteração do prompt, mas não compara duas versões do
prompt entre si (isso seria pairwise, com o cuidado extra de position bias). E a calibração
com **dois** pontos (um forte, um fraco) prova os extremos; o meio-termo (uma RCA que acerta a
causa mas erra a ação, C1=2/C3=0) só se calibra acrescentando fixtures intermediárias ao banco
— anotado como aperto futuro quando o gate acumular histórico de falsos positivos/negativos.

E o meio-termo apareceu **na primeira execução ponta-a-ponta** (§3.3): a RCA que o gpt-4o-mini
gerou é **correta mas mais rasa** que a de referência — acerta o gatilho (reindex → heap →
throttling → busca) e separa sintoma de causa, mas evidencia menos elo a elo (não cita o
circuit breaker nominalmente) e a correção definitiva escorrega para "subir o heap para 12GB",
que beira o maquiar-sintoma que a `rca-fraca` faz. Minha nota humana daria C1=2/C2=2/C3=1/C4=2
= **7 (PASS)**; o juiz Gemini deu **8 (PASS)**. Mesmo veredito, mas o juiz foi **1 ponto mais
generoso em C3** — dentro do corte de ±1, então aceitável, mas é o lembrete de que um juiz
pontual tende a leve otimismo no meio da escala. É exatamente onde as fixtures intermediárias
entrariam para apertar. O gate acertou o que importa (aprovar uma RCA genuinamente boa), e a
divergência fica registrada em vez de varrida.

**O gate roda a cada alteração — é a ponte para o CP10.** O valor não é rodar uma vez: é o juiz
**barrar automaticamente** toda mudança no `prompt.md` de causa-raiz que derrube a nota abaixo
de 6. Hoje isso é `promptfoo eval` na mão; no CP10 vira etapa de CI — mudou o prompt, o gate
roda, a nota caiu, o merge falha. É a mesma automação que fechou os itens estruturados no CP08,
agora estendida ao que só o julgamento alcança. Com CP08 (determinístico) + CP09 (julgamento),
a pirâmide de avaliação da biblioteca está completa: falta só colocá-la no pipeline.
