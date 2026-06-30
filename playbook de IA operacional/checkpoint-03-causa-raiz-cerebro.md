# Checkpoint 03 — Causa-raiz da degradação no Cerebro

> Playbook de IA Operacional da Aegis — item nº 3 (domínio SRE).
> O Cerebro (indexação/busca) começou a devolver buscas lentas e resultados
> parciais. O Sam Wilson levantou três artefatos (config, métricas, logs) e escalou.
> Pedido: um prompt de RCA reusável que raciocine até a **causa-raiz**, não o sintoma.

---

## 1. Decisões de método (o "porquê" antes do "o quê")

### Framework: RISE como base + Chain-of-Thought explícito + Step-Back

A tarefa é **procedural e diagnóstica de alto fôlego**: recebe três artefatos
concretos de fontes diferentes, exige uma sequência de raciocínio (correlacionar →
encadear causa → comprovar) e tem critério de validação claro. É o cenário ideal do
**R-I-S-E** — por definição, o **Input** do RISE são "dados concretos (logs,
métricas, configs)" e o **Steps** é o que "transforma o prompt em processo
reproduzível" (`fw-rise`). Mapeamento:

| Componente | No nosso prompt |
|---|---|
| **Role** | SRE/engenheiro de confiabilidade sênior conduzindo RCA, que não para no sintoma |
| **Input** | Os três artefatos: `{{config}}` + `{{metricas}}` + `{{logs}}` (delimitados) |
| **Steps** | Step-back → linha do tempo → sintomas por fonte → cadeia causal → evidência → fatores → hipótese alternativa → confiança/lacunas |
| **Expectation** | `# Critério de pronto`: cada elo com sinal das 3 fontes, sintoma≠causa, mitigação+correção, hipótese alternativa avaliada, confiança declarada |

Aplico a **regra de combinação** (base simples + elementos justificados):

- **+ Chain-of-Thought explícito.** O CoT é a técnica de referência para **exatamente
  esta tarefa** — analisar logs, identificar a causa-raiz, correlacionar timestamps e
  explicar por que o sistema falhou com base nos números (`tec-cot`) — e **definir os
  tópicos de raciocínio** (CoT explícito) rende "de 20% a 80%" sobre deixar o modelo
  raciocinar sozinho. Os meus `# Passos` são esse CoT explícito embutido no Steps do RISE.
- **+ Step-Back (passo 0).** O Step-Back "força uma reflexão prévia para evitar viés ou
  alucinação", carregando os conceitos do subsistema "fresquinhos" antes da análise
  (`tec-step-back`). É decisivo aqui: o sintoma **mais visível** é a busca lenta
  (caminho de leitura), mas a **origem** está no caminho de escrita (job de reindex
  travado saturando o heap compartilhado). Sem o passo atrás, o modelo tende a
  ancorar no efeito. Com ele, eu primo o raciocínio sobre **recursos compartilhados
  e acoplamento read/write**, que é onde a causa mora.

**Por que não os outros frameworks.** TAG (não há um KPI de negócio no centro — há
um diagnóstico técnico), BAB (não é transformação de estado A→B), RTF puro (a saída
exige raciocínio multi-etapa, não é "previsível e direta"), CARE puro (não há um
exemplo-gabarito de RCA para ancorar — e cada incidente é diferente; aqui o que
guia é o **processo**, não um exemplar). **RISE+CoT+Step-Back** é o mínimo necessário,
máximo suficiente.

**Por que não Chain-of-Verification dentro do prompt.** A CoVe é poderosa para
output que vira ação em produção, mas seu valor vem do **isolamento em outra janela
de contexto** (4 passos / múltiplos chats) — é *prompt-chaining*, não cabe num único
prompt reusável. Fica como **gancho de avaliação** (ver §4), e embuti só o espírito
dela como regra barata: *toda causa precisa de sinal; avalie uma hipótese alternativa*.

### Parametrização (regra de método #1)

