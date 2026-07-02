# Checkpoint 08 — Testes determinísticos com promptfoo

> Playbook de IA Operacional da Aegis — Avaliação. Cada prompt de saída estruturada
> ganha um `promptfooconfig.yaml` ao lado do `prompt.md`: o teste viaja junto com o
> prompt e roda em CLI/CI, para que ninguém confie num item sem verificação.

## 1. Decisões de método

**Por que só três itens.** A avaliação determinística (regex, `contains`, contagem por
código, `latency`, `cost`) é a base da pirâmide de testes: rápida e barata, mas só serve
quando a saída tem forma verificável sem julgamento (`eval-promptfoo`, `eval-3-perguntas`).
Os itens de **saída aberta** — causa-raiz (CP03), decisão de backpressure (CP04) e
migração (CP05) — não têm resposta única checável por regra estática; entram na camada de
avaliação por julgamento (rubrica / LLM-as-judge / golden answer) dos próximos checkpoints,
não aqui. Ficam **três** itens de saída estruturada:

| Item | Config | O que o teste trava |
|---|---|---|
| Nota de triagem padronizada | `sre/nota-triagem-padronizada/promptfooconfig.yaml` | 5 rótulos fixos, handle `@time`, ≤ 8 linhas |
| Triagem de saúde de pods | `sre/triagem-pods-kubernetes/promptfooconfig.yaml` | pod problemático + causa por caso; reconhecer o saudável |
| Endurecimento de NetworkPolicy | `seguranca/endurecer-networkpolicy/promptfooconfig.yaml` | YAML default-deny, sem allow-all, fluxos mínimos comentados |

**Onde o config mora.** Ao lado do `prompt.md`, na pasta do item — não numa pasta `devops/`
separada. A biblioteca já está organizada por **domínio de negócio** (`sre/`, `seguranca/`),
e o princípio "o teste viaja junto com o prompt" pede exatamente isso: mudou o prompt, o
`promptfooconfig.yaml` ao lado revalida antes do merge. O `file://prompt.md` do config é
relativo à própria pasta, então o par `prompt.md` + `promptfooconfig.yaml` é autocontido.

**Escolha de modelo (o trade-off que os dois limites cobram).** Os asserts `latency ≤ 5s`
e `cost ≤ US$ 0,01` tratam custo e velocidade como parte da qualidade — e conversam direto
com o provider. A execução da biblioteca é feita em modelo barato (a criação é que usa o
forte). Por isso os dois providers de cada config são os mais leves de cada fornecedor:

- `google:gemini-2.5-flash` — provider 1 (Google), o de execução padrão;
- `openrouter:openai/gpt-4o-mini` — provider 2, de outro fornecedor. Em vez de bater direto
  na OpenAI, passa pelo **OpenRouter** (um gateway: uma só `OPENROUTER_API_KEY` dá acesso a
  modelos de vários fornecedores). O modelo continua sendo o `gpt-4o-mini` do esqueleto —
  logo, um fornecedor distinto do Google, satisfazendo a regra do cross-provider — mas sem
  exigir conta na OpenAI. Requer `OPENROUTER_API_KEY` exportada.

Ambos declarados com `config: temperature: 0.0`: em avaliação determinística, zerar a
temperatura reduz a variância entre execuções e torna os asserts mais reprodutíveis. O
provider Gemini leva ainda `generationConfig.thinkingConfig.thinkingBudget: 0` — **desligar
o raciocínio** é o que mantém a chamada dentro do teto de latência (a execução mostrou
6–9s com raciocínio × 1–2s sem; ver §3.2 e §4). Para saída estruturada isso não custa
qualidade: a forma é fixa, não há decisão aberta a raciocinar.

Um Sonnet/Opus (ou um GPT full) daria saída melhor, mas arrisca **reprovar no `cost` e no
`latency`** — e o ponto do checkpoint é justamente sentir esse limite. Se um item de saída
estruturada só passa nos requisitos de conteúdo com um modelo caro, isso é sinal para
**simplificar o prompt**, não para afrouxar o teto de custo.

