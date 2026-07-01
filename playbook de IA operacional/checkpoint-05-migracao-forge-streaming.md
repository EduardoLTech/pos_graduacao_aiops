# Checkpoint 05 — Migrando o Forge de lote para tempo real

> Playbook de IA Operacional da Aegis — item nº 5 (domínio data).
> O Forge (pipeline de dados) roda em lote (job de hora em hora); o Bruce Banner quer
> migrá-lo para orientado a eventos (consumir o Relay e processar quase em tempo real).
> A mudança é grande demais para um prompt só. Pedido: **uma cadeia de prompts**
> encadeados (um diagnostica, o próximo planeja, o seguinte detalha), cada elo recebendo
> a saída do anterior — em passos reversíveis, sem virada única.

---

## 1. Decisões de método (o "porquê" antes do "o quê")

### Técnica central: Prompt Chaining (+ Least-to-Most no elo de planejamento)

O enunciado é explícito: *"quebrar a migração em etapas e resolver uma de cada vez…
cada etapa usando o resultado da anterior… Isso se chama encadear prompts… A entrega
não é um prompt monolítico; é essa cadeia"*. Isso é **prompt chaining** por definição —
a técnica para quando a tarefa tem **mais de uma etapa cognitiva** (aqui: diagnosticar,
planejar, detalhar), com cada prompt tendo **uma responsabilidade só**, **output
verificável** e **formato definido** para o próximo consumir.