Três parâmetros obrigatórios — um por fonte de sinal, espelhando os três artefatos
do enunciado: `{{config}}`, `{{metricas}}`, `{{logs}}`. Mantê-los separados (em vez
de um `{{artefatos}}` único) reforça no modelo que ele deve **cruzar fontes**, não
ler um bloco só. Três opcionais (`{{sistema}}`, `{{janela}}`, `{{contexto_extra}}`)
tornam o item **genérico**: serve a qualquer degradação da plataforma, não só ao
Cerebro/Elasticsearch.

### "Trate como produção": sanitização antes do modelo externo

O enunciado pede para decidir o que tratar antes de mandar a um modelo externo
(ponta da Natasha Romanoff, segurança/compliance). Os artefatos carregam **tenants**,
**topologia interna** (`cerebro-node-3`), **URL de registry** e **nomes de índice**
que podem refletir dado de cliente. Decisão: **anonimizar tenants, remover
hostnames/IPs/URLs internos, confirmar que os logs não trazem payload/PII e preferir
provedor com não-treinamento / retenção zero**. O prompt assume **entrada já
sanitizada** (declarado na seção `# Entrada` e no README do item).

### Meta-prompting / CRAFT (regra de método #2)

Construído via **CRAFT** (humano no controle): dirigi um modelo forte com um
meta-prompt descrevendo a dor (RCA cruzando 3 fontes, chegar à causa e não ao
sintoma), a natureza dos artefatos e a exigência de evidência por elo. O modelo
gerou o rascunho; **a curadoria é minha** (§4). O meta-prompt não entra na
biblioteca — só o prompt final. **Criar com o caro (Opus 4.8), executar com o
barato (Sonnet/Haiku).**

### Versionamento/organização

Mesmo padrão de catálogo: **Markdown + front-matter**, por **domínio (`sre/`)**,
pasta por prompt → `sre/analise-causa-raiz/prompt.md` + `README.md`.

---

## 2. Entregável — o prompt parametrizável

Caminho no repositório: `sre/analise-causa-raiz/prompt.md` (front-matter + corpo
completo lá). O corpo do prompt segue a estrutura RISE:

- **# Papel** — SRE sênior de RCA, rigoroso, não para no sintoma.
- **# Tarefa** — chegar à causa-raiz cruzando config × métricas × logs; mitigação
  imediata + correção definitiva.
- **# Entrada** — três artefatos delimitados (`<config>`, `<metricas>`, `<logs>`),
  já sanitizados; "trabalhe só com o que está aqui".
- **# Passos** — CoT explícito com **Step-Back no passo 0**, depois linha do tempo,
  sintomas por fonte, cadeia causal, evidência por elo, fatores, hipótese
  alternativa, confiança/lacunas.
- **# Formato da saída** — veredito de 1 linha + Linha do tempo + Causa-raiz (cadeia
  + evidência) + Sintoma×causa + Fatores + Ações (🔴 imediata / 🟢 definitiva) +
  Confiança/lacunas.
- **# Regras** — anti-alucinação (toda causa ancorada em sinal; sem evidência →
  "coletar X"), sintoma≠causa, não inventar.
- **# Critério de pronto (Expectation)** — fecha o 4º componente do RISE.

> O conteúdo integral está em `sre/analise-causa-raiz/prompt.md` para não duplicar
> a fonte da verdade (DRY de prompt).

---

## 3. Execução (real, verificada)

**Modelo de execução:** `claude-sonnet-4-6` (criar caro, executar barato).
**Execução manual verificada** — output **real** do modelo para o pacote de
artefatos do enunciado (config + métricas + logs do Cerebro), colado verbatim.

**Parâmetros usados:** `{{config}}` = `cerebro.yaml`; `{{metricas}}` = tabela de 5
pontos 08:00→10:00; `{{logs}}` = trecho do `cerebro-node-3`; `{{sistema}}` =
`Cerebro — indexação e busca (Elasticsearch/JVM)`; `{{janela}}` = `08:00–10:00 UTC,
buscas lentas e resultados parciais`; `{{contexto_extra}}` = `reindex noturno (02:00)
deveria terminar ~03:30`.