**Parametrização preservada.** Cada `vars` do config preenche os mesmos `{{placeholders}}`
do `prompt.md` (`{{alerta}}`, `{{snapshot}}`, `{{manifesto}}` + `{{regras_padrao}}` +
`{{mapa_servicos}}`). Os parâmetros opcionais (`contexto_extra`, `namespace`, `provedor`)
vão em `defaultTest.vars` como `nenhum`/valor fixo, para o Nunjucks não deixar variável sem
resolver. Os testes são o mesmo contrato do frontmatter `inputs`, agora executável.

## 2. Entregável — os três `promptfooconfig.yaml`

Os três arquivos estão versionados nas pastas dos itens. Tipos de assert usados, por
requisito do enunciado:

**`sre/nota-triagem-padronizada/promptfooconfig.yaml`** — asserts em `defaultTest` (valem
para os 3 alertas do CP02):
- `contains` × 5 → os rótulos `ALERTA:`, `IMPACTO:`, `HIPÓTESE INICIAL:`, `AÇÃO IMEDIATA:`, `ESCALAR PARA:`;
- `regex: ESCALAR PARA:.*@\w+` → handle de escalonamento;
- `javascript` → contagem de linhas não vazias `≤ 8` (concisão);
- limites operacionais: `latency: 5000` (nativo) + custo em `javascript` (ver §4).

**`sre/triagem-pods-kubernetes/promptfooconfig.yaml`** — asserts por caso (3 snapshots do CP01):
- Entrada 1: `contains sentinel-api-7d9c8b6f4-h4m2t` + `regex OOMKilled|[Mm]em[óo]ria`;
- Entrada 2: `contains` dos dois pods + `regex 2\.9\.2|ImagePullBackOff|manifest unknown` + `regex [Ii]nsufficient|[Cc]pu`;
- Entrada 3 (saudável): `javascript` que exige ausência de qualquer classificação de falha
  (`🔴`, `crashloopbackoff`, `oomkilled`, …) **e** presença de sinal de saúde (`saudável`, `🟢`, "nenhum pod problemático"…);
- limites operacionais em `defaultTest`: `latency: 5000` (nativo) + custo em `javascript`
  (usa o custo nativo quando o provider reporta; senão calcula pelos tokens — ver §4).

**`seguranca/endurecer-networkpolicy/promptfooconfig.yaml`** — asserts na NetworkPolicy gerada:
- `contains kind: NetworkPolicy` + `regex policyTypes:[\s\S]*Ingress` e `…Egress`;
- `javascript` que procura `- {}` **só como item de lista YAML** (`/^\s*-\s*\{\s*\}\s*$/m`)
  → sem allow-all na policy gerada, ignorando o `- {}` citado em prosa no Diagnóstico e
  independente de como a IA cerca o bloco (ver evolução na §4);
- `contains 5432` e `contains 9200` → egress p/ Forge e Cerebro; `regex app:\s*relay` → ingress do Relay;
- `contains "#"` → há comentário de regra;
- limites operacionais: `latency: 5000` (nativo) + custo em `javascript` (ver §4).

Validação estática dos três (não consome modelo):

```
$ promptfoo validate -c sre/nota-triagem-padronizada/promptfooconfig.yaml     → Configuration is valid.
$ promptfoo validate -c sre/triagem-pods-kubernetes/promptfooconfig.yaml       → Configuration is valid.
$ promptfoo validate -c seguranca/endurecer-networkpolicy/promptfooconfig.yaml → Configuration is valid.
```

## 3. Execução (real, verificada)

**Execução manual verificada.** Rodada **cross-provider** com os dois fornecedores ativos:
provider 1 `google:gemini-2.5-flash` (`temperature: 0.0`, `thinkingConfig.thinkingBudget: 0`)
e provider 2 `openrouter:openai/gpt-4o-mini` (gpt-4o-mini via OpenRouter). Cada item rodado
com `promptfoo eval --no-cache` — o `--no-cache` é essencial: resposta cacheada reporta
`latencyMs ≈ 0` e `cost ≈ 0`, o que faria `latency`/`cost` passarem sem medir nada. O
detalhe por assert vem de um leitor do JSON (`--output`) percorrendo
`gradingResult.componentResults` de cada caso; como há 2 providers, cada entrada aparece
duas vezes (3 entradas × 2 providers).