O enunciado já sugere a cadeia de três elos ("um prompt diagnostica o estado atual, o
próximo propõe o passo a passo, o seguinte detalha o plano executável e reversível") —
adotei exatamente essa divisão:

| Elo | Responsabilidade única | Consome | Produz | Framework/técnica |
|---|---|---|---|---|
| 1 | Diagnosticar o estado atual (sem propor migração) | estado atual + dependentes + restrições | mapa: fluxo, contratos, pontos frágeis, pontos de corte | RISE |
| 2 | Planejar a migração em fases ordenadas e reversíveis | saída do Elo 1 | plano faseado, dependência mapeada, sem big-bang | RISE + **Least-to-Most** |
| 3 | Detalhar **uma** fase como runbook executável/reversível | saída do Elo 2 + fase-alvo | pré-checagens, passos, gate, rollback, sucesso | RISE (roda em loop) |

**Por que Least-to-Most no Elo 2 (e não em toda a cadeia).** Planejar uma migração é
**decompor por dependência, do mais fundamental ao mais complexo** — o caso-modelo do
least-to-most (planejamento multi-etapa em que a ordem importa, tipo migração de
aplicação). Mas o least-to-most é *prompt chaining aplicado à decomposição*: ele resolve
**um** dos elos (o planejamento), não substitui a cadeia inteira. Por isso a cadeia é
**prompt chaining**, e o Elo 2 usa a decomposição least-to-most por dentro.

**Por que RISE como base de cada elo.** Cada elo, isolado, é uma tarefa procedural com
input concreto e critério de pronto próprio — o encaixe do RISE. Dentro da cadeia,
continuo usando os frameworks já conhecidos em cada elo, como manda a técnica.

**Por que não um Tree-of-Thought (como no Checkpoint 04).** Lá a tarefa era **escolher**
entre caminhos concorrentes (decisão "depende"). Aqui o caminho já foi decidido (ir para
event-driven); o desafio é **executar uma sequência** com dependências — território de
chaining/least-to-most, não de ramificação.

### Os gates entre elos (o controle de qualidade da cadeia)

O ponto frágil de qualquer cadeia é o **erro em cascata**: se o Elo 1 erra o diagnóstico,
o Elo 2 planeja sobre base errada e o Elo 3 detalha o errado. Por isso embuti a lógica de
**gate** — um checkpoint humano entre elos: valida-se a saída de um elo **antes** de
alimentar o próximo. É o mesmo conceito de quality gate de pipeline CI/CD. Cada prompt
termina com um **Critério de pronto** justamente para tornar esse gate objetivo.

### Parametrização (regra de método #1)

Cada elo é parametrizável e o parâmetro-chave é **a saída do elo anterior**:
`{{estado_atual}}`/`{{dependentes}}`/`{{restricoes_migracao}}` (Elo 1) →
`{{diagnostico}}` (Elo 2) → `{{plano}}` + `{{fase_alvo}}` (Elo 3). Isso torna a cadeia
reusável para **qualquer** migração incremental (não só o Forge), trocando só a entrada
do primeiro elo. Os parâmetros de contexto (`{{sistema}}`, `{{alvo}}`,
`{{contexto_execucao}}`) são opcionais.

### Meta-prompting / CRAFT (regra de método #2)

Cada elo foi gerado via **CRAFT** (humano no controle): dirigi um modelo forte com um
meta-prompt por elo, descrevendo a responsabilidade única daquele passo, o que ele
recebe do anterior e o formato de saída que o próximo precisa. O modelo gerou os
rascunhos; **a curadoria é minha** (§4). Os meta-prompts não entram na biblioteca — só os
três prompts finais. **Criar com o caro (Opus 4.8), executar com o barato (Sonnet/Haiku).**

### Versionamento/organização

Domínio **`data`** (pipeline do Forge, ponta do Bruce Banner). A cadeia mora numa pasta
única com um prompt por elo + README:
`data/migracao-incremental-encadeada/{prompt-1-diagnostico.md, prompt-2-plano.md,
prompt-3-detalhamento.md, README.md}`. O front-matter de cada elo marca `cadeia`, `elo`,
`consome` e `produz` — o versionamento passa a tratar a cadeia como uma unidade.

---

## 2. Entregável — a cadeia de prompts parametrizáveis

Caminho no repositório: `data/migracao-incremental-encadeada/` (os três prompts + README
com o conteúdo integral). Resumo de cada elo:

- **Elo 1 — Diagnóstico (`prompt-1-diagnostico.md`).** RISE. Recebe o estado atual, os
  dependentes e as restrições; devolve o mapa (fluxo, contratos por dependente, pontos
  frágeis ancorados, o que preservar, candidatos a ponto de corte). Regra dura: **só
  diagnostica, não propõe migração**.
- **Elo 2 — Plano faseado (`prompt-2-plano.md`).** RISE + Least-to-Most. Recebe o
  diagnóstico; decompõe em fases ordenadas por dependência, cada uma com **coexistência**
  (antigo+novo convivendo), **reversão** e **gate de avanço**. Regra dura: **sem
  big-bang; toda fase reversível; só o plano, não a execução**.
- **Elo 3 — Runbook da fase (`prompt-3-detalhamento.md`).** RISE, roda **em loop** (uma
  vez por fase). Recebe o plano + a fase-alvo; devolve pré-checagens, passos, **gate de
  validação**, **rollback** e critério de sucesso + impacto nos dependentes. Regra dura:
  **uma fase só; sempre reversível; gate antes de avançar**.

> O conteúdo integral dos três prompts está em `data/migracao-incremental-encadeada/`
> para não duplicar a fonte da verdade (DRY de prompt).

---

## 3. Execução (real, verificada)

> **Status: execução manual verificada.** Os três elos foram rodados em cadeia; cada elo
> passou no seu gate e a saída de um alimentou o próximo. Outputs reais colados verbatim
> ao fim desta seção.

**Modelo de execução:** `claude-sonnet-4-6`.

### Como rodar a cadeia (elo a elo, com gate entre eles)

Uma conversa por execução; valide a saída de cada elo antes de seguir.

**➊ Elo 1 — Diagnóstico.** Cole o corpo do `prompt-1-diagnostico.md` (do primeiro `#` em
diante, sem front-matter) e preencha:

- `{{sistema}}` = `Forge — pipeline de dados e data warehouse da Aegis; transforma o telemetry em tabela consultável.`
- `{{estado_atual}}` =
  ```
  Forge hoje:
  - ingestão: um job em cron acorda a cada 60min (o "forge-batch-ingest")
  - transformação: 14 etapas de processamento encadeadas (em Spark), ~40min no total
  - destino: grava em tabelas no data warehouse, particionadas por hora
  - ponto frágil: se um lote falha, o próximo acumula o dobro de volume
  ```
- `{{dependentes}}` =
  ```
  - Sentinel: lê as tabelas agregadas do Forge
  - Cerebro: indexa os eventos transformados pelo Forge
  - Relatórios de billing da Pepper: rodam de madrugada sobre as tabelas do Forge
  ```
- `{{restricoes_migracao}}` =
  ```
  - consumir do Relay continuamente, processando em pequenos blocos no lugar do lote de 1h
  - manter quem depende do Forge funcionando durante a transição
  - nada de virada única (big-bang): migração em passos e com volta atrás (reversível)
  ```

> **🚦 Gate 1:** o mapa reflete o fluxo real (cron 60min → 14 etapas Spark ~40min →
> tabelas particionadas por hora), os três dependentes com seus contratos, e o ponto
> frágil do dobro-de-volume? Se sim, siga.

**➋ Elo 2 — Plano faseado.** Cole o corpo do `prompt-2-plano.md`; em `{{diagnostico}}`
cole **a saída do Elo 1** (ou, na mesma conversa, refira "o mapa acima"); repita o
`{{restricoes_migracao}}` acima e informe:

- `{{alvo}}` = `Forge consumindo o Relay continuamente e processando em pequenos blocos, quase em tempo real, no lugar do lote de 1h.`

> **🚦 Gate 2:** há ≥3 fases ordenadas por dependência, cada uma com coexistência,
> reversão e gate de avanço, e nenhuma é big-bang? Se sim, siga.

**➌ Elo 3 — Runbook da fase.** Cole o corpo do `prompt-3-detalhamento.md`; em `{{plano}}`
cole **a saída do Elo 2**, e informe:

- `{{fase_alvo}}` = `Fase 1` (repetir o elo trocando a fase até detalhar todas)
- `{{contexto_execucao}}` = `nenhum` (ou o stack real: orquestrador, warehouse, ferramenta de deploy)

> **🚦 Gate 3:** o runbook da fase tem pré-checagens, passos com efeito, gate verificável,
> rollback coerente com o plano e critério de sucesso + impacto nos dependentes?

### Outputs reais (verbatim)

**➊ Elo 1 — Diagnóstico do estado atual:**

```
 Fluxo atual
  a. ingestão → cron dispara o job "forge-batch-ingest" a cada 60min
  b. transformação → 14 etapas encadeadas em Spark, ~40min de processamento total por lote
  c. gravação → grava nas tabelas do data warehouse, particionadas por hora
- Dependentes

┌───────────────────────┬────────────────────────────┬───────────────────────────────────────────────────────────────────┐
│      dependente       │       o que consome        │                          expectativa/SLA                          │
├───────────────────────┼────────────────────────────┼───────────────────────────────────────────────────────────────────┤
│ Sentinel              │ lê as tabelas agregadas    │ falta saber frequência/SLA de leitura do Sentinel                 │
├───────────────────────┼────────────────────────────┼───────────────────────────────────────────────────────────────────┤
│ Cerebro               │ indexa os eventos          │ falta saber frequência/SLA de indexação do Cerebro                │
│                       │ transformados              │                                                                   │
├───────────────────────┼────────────────────────────┼───────────────────────────────────────────────────────────────────┤
│ Pepper (relatórios de │ consome dados do Forge     │ roda de madrugada — janela específica, provável dependência de o  │
│  billing)             │ para relatórios            │ lote da hora anterior já estar consolidado                        │
└───────────────────────┴────────────────────────────┴───────────────────────────────────────────────────────────────────┘

(nota: <dependentes> lista Relay e Sentinel, mas Relay aparece na entrada como fonte a ser consumida na migração, não como dependente do Forge hoje; a seção <estado_atual> lista Sentinel, Cerebro e Pepper como quem depende do Forge — falta saber se Relay já é dependente hoje ou só entra como fonte na migração)

- Pontos frágeis
  - efeito cascata em falha: "se um lote falha, o próximo acumula o dobro de volume" — sem isolamento entre execuções, uma falha degrada a execução seguinte
  - cadência rígida de 60min cria lote único e grande (~40min de processamento) — pouca margem entre fim do processamento e próximo disparo
  - pipeline de 14 etapas encadeadas em Spark — falta saber se há checkpoint/retomada intermediária entre etapas, ou se falha em qualquer etapa exige reprocessar o lote inteiro
  - Pepper roda de madrugada consumindo dados do Forge — falta saber a defasagem tolerada entre a última ingestão do dia e a execução do relatório
- Crítico preservar
  - disponibilidade e consistência das tabelas agregadas para o Sentinel
  - disponibilidade dos eventos transformados para indexação do Cerebro
  - integridade e pontualidade dos dados que alimentam os relatórios de billing da Pepper (madrugada)
  - continuidade de consumo do Relay sem gaps ou duplicação durante a transição (restrição explícita)
  - capacidade de reverter qualquer passo da migração (restrição explícita: nada de big-bang, tem que poder voltar atrás)
- Candidatos a ponto de corte
  - ingestão (cron "forge-batch-ingest") | é o ponto de entrada isolado do restante do pipeline — pode ser substituído por consumo contínuo do Relay sem tocar nas 14 etapas de transformação nem no destino
  - as 14 etapas de transformação | encadeadas mas descritas como unidades distintas — candidatas a serem fatiadas/migradas em grupos, desde que se preserve o contrato de saída para o data warehouse
  - gravação no data warehouse | ponto de saída único e comum a todos os dependentes — isolar aqui permite trocar o que vem antes sem impactar Sentinel/Cerebro/Pepper, desde que o formato/particionamento das tabelas seja mantido
- falta saber: SLA/frequência de leitura do Sentinel e do Cerebro; se Relay já depende do Forge hoje ou é só fonte futura; se há checkpoints intermediários entre as 14 etapas Spark; janela de tolerância dos relatórios de billing da Pepper.
```

**➋ Elo 2 — Plano de migração faseado:**

```
Alvo em uma linha: substituir a ingestão em lote horário (cron "forge-batch-ingest") por consumo contínuo do Relay em pequenos blocos, mantendo as 14 etapas de transformação e a gravação no data warehouse compatíveis com Sentinel, Cerebro e Pepper, sem gaps/duplicação e sem virada única.

---
Fase 1 — Instrumentar o estado atual
- Objetivo: medir o que hoje é "falta saber": frequência/SLA de leitura do Sentinel, de indexação do Cerebro, janela de tolerância da Pepper, e se há checkpoint intermediário nas 14 etapas Spark. Sem essa base, nenhuma fase seguinte pode ter gate confiável.
- Depende de: nada.
- Coexistência: puramente observacional — nenhum comportamento do pipeline muda.
- Reversão: remover instrumentação; não há risco de estado a desfazer.
- Gate de avanço: SLA/frequência de Sentinel e Cerebro documentados, janela de tolerância da Pepper conhecida, e mapa de onde (se houver) o pipeline Spark pode ser retomado sem reprocessar tudo.

Fase 2 — Congelar o contrato de gravação no data warehouse
- Objetivo: tornar o formato e o particionamento por hora das tabelas gravadas um contrato explícito e estável, isolando os dependentes (Sentinel, Cerebro, Pepper) de qualquer mudança que venha antes na cadeia (ingestão/transformação).
- Depende de: Fase 1 (precisa saber o que cada dependente realmente espera do contrato).
- Coexistência: nenhuma mudança funcional ainda; apenas formalização/validação do contrato existente (ex.: testes de schema/particionamento contra o que já é produzido hoje).
- Reversão: contrato é só documentação/validação — reverter é descartar a validação, sem impacto operacional.
- Gate de avanço: contrato de saída (schema + particionamento) documentado e validado contra o comportamento atual, aceito como "o que não pode quebrar" pelas fases seguintes.

Fase 3 — Consumo contínuo do Relay em modo sombra
- Objetivo: introduzir um consumidor que lê o Relay continuamente em pequenos blocos, em paralelo ao cron "forge-batch-ingest", escrevendo em uma área isolada (não a tabela final) — sem afetar transformação nem gravação de produção.
- Depende de: Fase 2 (precisa saber contra qual contrato validar a paridade dos dados lidos).
- Coexistência: cron antigo continua sendo a única fonte real do DW; o novo consumo do Relay roda em sombra, comparando volume/conteúdo com o que o cron ingere.
- Reversão: desligar o novo consumidor do Relay; cron permanece intocado, zero impacto nos dependentes.
- Gate de avanço: consumo contínuo do Relay comprovadamente sem gaps/duplicação e equivalente (em conteúdo) ao que o cron ingeriria na mesma janela.

Fase 4 — Adaptar as 14 etapas de transformação a micro-blocos
- Objetivo: fazer as 14 etapas Spark operarem sobre os pequenos blocos vindos do Relay (Fase 3) em vez do lote horário de ~40min, produzindo saída equivalente à gravação atual — ainda em área isolada, sem substituir a gravação de produção.
- Depende de: Fase 3 (precisa de um fluxo de blocos validado como entrada).
- Coexistência: pipeline antigo (cron → 14 etapas → DW) segue gravando produção; pipeline novo (Relay → 14 etapas adaptadas) grava em paralelo numa área sombra para comparação bloco a bloco.
- Reversão: pausar o pipeline novo; produção continua servida integralmente pelo caminho antigo.
- Gate de avanço: saída do pipeline novo bate com o contrato da Fase 2 e é equivalente à saída do pipeline antigo para o mesmo intervalo de tempo, de forma consistente (não só num teste pontual).

Fase 5 — Corte da gravação com escrita dupla e flag
- Objetivo: passar a gravar as tabelas de produção do DW a partir do pipeline novo, mantendo o cron/pipeline antigo ativo como fallback controlado por feature flag.
- Depende de: Fase 4 (pipeline novo já provado equivalente).
- Coexistência: escrita dupla temporária (antigo e novo gravam, mas apenas um é "fonte da verdade" por flag) — Sentinel, Cerebro e Pepper continuam lendo da tabela oficial sem saber da troca por trás da flag.
- Reversão: virar a flag de volta para o pipeline antigo como fonte da verdade; nenhuma mudança de schema/particionamento foi feita, então o rollback é imediato.
- Gate de avanço: janela de operação com o pipeline novo como fonte, cobrindo pelo menos um ciclo completo de leitura de Sentinel, indexação de Cerebro e uma execução de madrugada da Pepper, sem incidentes e dentro dos SLAs medidos na Fase 1.

Fase 6 — Descomissionar o cron "forge-batch-ingest"
- Objetivo: desligar definitivamente o job de ingestão horária e o caminho antigo (ingestão cron + trecho correspondente das 14 etapas), deixando o consumo contínuo do Relay como único caminho.
- Depende de: Fase 5 (pipeline novo consolidado como fonte de produção por período suficiente).
- Coexistência: não há mais convivência — este é o ponto em que o antigo sai de cena; por isso é a última fase e só acontece depois de todas as anteriores terem gate fechado.
- Reversão: reativar o cron e a flag da Fase 5 apontando para o caminho antigo (mantido "frio" por um período de segurança antes de ser removido de vez).
- Gate de avanço: nenhuma dependência (Sentinel, Cerebro, Pepper) reportando problema após N ciclos completos com o cron desligado; cron mantido pausado (não removido) até esse período de segurança expirar.

---
Ordem recomendada: 1 → 2 → 3 → 4 → 5 → 6

Riscos de sequência:
- Pular a Fase 1 (SLAs) faz os gates das fases seguintes serem arbitrários — sem saber o que Sentinel/Cerebro/Pepper toleram, não dá para provar equivalência.
- Trocar Fase 2 e Fase 3 (validar contrato depois de já estar consumindo Relay) arrisca descobrir tarde que o formato/particionamento não é compatível, forçando retrabalho nas etapas 3 e 4.
- Adaptar as 14 etapas (Fase 4) antes de validar o consumo do Relay (Fase 3) mistura dois riscos ao mesmo tempo — dificulta isolar se um problema é da fonte ou da transformação.
- Fazer o corte de gravação (Fase 5) sem escrita dupla/flag equivale a big-bang — perde a reversibilidade exigida.
- Desligar o cron (Fase 6) antes de cobrir um ciclo completo de Pepper (madrugada) arrisca quebrar justamente o dependente mais sensível a defasagem, sem chance de rollback rápido se o cron já tiver sido removido.
```

**➌ Elo 3 — Runbook executável da Fase 1:**

```
Fase: Fase 1 — Instrumentar o estado atual
Pré-condição: nenhuma

Pré-checagens
- [ ] Confirmar que o cron "forge-batch-ingest" está saudável agora (última execução ok, sem atraso, sem erro nas últimas N janelas) — instrumentar um estado já degradado gera baseline inválida.
- [ ] Confirmar acesso de leitura (logs/métricas/configuração) a Sentinel, Cerebro e Pepper, sem precisar de mudança de permissão nos três sistemas.
- [ ] Confirmar que as 14 etapas Spark expõem algum rastro de execução por etapa (log, métrica ou checkpoint), mesmo que não estruturado — é o que será inspecionado no passo 4.
- [ ] Validar com os donos de Sentinel, Cerebro e Pepper que instrumentação observacional (leitura de logs/métricas, sem escrita) não tem restrição de acesso ou custo (ex.: egress de logs, cota de API).

Execução
1. Medir frequência e SLA de leitura do Sentinel: identificar de quanto em quanto tempo ele lê o DW e qual atraso ele tolera antes de considerar dado "stale" → produz um número (ex.: lê a cada X min, tolera Y min de atraso).
2. Medir frequência/SLA de indexação do Cerebro: identificar o intervalo entre gravação no DW e a indexação, e se há reprocessamento/retry em caso de atraso → produz o mesmo tipo de número para o Cerebro.
3. Medir a janela de tolerância da Pepper: identificar o horário da execução de madrugada, o intervalo de dados que ela consome e quanto atraso/gap ela absorve sem falhar → produz a janela crítica (a mais sensível dos três, segundo o plano).
4. Mapear as 14 etapas Spark em busca de checkpoint intermediário: para cada etapa, registrar se existe ponto de retomada sem reprocessar do zero, ou se hoje é tudo-ou-nada → produz o mapa "onde dá para retomar" que a Fase 4 vai precisar.
5. Consolidar os quatro achados (SLA Sentinel, SLA Cerebro, janela Pepper, mapa de checkpoint) em um único documento de referência, versionado, acessível a quem for validar os gates das próximas fases.
6. Confirmar com os três times donos (Sentinel, Cerebro, Pepper) que os números medidos batem com a expectativa deles — instrumentação só vale se validada por quem conhece o sistema, não só pelo dado observado.

Nenhum passo acima altera o pipeline de ingestão, transformação ou gravação — é 100% leitura/observação, coerente com a Coexistência declarada da fase.

🚦 Gate de validação
- Medir: os quatro artefatos existem e estão documentados — (a) SLA/frequência de leitura do Sentinel, (b) SLA/frequência de indexação do Cerebro, (c) janela de tolerância da Pepper, (d) mapa de checkpoint das 14 etapas Spark.
- Avança se: os quatro itens estão documentados E confirmados pelos respectivos times donos como corretos/completos.
- Se falhar (falta algum item, ou time dono não confirma): → Rollback

Rollback
1. Remover/desligar a instrumentação adicionada (scripts de coleta, dashboards temporários, exports de log) — não há estado de dado a desfazer, pois nada foi escrito em produção.
2. Descartar o documento de consolidação se os números não foram confirmados pelos times donos, para não deixar um "contrato" implícito baseado em dado não validado.
3. Cron e pipeline atual continuam intocados durante todo o processo — não há necessidade de nenhuma ação de reversão sobre eles.

✅ Critério de sucesso
- Documento único, versionado e confirmado pelos times donos, contendo: SLA/frequência de leitura do Sentinel, SLA/frequência de indexação do Cerebro, janela de tolerância da Pepper, e mapa de retomada das 14 etapas Spark.
- Esse documento é aceito como base objetiva para os gates das Fases 2 a 6 (nenhum gate futuro pode ser definido sem referenciar estes números).

Impacto nos dependentes: nulo — Sentinel, Cerebro e Pepper continuam operando exatamente como antes; nenhuma leitura, escrita ou timing foi alterado, apenas observado.
```

---

## 4. Curadoria (a "assinatura" no item)

- **O risco central que blindei: o prompt monolítico.** A tentação é um prompt "planeje a
  migração do Forge". A cadeia força **uma responsabilidade por elo** e um **formato de
  saída pensado para o próximo elo ler** — é o que faz a resposta deixar de ser genérica.
  Cada prompt tem a regra "não faça o trabalho do próximo elo" (Elo 1 não propõe migração;
  Elo 2 não detalha execução; Elo 3 só uma fase).
- **Gates contra erro em cascata.** O maior perigo da cadeia (e do least-to-most) é o erro
  do elo 1 contaminar 2 e 3. Por isso cada elo termina com **Critério de pronto** e o
  roteiro tem um **gate humano** explícito entre elos. Sem passar no gate, não avança.
- **Reversibilidade e coexistência em primeiro plano.** As restrições do enunciado ("sem
  big-bang", "manter dependentes funcionando", "poder voltar atrás") viraram **campos
  obrigatórios** do Elo 2 (Coexistência + Reversão + Gate por fase) e do Elo 3 (Rollback
  + Impacto nos dependentes). Uma fase sem rollback está incompleta por regra.
- **Least-to-most só onde cabe.** Não espalhei a decomposição por toda a cadeia; concentrei
  no Elo 2, que é o de planejamento. Elo 1 é diagnóstico e Elo 3 é execução — usar
  least-to-most neles seria força bruta desnecessária.
- **Anti-alucinação.** Elo 1 e Elo 2 ancoram na entrada (`falta saber <X>` quando faltar
  dado); Elo 3 só aterra em comandos se houver `{{contexto_execucao}}` — sem isso, fica no
  nível de ação, para não inventar ferramenta/stack.

### Plano de migração previsto (minha leitura — a validar contra a execução real)

> Registro **minha previsão** (curadoria), explicitamente **não** como output de modelo.
> Serve para conferir a §3 quando a execução real voltar.

**Diagnóstico esperado (Elo 1):** ponto de corte natural entre **ingestão** (o cron que
lê o acumulado) e **transformação** (as 14 etapas Spark); os dependentes leem o
**destino** (tabelas por hora), então o contrato a preservar é a **tabela de saída**, não
o modo de processar. Ponto frágil (dobro de volume em falha) some quando a ingestão vira
contínua.

**Plano faseado esperado (Elo 2), do mais fundamental ao mais complexo:**
1. **Consumo em paralelo (shadow):** um novo consumidor lê o Relay continuamente e grava
   em tabelas-sombra, **sem** ninguém consumir ainda. Coexiste 100% com o batch. Reversão:
   desligar o consumidor.
2. **Transformação em micro-blocos:** portar as 14 etapas para rodar em blocos pequenos
   sobre o stream, escrevendo nas tabelas-sombra. Gate: paridade de resultado sombra × batch.
3. **Escrita dupla + validação:** o novo caminho passa a escrever na **mesma tabela** que
   o batch (ou tabela versionada), com reconciliação. Gate: dados batem por N ciclos.
4. **Virada de leitura dos dependentes (um por vez):** apontar Sentinel, depois Cerebro,
   depois o billing para o caminho novo — **um de cada vez**, cada um reversível. O billing
   por último (roda de madrugada, mais sensível e menos urgente).
5. **Desativar o batch:** só depois de todos os dependentes migrados e estáveis. Reversão:
   reativar o cron enquanto a escrita dupla ainda existir.

**Runbook esperado (Elo 3) para a Fase 1:** pré-checar Relay saudável e offsets;
subir o consumidor-sombra; **gate** = tabelas-sombra recebendo dados sem afetar o batch
nem os dependentes; rollback = desligar consumidor e descartar sombra; sucesso = sombra
populando em tempo real, zero impacto nos leitores atuais.

**O que a cadeia deve evitar (e o gate pega):** um plano que já na Fase 1 corte o batch
(big-bang), ou que vire todos os dependentes de uma vez, ou uma fase sem rollback.

### Verificação da execução real (não foi simulação) — ✅ item entregue

As três saídas da §3 são a **execução manual verificada** no `claude-sonnet-4-6`, rodada
em cadeia (saída de cada elo alimentando o próximo). Os três elos passaram nos critérios
de pronto — o item está entregue, sem necessidade de ajuste nos prompts:

- ✅ **Responsabilidade única respeitada em cada elo.** O Elo 1 **só diagnosticou** (não
  esboçou migração); o Elo 2 **só planejou** (nenhum comando/config); o Elo 3 detalhou
  **uma fase só** (Fase 1), sem antecipar as outras. A regra "não faça o trabalho do
  próximo elo" segurou nos três.
- ✅ **Formato de consumo funcionou de ponta a ponta.** A saída estruturada do Elo 1
  (candidatos a ponto de corte, `falta saber`) foi de fato consumida pelo Elo 2, e o
  plano do Elo 2 (com "Reversão" e "Gate de avanço" por fase) foi consumido pelo Elo 3,
  que reaproveitou a Coexistência e a Reversão declaradas. A cadeia fechou.
- ✅ **Anti-alucinação (`falta saber`) propagou como projeto, não como buraco.** O Elo 1
  marcou 4 lacunas (SLAs de Sentinel/Cerebro, janela da Pepper, checkpoints Spark) em vez
  de inventar números — e o Elo 2 **transformou essas lacunas na Fase 1 (Instrumentar)**,
  fechando o loop: o gate herdado virou a primeira coisa a resolver. Foi o comportamento
  mais forte da execução.
- ✅ **Reversibilidade e sem-big-bang em toda fase.** As 6 fases têm Reversão e Gate; o
  próprio Elo 2 listou "corte de gravação sem escrita dupla/flag equivale a big-bang —
  perde a reversibilidade" nos riscos de sequência. A regra dura pegou.
- ✅ **Elo 3 não inventou comandos.** Como `{{contexto_execucao}}` = `nenhum`, o runbook
  ficou no nível de ação ("medir frequência de leitura do Sentinel"), sem forjar
  ferramenta/stack — exatamente a regra condicional do prompt.
- ✅ **Contradição de entrada sinalizada, não engolida.** O Elo 1 percebeu a ambiguidade
  Relay-como-fonte vs. Relay-como-dependente e **pediu esclarecimento** em vez de assumir.

**Divergências vs. minha previsão — todas benignas e, em dois casos, melhores que a minha:**
- **O modelo abriu com uma fase de instrumentação que eu não previ.** Minha previsão
  começava direto no shadow; o modelo, guiado pelas lacunas do Elo 1, colocou "medir os
  SLAs" como Fase 1 — mais defensável, porque sem esses números os gates das fases
  seguintes seriam arbitrários (ele próprio disse isso nos riscos de sequência). Essa
  é a prova de que o gate/`falta saber` do Elo 1 realmente pilotou o Elo 2.
- **Congelar o contrato do DW virou fase própria (Fase 2).** Eu tinha isso só como
  "preservar a tabela de saída"; o modelo o promoveu a fase explícita, isolando os
  dependentes por contrato — mais limpo.
- **Cutover dos dependentes: caminho diferente do meu, igualmente válido.** Eu previa
  virar Sentinel → Cerebro → Pepper **um a um**, cada um como fase. O modelo optou por
  **feature flag transparente** (Fase 5): os leitores nunca mudam, a troca acontece atrás
  da flag. As duas são defensáveis; a do modelo evita mexer nos três consumidores, ao
  custo de exigir que a tabela oficial seja a mesma. Nenhuma viola as restrições — é
  espaço de decisão legítimo, não erro.
- **Núcleo convergiu:** shadow → equivalência provada → escrita dupla com flag →
  descomissionar o batch por último (com o cron mantido "frio" para rollback), e a Pepper
  tratada como o dependente mais sensível (madrugada) — igual à previsão.

### Ganchos para os próximos checkpoints (avaliação)

Cadeia pronta para o módulo de avaliação: **gate automático** (um prompt-juiz validando a
saída de cada elo antes do próximo — evolução natural do gate manual), **Chain-of-Verification**
sobre o plano do Elo 2 antes de executar em produção (a técnica seguinte ao least-to-most,
justamente para garantir que a decomposição não carregue erro), e **rubrica** por elo
(Elo 1: contratos completos? Elo 2: toda fase reversível e sem big-bang? Elo 3: rollback
coerente com o plano?).