```
Veredito: O reindex job agendado (que rodou muito além de sua duração esperada)
competiu por heap/threads de escrita com a indexação normal, disparando throttling
progressivo que, junto à pressão de memória, acabou estourando o circuit breaker e
derrubando também as buscas — a causa-raiz é a sobrecarga de escrita do reindex
prolongado, não a degradação de busca em si.

Linha do tempo
- 02:00 → reindex job [88123] inicia, duração esperada ~90min / fim previsto ~03:30
  (config: reindex_job.avg_duration_min=90)
- 08:02 → job a 38% — já bem além do prazo esperado (log: LoggingTaskListener,
  created 3.8M/10M)
- 08:41 → ponto de virada: indexação começa a ser throttled por escrita de segmento
  não acompanhar o ritmo (log: IndexingMemoryController "segment writing can't keep
  up"), coincidindo com início da subida de heap_used_pct (61→68% entre 08:00 e
  08:30, métrica)
- 09:03–09:51 → fila de escrita sobe de 150/200 para 188/200 (log: ThreadPool queue),
  heap sobe 79→88% e search_p99_ms dispara de 2300→4100ms (métrica)
- 09:58 → fila de escrita satura (200/200, rejeição de bulk), circuit breaker do
  parent atinge 96% e dispara, busca retorna parcial (11/12 shards) (log:
  EsRejectedExecutionException + CircuitBreakingException)
- 10:01–10:05 → CircuitBreakingException confirmada, rejeição de 1284 bulks em 5min,
  falhas totais de shard em buscas (log), search_p99_ms=6700ms e
  heap_used_pct=94% (métrica)

Causa-raiz (gatilho → propagação → efeito)
1. Gatilho: reindex job agendado às 02:00 não terminou no prazo esperado — ainda em
   41% às 09:58, muito além de avg_duration_min: 90 (config: reindex_job.avg_duration_min=90
   vs log: 09:58:44 created 4.1M/10M, ETA unknown).
2. Propagação 1 — pressão de escrita: o reindex prolongado mantém carga de indexação
   alta concorrente com tráfego normal; segment writing não acompanha, throttling de
   indexação é ativado (log: 08:41:07 IndexingMemoryController "segment writing can't
   keep up"), e indexed_docs_per_s sobe de 4200→12400 no período (métrica: 08:00→10:00),
   confirmando volume de escrita anormalmente alto.
3. Propagação 2 — pressão de heap: GC jovem/antigo cada vez mais longos e frequentes
   (620ms→1.1s→1.8s, log: JvmGcMonitorService) acompanham heap_used_pct subindo de
   61%→94% (métrica), evidenciando que a memória usada pela indexação/buffers está
   consumindo o heap compartilhado com buscas — heap fixo em jvm_heap: 8g (config) sem
   folga para os dois caminhos simultâneos.
4. Propagação 3 — saturação de filas: write thread pool queue sobe 150→188→200/200 com
   rejeições (log: ThreadPool 09:03, 09:51, 09:58), e o circuit breaker do parent
   (limite implícito no heap de 8g) é atingido e tripado (log: HierarchyCircuitBreakerService
   09:31 86% → 09:58 96% tripped).
5. Efeito final: buscas degradam e falham — search_p99_ms 850→6700ms (métrica),
   resultados parciais e CircuitBreakingException, cache hit ratio cai 74%→29%
   (métrica + log: query cache eviction rate spiking) porque o heap pressionado força
   eviction do cache de query, não porque a busca em si seja a origem do problema.

Sintoma × causa: a latência alta de busca (search_p99_ms crescente) e os erros de
circuit breaker/partial results são efeito visível, não causa — a origem é a contenção
de heap/threads gerada pelo reindex de escrita que não terminou no tempo esperado e
cresceu junto com a indexação normal.

Fatores contribuintes
- jvm_heap: 8g único, compartilhado entre indexação e busca/cache, sem isolamento de
  circuit breaker dedicado para reindex.
- query_cache.size_mb: 512 pequeno relativo à pressão de heap — facilita eviction
  agressiva quando heap aperta.
- Ausência de limite de duração/circuito de corte para o reindex job (config só define
  avg_duration_min informativo, não um timeout).

Ações
- 🔴 Mitigação imediata: cancelar/pausar o reindex task [88123] (ou throttle-lo
  manualmente) para liberar heap e a fila de escrita imediatamente — ataca o gatilho,
  não o sintoma de busca.
- 🟢 Correção definitiva: (1) definir timeout/circuit breaker dedicado para reindex
  jobs que excedam um múltiplo de avg_duration_min; (2) isolar recursos entre indexação
  em massa e tráfego de busca (ex.: throttle automático mais agressivo, thread pool/heap
  reservation separados, ou rodar reindex em índice/nó dedicado); (3) revisar
  query_cache.size_mb e o limite do circuit breaker do parent para dar mais folga
  durante picos de indexação.

Confiança e lacunas
- Confiança: alta para a cadeia reindex→pressão de heap/escrita→circuit
  breaker→degradação de busca, pois todos os elos têm evidência cruzada (config +
  métrica + log) no mesmo nó (cerebro-node-3).
- Hipótese alternativa avaliada: poderia ser um pico orgânico de tráfego de indexação
  externo (não o reindex). Descartada como causa primária porque o LoggingTaskListener
  mostra o reindex [88123] ainda rodando e atrasado durante toda a janela (38%→41%
  entre 08:02 e 09:58), coincidindo exatamente com a curva de degradação — mas não dá
  para excluir totalmente contribuição de tráfego externo concorrente.
- Lacunas a coletar: coletar breakdown de indexed_docs_per_s por origem (reindex vs.
  tráfego normal) para confirmar proporção; coletar logs dos outros 11 nós do cluster
  para verificar se o problema é local ao node-3 ou distribuído; coletar configuração
  de circuit breaker (indices.breaker.total.limit) que não está no cerebro.yaml
  fornecido, para confirmar o limiar exato de 8gb citado nos logs.
```