**Comando:**

```bash
export GOOGLE_API_KEY="..."       # Gemini (AI Studio), free-tier — provider 1
export OPENROUTER_API_KEY="..."   # OpenRouter — provider 2 (gpt-4o-mini)
promptfoo eval -c sre/nota-triagem-padronizada/promptfooconfig.yaml   --no-cache --output resultado-nota.json
promptfoo eval -c sre/triagem-pods-kubernetes/promptfooconfig.yaml    --no-cache --output resultado-pods.json
promptfoo eval -c seguranca/endurecer-networkpolicy/promptfooconfig.yaml --no-cache --output resultado-np.json
```

### 3.1 `nota-triagem-padronizada` — 6/6 PASS (3 entradas × 2 providers)

```
Results:
  ✓ 6 passed (100%)
  0 failed (0%)
  0 errors (0%)
Duration: 3s (concurrency: 4)

Providers:
  google:gemini-2.5-flash: 3.973 (3 requests; 3.650 prompt, 323 completion)
  openrouter:openai/gpt-4o-mini: 3.714 (3 requests; 3.442 prompt, 272 completion)
```

```
--- caso 0 | google:gemini-2.5-flash | latencyMs = 1224
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
   PASS | javascript | Assertion passed
   PASS | latency | Assertion passed
   PASS | javascript | custo estimado US$ 0.000662
--- caso 1 | openrouter:openai/gpt-4o-mini | latencyMs = 1968
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
   PASS | javascript | Assertion passed
   PASS | latency | Assertion passed
   PASS | javascript | custo estimado US$ 0.000233
--- caso 2 | google:gemini-2.5-flash | latencyMs = 1100
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
   PASS | javascript | Assertion passed
   PASS | latency | Assertion passed
   PASS | javascript | custo estimado US$ 0.000628
--- caso 3 | openrouter:openai/gpt-4o-mini | latencyMs = 1937
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
   PASS | javascript | Assertion passed
   PASS | latency | Assertion passed
   PASS | javascript | custo estimado US$ 0.000227
--- caso 4 | google:gemini-2.5-flash | latencyMs = 1039
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
   PASS | javascript | Assertion passed
   PASS | latency | Assertion passed
   PASS | javascript | custo estimado US$ 0.000612
--- caso 5 | openrouter:openai/gpt-4o-mini | latencyMs = 1755
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
   PASS | javascript | Assertion passed
   PASS | latency | Assertion passed
   PASS | javascript | custo estimado US$ 0.000220
```

Os dois providers passaram nos 3 alertas: cinco rótulos, handle `@time`, ≤ 8 linhas,
latência ~1–2s e custo na casa de US$ 0,0002–0,0007.

### 3.2 `triagem-pods-kubernetes` — Gemini 3/3; gpt-4o-mini 1/3 (achados reais, não bug de teste)

Nota histórica: o `triagem-pods` chegou a reprovar `latency` no próprio Gemini quando o
raciocínio estava **ligado** (`caso 0 7774ms`, `caso 1 8843ms`, `caso 2 6035ms`); com
`thinkingBudget: 0` o Gemini passou os três. No cross-provider abaixo, os fails que restam
são do **gpt-4o-mini** e são legítimos:

```
Results:
  ✓ 4 passed (66.67%)
  ✗ 2 failed (33.33%)
  0 errors (0%)
Duration: 6s (concurrency: 4)

Providers:
  google:gemini-2.5-flash: 6.030 (3 requests; 5.368 prompt, 662 completion)
  openrouter:openai/gpt-4o-mini: 5.650 (3 requests; 5.093 prompt, 557 completion)
```

```
--- caso 0 | google:gemini-2.5-flash | latencyMs = 1882
   PASS | latency | Assertion passed
   PASS | javascript | custo estimado US$ 0.001231
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
--- caso 1 | openrouter:openai/gpt-4o-mini | latencyMs = 2759
   PASS | latency | Assertion passed
   PASS | javascript | custo estimado US$ 0.000353
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
--- caso 2 | openrouter:openai/gpt-4o-mini | latencyMs = 5808
   FAIL | latency | Latency 5808ms is greater than threshold 5000ms
   PASS | javascript | custo estimado US$ 0.000414
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
   PASS | regex | Assertion passed
--- caso 3 | google:gemini-2.5-flash | latencyMs = 2065
   PASS | latency | Assertion passed
   PASS | javascript | custo estimado US$ 0.001376
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
   PASS | regex | Assertion passed
--- caso 4 | openrouter:openai/gpt-4o-mini | latencyMs = 3887
   PASS | latency | Assertion passed
   PASS | javascript | custo estimado US$ 0.000331
   FAIL | javascript | Custom function returned false const o = output.toLowerCase(); const semFalha =
--- caso 5 | google:gemini-2.5-flash | latencyMs = 831
   PASS | latency | Assertion passed
   PASS | javascript | custo estimado US$ 0.000658
   PASS | javascript | Assertion passed
```

Mapeando: casos 0/3/5 = Gemini (Entradas 1/2/3, **todos PASS**); casos 1/2/4 = gpt-4o-mini
(Entradas 1/2/3). Os dois fails do gpt-4o-mini: **caso 2** só na `latency` (5808ms, snapshot
maior, estourou 5s por 0,8s — conteúdo verde) e **caso 4** no `javascript` do caso saudável
— e este é o achado forte: o gpt-4o-mini **inventou um problema** no snapshot saudável
(marcou o `sentinel-worker` como `Running` 🔴, "reinício recente… pode indicar problema"),
enquanto o Gemini respondeu "Todos os pods estão saudáveis". A dupla-trava do assert pegou.
Não foi afrouxado — ver §4.

### 3.3 `endurecer-networkpolicy` — conteúdo 9/9 + cost PASS nos dois; `latency` FAIL nos dois

```
Results:
  0 passed (0%)
  ✗ 2 failed (100%)
  0 errors (0%)
Duration: 3m 54s (concurrency: 4)

Providers:
  openrouter:openai/gpt-4o-mini: 3.020 (1 requests; 1.996 prompt, 1.024 completion)
  google:gemini-2.5-flash: 2.906 (1 requests; 2.112 prompt, 794 completion)
```

```
--- caso 0 | openrouter:openai/gpt-4o-mini | latencyMs = 13360
   FAIL | latency | Latency 13360ms is greater than threshold 5000ms
   PASS | javascript | custo estimado US$ 0.000914
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
   PASS | regex | Assertion passed
   PASS | javascript | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
   PASS | contains | Assertion passed
--- caso 1 | google:gemini-2.5-flash | latencyMs = 233189
   FAIL | latency | Latency 233189ms is greater than threshold 5000ms
   PASS | javascript | custo estimado US$ 0.002619
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
   PASS | regex | Assertion passed
   PASS | javascript | Assertion passed
   PASS | contains | Assertion passed
   PASS | contains | Assertion passed
   PASS | regex | Assertion passed
   PASS | contains | Assertion passed
```

Nos **dois** providers todos os asserts de conteúdo passaram (`kind: NetworkPolicy`,
`policyTypes` com Ingress e Egress, allow-all ausente na policy gerada, egress em 5432 e
9200, ingress `app: relay`, comentário presente) e o custo passou. O único fail é `latency`,
nos dois — e por motivos diferentes que a §4 separa: no gpt-4o-mini é geração pesada real
(13s); no Gemini é a anomalia de backoff (233s).

## 4. Curadoria

**O que blindei nos testes (e por quê não fui mais estrito).**
- **Nota:** os asserts de rótulo são `contains` e não `regex` de linha inteira de
  propósito — travam a *presença* dos cinco campos sem prender a redação do plantonista. A
  concisão virou contagem de **linhas não vazias** em `javascript` (e não `≤ 8` de bytes),
  para não punir uma linha em branco entre campos.