---

## 4. Curadoria (a "assinatura" no item)

- **O risco central que blindei: parar no sintoma.** O sinal mais alto é a busca
  (p99 850→6700ms, resultado parcial 11/12 shards) — caminho de **leitura**. Mas a
  origem está na **escrita**. Por isso o passo 0 (Step-Back) força o modelo a pensar
  em **recursos compartilhados e acoplamento read/write** *antes* de olhar os dados,
  e a regra "sintoma ≠ causa" + "rastreie para trás" o impede de entregar "a busca
  está lenta" como se fosse causa.
- **Evidência por elo, das três fontes.** A cadeia só vale se cada passo citar um
  sinal real — e de fontes diferentes, senão o modelo "prova" tudo com a métrica
  mais óbvia. A regra exige `config:` + `métrica:@horário` + `log:linha` por elo.
- **Hipótese alternativa obrigatória.** Embuti o espírito do Chain-of-Verification
  numa regra barata: avaliar ≥1 explicação concorrente e dizer por que cai. Reduz o
  viés de fixar na primeira leitura (ex.: "é só falta de heap, sobe pra 16g" ignora
  que o gatilho é o job travado).
- **Mitigação que ataca a origem, não maquia o sintoma.** Exigi separar 🔴 imediata
  (aliviar a cadeia) de 🟢 definitiva (impedir recorrência) — diferença que importa
  no plantão.
- **Sanitização declarada** (tenants, topologia, registry, índice; provedor com
  não-treino). É o "trata como produção" do enunciado, ancorado na ponta de
  compliance (Natasha).

### Causa-raiz prevista (minha leitura — a validar contra a execução real)

> Registro aqui **minha previsão** (curadoria), explicitamente **não** como output
> de modelo. Serve para conferir a §3 quando a execução real voltar.