- **Pods:** a causa é verificada por `regex` com alternância (`OOMKilled|memória`,
  `Insufficient|cpu`) porque o requisito é "chegar à causa", não a uma frase exata —
  determinístico sem ser frágil. O caso saudável é o mais delicado: um `contains` simples
  não distingue "está tudo Running" de "classifiquei um pod como falho". Por isso o assert
  é **dupla trava** — exige sinal de saúde **e** ausência de qualquer marcador de falha —,
  que é exatamente o edge case (não inventar problema) que o item precisa proteger. E aqui o
  cross-provider **provou o valor do teste**: no caso saudável o Gemini acertou ("Todos os
  pods estão saudáveis"), mas o **gpt-4o-mini inventou um problema** (marcou um pod estável
  como `Running` 🔴 por causa de um reinício antigo) — a dupla-trava reprovou o gpt-4o-mini
  e deixou o Gemini passar. **Não afrouxei o assert para o gpt-4o-mini passar**: isso trairia
  o propósito do teste; o fail é um sinal legítimo de que aquele modelo é menos confiável no
  "não inventar problema". Fica registrado como diferença de qualidade entre providers, não
  como bug de teste.
- **NetworkPolicy:** o allow-all foi o assert que mais evoluiu, em dois passos guiados pela
  execução. (1) A versão inicial `not-contains "- {}"` sobre a saída inteira **reprovava
  indevidamente**, porque o prompt emite um *Diagnóstico* que **cita** o `- {}` do manifesto
  de entrada como o defeito a corrigir. (2) A segunda tentativa extraía o bloco ```yaml``` e
  checava só ali — mas quebrava entre providers: o gpt-4o-mini cercava o código diferente do
  Gemini, e o `javascript` caía no fallback "saída inteira" e reprovava por falso positivo.
  A versão final é robusta e simples: procura `- {}` **só como item de lista YAML (linha
  inteira)** — `/^\s*-\s*\{\s*\}\s*$/m` —, o que ignora as menções em prosa do Diagnóstico e
  independe de como cada IA cerca o bloco. Passou nos dois providers. (Detalhe de sintaxe que
  a execução também expôs: no assert `javascript` de **uma linha** não se escreve `return` —
  o promptfoo já o injeta; `return X` de uma linha vira `return return X`. Expressão pura ou
  bloco multi-linha com `const`+`return`.) O limite honesto que permanece: `contains "#"` só
  garante que **existe** comentário, não que **toda** regra tem o seu — verificar isso pede
  percorrer `ingress`/`egress` no `javascript`; anotado como aperto futuro.
- **Custo com provider sem custo nativo.** O OpenRouter **não devolve custo**, e o assert
  `cost` nativo **erra** (não fala) nele. `inputCost`/`outputCost` no provider não bastaram
  (o provider OpenRouter não roda o cálculo). A solução final foi trocar o `cost` nativo por
  um `javascript` que usa o custo nativo quando existe (Gemini) e **calcula pelos tokens**
  quando não existe (OpenRouter, preço do gpt-4o-mini: in 0,15 / out 0,60 por 1M). Bônus: o
  assert imprime o valor estimado (`custo estimado US$ 0.000227`), o que dá mais
  rastreabilidade que o `cost` nativo. Regra do playbook: provider sem custo nativo exige
  preço declarado + cálculo por tokens.

**O trade-off custo/latência não foi teórico — foi a história desta execução.** Os dois
tetos operacionais (`latency ≤ 5s`, `cost ≤ US$ 0,01`) mandaram em quase toda decisão de
provider:

1. **`thinkingConfig.thinkingBudget: 0` é o que faz o teto de 5s ser alcançável.** O Gemini
   2.5 Flash tem raciocínio ligado por padrão, e ele **custa latência**: a triagem de pods
   com raciocínio deu **6–9s** (reprovando 5s) e, sem raciocínio, **1–2,3s** (passando) — a
   mesma bateria, o mesmo modelo, só o raciocínio a menos. Para saída **estruturada** (a
   forma é fixa; não há decisão aberta a raciocinar), desligar o thinking é a escolha certa:
   mais rápido, mais barato, mesma qualidade de conteúdo (os asserts continuaram verdes).
   Onde o raciocínio importa é justamente nos itens de saída **aberta** (CP03/04/05), que
   não entram aqui.