**Cadeia provável:** o **job de reindex** (agendado 02:00, `avg_duration_min: 90`,
deveria terminar ~03:30) **travou/regrediu** — às 10:00 ainda em **41%** (`log
08:02→09:58: created 4.1M/10M, ETA unknown`) → carga de **escrita** sustentada
estoura o buffer de indexação (`IndexingMemoryController: throttling shard 7`) e
**enche a write thread pool** (`150→188→200/200, EsRejectedExecutionException`, 1284
bulks rejeitados/5min) → a pressão consome o **heap único de 8g** (`métrica
heap 61%→94%`; GC `old` de 1.1s→1.8s) → o **circuit breaker pai dispara a 96%**
(`HierarchyCircuitBreakerService` → `CircuitBreakingException: Data too large`),
que recusa **tanto indexação quanto busca** → busca estoura o timeout de 5s e
retorna **parcial** (`11/12 shards`, depois `all shards failed`); o **query cache**
é despejado sob pressão de heap (`hit 74%→29%`), encarecendo cada query e realimentando
a latência (p99 850→6700ms). **Causa-raiz:** o **reindex travado saturando o heap e a
fila de escrita**, acoplando escrita e leitura pelo heap/circuit breaker
compartilhados — **não** "a busca está lenta" nem "falta heap" isolado.
**🔴 Imediata:** pausar/throttlar o reindex para aliviar heap → o circuit breaker
relaxa e a busca volta. **🟢 Definitiva:** rodar o reindex com throttle e fora do
pico, e/ou aumentar heap / reduzir shards / segregar recursos de escrita e leitura.

### Verificação da execução real (não foi simulação) — ✅ item entregue

A saída da §3 é a **execução manual verificada** no `claude-sonnet-4-6`. O teste real
**confirmou a previsão em todos os critérios de pronto** — o item está entregue, sem
necessidade de ajuste no prompt:

- ✅ **Causa-raiz, não sintoma.** O veredito já abre com "a causa-raiz é a sobrecarga
  de escrita do reindex prolongado, **não a degradação de busca em si**". O Step-Back
  do passo 0 cumpriu o papel: o modelo não ancorou no p99 (efeito mais visível) e
  rastreou até o gatilho de escrita. Era o risco nº 1 do checkpoint e o prompt o segurou.
- ✅ **Evidência cruzada por elo.** Cada passo da cadeia cita fonte explícita —
  `config: avg_duration_min=90`, `métrica: heap 61%→94%`, `log: IndexingMemoryController
  / ThreadPool / HierarchyCircuitBreakerService`. A regra de "sinal por elo, fontes
  diferentes" pegou: nenhum elo provado só pela métrica óbvia.
- ✅ **Sintoma × causa** explicitado em seção própria (latência/circuit breaker = efeito).
- ✅ **Mitigação ataca a origem** (pausar o reindex task [88123]), com 🔴 imediata
  separada da 🟢 definitiva (timeout no reindex, isolamento read/write, tuning do breaker).
- ✅ **Hipótese alternativa avaliada** (pico orgânico de indexação externa) e descartada
  com evidência (o reindex aparece atrasado por toda a janela), sem fingir certeza total.
- ✅ **Confiança declarada + lacunas acionáveis.**

**Divergências vs. minha previsão — todas benignas, nenhuma exige mudança no prompt:**
- O modelo foi **mais fino na cadeia do cache**: explicou que o `hit 74%→29%` é *efeito*
  da eviction sob pressão de heap (não causa) — exatamente o tipo de "sintoma≠causa"
  que o prompt pede, e que eu só havia esboçado.
- **Lacuna que eu não havia previsto e valida o anti-alucinação:** o modelo notou que o
  limiar do circuit breaker (`indices.breaker.total.limit`) **não está no `cerebro.yaml`
  fornecido** e pediu para coletá-lo, em vez de inventar o valor. É a regra "sem
  evidência → coletar X" funcionando na prática — o sinal mais forte de que o item é
  confiável para o plantão.

### Ganchos para os próximos checkpoints (avaliação)

Item pronto para o módulo de avaliação: **rubrica** (causa-raiz≠sintoma? evidência
das 3 fontes por elo? mitigação na origem? hipótese alternativa? confiança/lacunas?),
**golden-answer** no promptfoo contra a RCA de referência, e **Chain-of-Verification**
como passo extra antes de qualquer ação guiada por esta RCA em produção.