2. **O cache falseia `latency`/`cost`.** Resposta cacheada reporta ~0ms/~0 custo e passa os
   dois asserts sem medir nada; por isso toda a validação foi feita com `--no-cache`. Fica
   como regra do playbook: medição de latência/custo só vale com cache desligado.
3. **`cost ≤ US$ 0,01` passou folgado em todos** — o Flash sem raciocínio gera respostas
   baratas (centenas de tokens). O custo nunca foi o gargalo; a latência foi.

**A reprovação de `latency` da NetworkPolicy é honesta e diagnosticada — e o cross-provider
separou duas causas diferentes.** O conteúdo passa 9/9 (+ cost) nos dois providers; só a
`latency` reprova, em ambos, por motivos distintos:
- **gpt-4o-mini: ~13s — é geração pesada de verdade.** Esta é a mais robusta das três saídas
  (Diagnóstico + YAML + tabela + Lacunas, ~1.000 tokens); um modelo barato leva ~13s e
  estoura os 5s honestamente. É o cenário que o próprio desafio prevê: "um modelo mais lento
  pode reprovar aqui". Para caber em 5s seria preciso encurtar o formato de saída (só o YAML,
  sem diagnóstico/tabela) — o que descaracterizaria o item — ou usar um modelo mais rápido.
- **Gemini: ~233s (~4min) — é anomalia de backoff, não geração.** 794 tokens a ~3 tokens/s
  não é geração; é **retry/backoff por baixo do provedor**. Reproduzido de forma idêntica com
  cache on/off, raciocínio on/off e request isolado — e, no mesmo intervalo, os outros itens
  (o `nota` tem prompt **maior**, 3.650 tokens, contra 2.112 do `np`) responderam em ~1s, e o
  gpt-4o-mini gerou a mesma NetworkPolicy em 13s. Logo: **anomalia do free-tier do Gemini para
  aquela geração específica**, não tamanho de prompt, não o teto de 5s.

Não baixei a régua nem inflei o threshold para "passar": mantive `latency: 5000` (o desafio
o exige) e registro os fails com a causa. O caminho para fechar 10/10 aqui é um endpoint sem
rate-limit agressivo (conta paga / CI) e/ou encurtar o formato de saída deste item — decisão
que fica para quando o custo/latência dessa geração pesada virar prioridade.

**Segundo provider via OpenRouter.** O enunciado pede um segundo fornecedor. Em vez de
depender de uma conta OpenAI, o provider 2 é `openrouter:openai/gpt-4o-mini`: o mesmo
modelo do esqueleto (fornecedor distinto do Google), mas acessado pelo **OpenRouter** —
um gateway em que uma única `OPENROUTER_API_KEY` alcança modelos de OpenAI, Anthropic,
Mistral e outros. Vantagem prática: cross-provider real sem multiplicar contas. Basta
exportar `OPENROUTER_API_KEY` junto com a `GOOGLE_API_KEY` e o `eval` roda os dois
fornecedores. A única fricção que o OpenRouter trouxe — não devolver custo, quebrando o
assert `cost` nativo — está resolvida no bullet "Custo com provider sem custo nativo" acima
(cálculo do custo por tokens no `javascript`).

**Placar final (cross-provider).** `nota-triagem`: 6/6 verde nos dois providers.
`triagem-pods`: Gemini 3/3; gpt-4o-mini 1/3, com o teste expondo dois problemas reais do
modelo (um caso saudável classificado como falho, uma latência acima de 5s no snapshot
maior). `networkpolicy`: conteúdo 9/9 + cost verde nos dois; `latency` reprovada nos dois
(gpt-4o-mini por geração pesada real, Gemini por anomalia de backoff). Ou seja: dos três
itens, um passa 100%, um passa 100% no provider primário e serve de comparador de qualidade,
e um tem o conteúdo blindado com a latência condicionada ao provedor/endpoint.

**Ganchos para 09 e 10.** Os três itens estruturados agora têm rede de segurança
determinística. Os três de saída aberta (CP03/04/05) seguem descobertos por
natureza. É o que motiva a próxima camada: rubrica e LLM-as-judge para causa-raiz, decisão
e migração — os testes que julgam conteúdo onde o regex não alcança, fechando a pirâmide de
avaliação.
