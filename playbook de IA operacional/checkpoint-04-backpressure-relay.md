# Checkpoint 04 — Segurando a sobrecarga do Relay

> Playbook de IA Operacional da Aegis — item nº 4 (domínio arquitetura).
> Sob pico, o Relay (barramento) recebe mais telemetry do que entrega, a fila cresce e
> o alerting do Sentinel atrasa. O Tony Stark quer uma **estratégia de backpressure** —
> mas não existe resposta única: há vários caminhos, cada um com um preço.
> Pedido: um prompt reusável que **compare os caminhos e pese os trade-offs** antes de
> recomendar, em vez de cuspir uma resposta só.

---

## 1. Decisões de método (o "porquê" antes do "o quê")

### Framework: RISE como base + Tree-of-Thought + Step-Back

O enunciado é explícito: *"não existe resposta única… faz a IA comparar mais de um
caminho, pesando prós e contras, antes de recomendar… o raciocínio importa tanto quanto
a recomendação"*. Isso é a definição de um problema **"depende"** — e o **Tree-of-Thought**
é a técnica para exatamente isso: ramificar o raciocínio em caminhos alternativos,
avaliar viabilidade e **trade-offs** de cada ramo e convergir na melhor opção com base
no contexto. O Chain-of-Thought seria o oposto: linha única de raciocínio para uma
resposta definitiva — que não é o caso aqui.

Como **base** eu uso o **RISE**, porque a tarefa é procedural com input concreto (o
cenário) e um critério de pronto claro. Mapeamento:

| Componente | No nosso prompt |
|---|---|
| **Role** | Staff engineer/arquiteto conduzindo decisão cara, que não entrega resposta única |
| **Input** | O cenário: `{{estado_sistema}}` + `{{restricoes}}` (+ `{{opcoes_candidatas}}`, `{{criterios}}`) |
| **Steps** | Step-back → enumerar ≥3 caminhos → desenvolver cada ramo → filtrar pelas restrições → tabela de trade-offs → confronto → recomendação → riscos |
| **Expectation** | `# Critério de pronto`: ≥3 caminhos avaliados em todos os critérios, restrições testadas, recomendação com "por que ela e por que não as outras", preço de cada caminho explícito |

**Regra de combinação** (base simples + elementos justificados):

- **+ Tree-of-Thought (núcleo).** É a técnica para "análise de trade-offs, comparação de
  custo/complexidade/performance, comparação de estratégias" — qualquer situação em que
  a resposta é "depende". Aqui há quatro caminhos em cima da mesa (prioridade ao
  Sentinel, dead-letter queue, particionar por cliente, auto-scaling) e combinações
  possíveis: é ramificação pura. O Steps do RISE embute o ToT — desenvolver cada opção
  como um ramo independente **antes** de comparar, para não ancorar na primeira ideia.
- **+ Step-Back (passo 0).** Enunciar as alavancas genéricas de backpressure (sob
  sobrecarga: priorizar, bufferizar, particionar, escalar, descartar) e **a restrição
  inegociável** (perda de telemetry é inaceitável — memória do Steve Rogers) antes de
  olhar as opções mantém o filtro rígido no centro e evita que o modelo recomende algo
  que viole o não-negociável.

**Por que não os outros frameworks.** CoT (linear, resposta única — o enunciado pede
justamente o contrário); RTF (a saída não é "previsível e direta", é raciocínio
multi-ramo); TAG (há ângulo de KPI — custo, SLA — mas o centro é a **decisão
arquitetural com trade-offs**, terreno do ToT, não a otimização de uma métrica); BAB
(não é transformação de um estado A para um B); CARE (não há exemplar-gabarito de
decisão para ancorar — cada decisão é diferente; o que guia é o **processo** de
comparação). **RISE + ToT + Step-Back** é o mínimo necessário, máximo suficiente.

### Parametrização (regra de método #1)

Dois parâmetros obrigatórios que espelham o que o enunciado chama de "o estado + as
restrições": `{{estado_sistema}}` e `{{restricoes}}`. Mantê-los separados força o modelo
a tratar as restrições como **filtro**, não como mais um dado. Três opcionais tornam o
item genérico para **qualquer** decisão de engenharia, não só o Relay:
`{{opcoes_candidatas}}` (caminhos já na mesa — se vazio, o modelo propõe),
`{{criterios}}` (com default embutido) e `{{sistema}}`.

### Custo assumido do Tree-of-Thought

O ToT custa mais: resposta mais longa, mais tokens (várias análises em paralelo). É um
trade-off consciente — em decisão cara, o raciocínio exposto **é** o produto, e o item é
rodado pontualmente, não em loop de plantão. Registrado no README do item.

### Meta-prompting / CRAFT (regra de método #2)

Construído via **CRAFT** (humano no controle): dirigi um modelo forte com um meta-prompt
descrevendo a dor (decisão de backpressure sem resposta única, comparar caminhos e pesar
prós/contras, respeitar o inegociável de não perder dado), pedindo estrutura RISE com ToT
no Steps. O modelo gerou o rascunho; **a curadoria é minha** (§4). O meta-prompt não
entra na biblioteca — só o prompt final. **Criar com o caro (Opus 4.8), executar com o
barato (Sonnet/Haiku).**

### Versionamento/organização

Novo domínio **`arquitetura`** (decisão de engenharia é função distinta de
triagem/RCA — domínio por negócio/função, não por técnica). Padrão de catálogo:
Markdown + front-matter, pasta por prompt → `arquitetura/decisao-arquitetural-tradeoff/prompt.md`
+ `README.md`.

---

## 2. Entregável — o prompt parametrizável

Caminho no repositório: `arquitetura/decisao-arquitetural-tradeoff/prompt.md`
(front-matter + corpo completo lá). Estrutura RISE com ToT embutido no Steps:

- **# Papel** — staff engineer/arquiteto em decisão cara; não entrega resposta única.
- **# Tarefa** — comparar ≥3 caminhos, avaliar contra critérios e restrições, recomendar
  (podendo ser combinação faseada) com o porquê dela e o porquê dos descartados.
- **# Entrada** — `{{estado_sistema}}`, `{{restricoes}}`, `{{opcoes_candidatas}}`,
  `{{criterios}}`, `{{sistema}}`, delimitados; "trabalhe só com o que está aqui".
- **# Passos** — Step-back (passo 0) → enumerar caminhos → desenvolver cada ramo isolado
  → filtro das restrições inegociáveis → tabela de trade-offs → confronto das finalistas
  → recomendação → riscos e validação.
- **# Formato da saída** — veredito 1 linha + caminhos considerados + tabela de
  trade-offs + checagem de restrições + recomendação (🔴 agora × 🟢 estrutural) + por que
  não as alternativas + riscos/validação.
- **# Regras** — não pular para a resposta (≥3 caminhos); recomendação sempre respeita o
  inegociável; trade-off honesto (nomear o preço); ancorar no cenário; `falta medir <X>`.
- **# Critério de pronto (Expectation)** — fecha o 4º componente do RISE.

> O conteúdo integral está em `arquitetura/decisao-arquitetural-tradeoff/prompt.md` para
> não duplicar a fonte da verdade (DRY de prompt).

---

## 3. Execução (real, verificada)

> **Status: execução manual verificada.** Output **real** do modelo para o cenário do
> Relay, colado verbatim abaixo.

**Modelo de execução:** `claude-sonnet-4-6` (criar caro, executar barato).

### Parâmetros usados na execução

- `{{sistema}}` =
  `Relay — barramento de eventos assíncrono e borda de ingestão da Aegis; todo o telemetry dos clientes entra por ele e é distribuído para Forge (ingestão) e Sentinel (alerting em tempo real).`

- `{{estado_sistema}}` =
  ```
  Relay (barramento de eventos):
  - throughput sustentado: 180k msgs/s
  - pico observado no incidente da semana passada: 320k msgs/s por 25min
  - retenção atual: 4h
  - consumidores: Forge (ingestão), Sentinel (alerting em tempo real)
  ```

- `{{restricoes}}` =
  ```
  - [RÍGIDA] alerting do Sentinel não pode atrasar mais que 60s (SLA com cliente)
  - [FLEXÍVEL] ingestão do Forge pode atrasar até 15min sem violar SLA
  - [RÍGIDA] perda de telemetry é inaceitável (produto de observabilidade; o barramento antigo perdia mensagens sob pico — não repetir)
  - [PRESSÃO] orçamento de infra do trimestre já está 8% acima do previsto
  ```

- `{{opcoes_candidatas}}` =
  ```
  - Prioridade de consumo: Sentinel (tempo real) na frente do Forge (que espera até 15min)
  - Dead-letter queue: guardar o não processado numa fila separada para reprocessar depois
  - Particionar o Relay por cliente, para um cliente barulhento não afetar os outros
  - Auto-scaling: aumentar automaticamente o número de consumidores quando a carga sobe
  (pode ser um destes ou uma combinação)
  ```

- `{{criterios}}` = `nenhum` (usar o default: SLA · custo/infra · risco de perda · complexidade · tempo até valer)

### Output real do modelo (verbatim)

```
Veredito: priorizar o Sentinel sobre o Forge (shedding seletivo) combinado com uma
dead-letter queue para o que for adiado — feito agora; particionamento por cliente e
auto-scaling ficam como camada estrutural para o próximo trimestre, pois sozinhos não
resolvem o pico atual e custam mais do que o orçamento permite hoje.

Passo 0 — Alavancas e restrição inegociável

Sob sobrecarga as alavancas clássicas são: priorizar (dar SLA a quem tem SLA mais
apertado), bufferizar (guardar o que pode esperar), particionar (isolar ruído), escalar
(adicionar capacidade) ou descartar (aceitar perda). A restrição inegociável aqui é
dupla: Sentinel ≤60s e zero perda de telemetria (lição do incidente anterior de Steve
Rogers). Isso já elimina "descartar" como alavanca aceitável e empurra a solução para
priorização + buffer, não para escalonamento puro (que custa dinheiro que não sobra).

Caminhos considerados

- A — Priorizar Sentinel sobre Forge: em pico, o Relay entrega primeiro ao consumidor de
  alerting, deixando Forge acumular atraso (dentro do teto de 15min).
- B — Dead-letter queue (DLQ) para reprocesso: o que não é processado em tempo é gravado
  numa fila separada e reprocessado depois, sem perda.
- C — Particionamento por cliente: sharding do Relay para isolar um cliente barulhento
  dos demais.
- D — Auto-scaling de consumidores: escalar automaticamente o número de consumidores
  quando a carga sobe.

Desenvolvimento por caminho

A — Priorizar Sentinel
- SLA: resolve diretamente o risco de violar o SLA de 60s do Sentinel, porque Forge cede espaço.
- Custo: baixo — é política de scheduling/QoS, não capacidade nova.
- Perda/dano: por si só não perde dados, mas sob pico sustentado (>15min) Forge pode estourar o próprio SLA se não houver buffer.
- Complexidade: baixa-média — exige fila com prioridade ou dois tópicos/lanes no Relay.
- Tempo até efeito: rápido (dias), é configuração, não infraestrutura nova.

B — Dead-letter queue
- SLA: não resolve atraso do Sentinel diretamente, mas garante que o Forge não perca nada mesmo se atrasar além dos 15min — vira a rede de segurança que falta na opção A.
- Custo: baixo-médio — precisa de storage adicional, mas não de mais throughput.
- Perda/dano: resolve exatamente a lição do incidente anterior (zero perda), é a opção mais alinhada com "perda de telemetria é inaceitável".
- Complexidade: média — precisa de lógica de reprocesso e monitoração da própria DLQ (backlog da DLQ pode virar problema novo).
- Tempo até efeito: médio (semana a poucas semanas) — depende de implementar o mecanismo de reprocesso.

C — Particionamento por cliente
- SLA: ajuda indiretamente (isola ruído de um cliente), mas não resolve o cenário do incidente relatado, que foi pico agregado, não um cliente específico.
- Custo: alto — resharding do Relay é retrabalho estrutural, toca ingestão e consumidores.
- Perda/dano: neutro, não endereça perda em pico agregado.
- Complexidade: alta — rebalanceamento de partições, possível rehashing de chaves, coordenação com Forge/Sentinel.
- Tempo até efeito: longo (múltiplas semanas/meses).
- falta medir: se o pico da semana passada foi causado por concentração em poucos clientes ou distribuído — sem esse dado, o benefício de C é especulativo.

D — Auto-scaling de consumidores
- SLA: ajuda ambos os consumidores a digerir a fila mais rápido, mas scaling tem lag (provisionamento, rebalanceamento de partições/consumer groups) — pode não reagir a tempo de um pico de 25min.
- Custo: viola a restrição de orçamento — trimestre já 8% acima do previsto, e auto-scaling tende a aumentar gasto, não reduzir.
- Perda/dano: ajuda a reduzir acúmulo, mas não é garantia contra perda (retenção de 4h ainda é o teto absoluto).
- Complexidade: média-alta — requer métricas de lag, políticas de scale-out/in, testes de carga.
- Tempo até efeito: médio, mas o ganho está condicionado a orçamento que não existe hoje.

Trade-offs

┌─────────────────┬─────────────────────────────┬─────────────────┬────────────────────┬────────────────────┬──────────┐
│                 │                             │                 │                    │                    │  Tempo   │
│      Opção      │         Impacto SLA         │   Custo/infra   │   Risco de perda   │    Complexidade    │   até    │
│                 │                             │                 │                    │                    │  efeito  │
├─────────────────┼─────────────────────────────┼─────────────────┼────────────────────┼────────────────────┼──────────┤
│ A. Priorizar    │ Resolve SLA do Sentinel;    │                 │ Médio se pico >    │                    │          │
│ Sentinel        │ Forge fica no limite dos    │ Baixo           │ retenção de 4h sem │ Baixa-média        │ Rápido   │
│                 │ 15min                       │                 │  buffer            │                    │          │
├─────────────────┼─────────────────────────────┼─────────────────┼────────────────────┼────────────────────┼──────────┤
│                 │ Não ataca os 60s            │ Baixo-médio     │ Baixo — é a rede   │ Média (reprocesso  │          │
│ B. DLQ          │ diretamente, mas evita      │ (storage)       │ de segurança       │ + monitorar a DLQ) │ Médio    │
│                 │ perda quando Forge estoura  │                 │                    │                    │          │
├─────────────────┼─────────────────────────────┼─────────────────┼────────────────────┼────────────────────┼──────────┤
│ C. Particionar  │ Ajuda só se causa raiz for  │ Alto            │ Neutro para pico   │ Alta               │ Longo    │
│ por cliente     │ cliente isolado             │ (resharding)    │ agregado           │                    │          │
├─────────────────┼─────────────────────────────┼─────────────────┼────────────────────┼────────────────────┼──────────┤
│                 │                             │ Estoura         │ Reduz acúmulo, não │                    │ Médio,   │
│ D. Auto-scaling │ Ajuda mas com lag de reação │ orçamento (já   │  garante zero      │ Média-alta         │ mas caro │
│                 │                             │ +8%)            │ perda              │                    │          │
└─────────────────┴─────────────────────────────┴─────────────────┴────────────────────┴────────────────────┴──────────┘

Preço de cada caminho: A custa "Forge fica mais lento sob pico" (aceitável dentro do SLA
de 15min); B custa complexidade operacional extra (monitorar backlog da DLQ); C custa
retrabalho estrutural caro sem evidência de que resolve o problema relatado; D custa
dinheiro que o time não tem agora.

Checagem de restrições inegociáveis

- Sentinel ≤60s: A passa (resolve diretamente); B é neutro (não atrasa nem resolve sozinho); C passa só se ruído vier de 1 cliente (não comprovado); D passa em teoria, mas com risco de lag de provisionamento.
- Forge ≤15min: A passa desde que o pico não ultrapasse a janela de retenção somada ao tempo de processamento — exige B para não perder o excedente; C e D não resolvem isso de forma garantida.
- Zero perda de telemetria: só B garante isso de forma direta. A sozinha arrisca perda se o pico exceder a retenção de 4h; C e D não endereçam perda.
- Orçamento (já +8%): A e B passam (custo baixo); C reprova (resharding caro); D reprova (escalonamento consome mais infra).

Recomendação

🔴 Agora: A + B combinados — priorizar Sentinel no Relay (lane/fila de prioridade) e
implementar DLQ para tudo que Forge não processar dentro da janela de retenção. Essa
combinação é a única que satisfaz as quatro restrições simultaneamente: protege o SLA de
60s, mantém Forge dentro dos 15min (ou, se estourar, preserva os dados na DLQ em vez de
perdê-los), custa pouco e é rápida de implementar.

🟢 Estrutural (próximo trimestre, após liberação de orçamento ou evidência de causa
raiz): avaliar C somente se os dados do próximo incidente mostrarem que o pico veio de um
cliente concentrado (hoje isso não está comprovado — falta medir distribuição do pico por
cliente); avaliar D somente quando o orçamento normalizar, como camada adicional de
resiliência para picos > 25min.

Por que não as alternativas

- C isolada: caro e não comprovadamente relacionado à causa do incidente relatado — resolveria um problema que talvez não seja o que aconteceu.
- D isolada: viola a restrição de orçamento do trimestre e tem lag de reação que pode não cobrir um pico de 25min como o observado.
- A isolada (sem B): continua exposta à lição do Steve Rogers — se o pico ultrapassar a retenção de 4h, Forge perde mensagens, repetindo o problema do barramento antigo.

Riscos e o que validar

Confiança: média-alta para A+B como resposta ao pico descrito; baixa para descartar C e D
permanentemente, pois faltam dados.

Riscos residuais: (1) a DLQ pode acumular backlog silenciosamente se o reprocesso não
tiver alarme próprio; (2) se picos como o da semana passada se tornarem frequentes (não
só um evento isolado), A+B pode não bastar e D vira necessário, forçando renegociação de
orçamento.

Antes de executar, validar: falta medir volume esperado de dados que iriam para a DLQ num
pico de 320k msgs/s por 25min (dimensionar storage); falta medir se o incidente da semana
passada foi causado por um cliente concentrado (decide se C é relevante); definir alarme
de profundidade da fila de prioridade do Sentinel e da DLQ antes do rollout.
```

---

## 4. Curadoria (a "assinatura" no item)

- **O risco central que blindei: cuspir uma resposta única.** O enunciado pede
  comparação de caminhos, então a regra "não pule para a resposta — ≥3 caminhos
  desenvolvidos antes de recomendar, mesmo que você já 'saiba'" e o Steps que manda
  desenvolver cada ramo **isoladamente** (antes de comparar) são o coração do item. Sem
  isso, o ToT degenera em CoT com uma resposta pré-decidida.
- **A restrição inegociável como filtro, não como bullet.** "Perda de telemetry é
  inaceitável" (Steve Rogers) e o SLA de 60s do Sentinel são **rígidos**. O passo 0
  (Step-Back) os coloca no centro antes das opções, e o passo 3 (filtro) desqualifica
  qualquer caminho que os viole sozinho. Marquei no parâmetro `{{restricoes}}` o que é
  `[RÍGIDA]` vs `[FLEXÍVEL]` vs `[PRESSÃO]` para o modelo tratar cada um no seu peso.
- **Trade-off honesto.** A regra "todo caminho tem um preço; nomeie-o — nada de opção
  sem desvantagem" impede a saída boba em que a recomendação parece gratuita. Casa com
  o orçamento 8% acima: custo é critério de primeira classe.
- **Recomendação pode ser combinação faseada (🔴 agora × 🟢 estrutural).** Decisões de
  backpressure raramente são "uma bala de prata"; separar o que fazer no pico do que é
  mudança estrutural reflete a realidade e respeita o orçamento (começar barato).
- **Ancoragem no cenário + `falta medir <X>`.** Anti-alucinação: sem inventar números
  ou SLAs fora da entrada; se um critério não der para avaliar, dizer o que medir.

### Recomendação prevista (minha leitura — a validar contra a execução real)

> Registro **minha previsão** (curadoria), explicitamente **não** como output de modelo.
> Serve para conferir a §3 quando a execução real voltar.

**Combinação faseada, ordenada por custo (por causa do orçamento 8% acima):**

- **🔴 Agora (barato, software):** **prioridade de consumo** — Sentinel (alerting) na
  frente do Forge. Justificativa direta pelas restrições: o Sentinel tem SLA rígido de
  60s e o Forge tolera 15min; sob pico, drenar primeiro o consumidor crítico. A
  **retenção de 4h** vira aliada: o pico dura ~25min, então o Forge **recupera o atraso
  depois** dentro da folga da retenção, sem perder nada. Custo ~zero, efeito imediato,
  protege o SLA que importa.
- **🟢 Estrutural:** **particionar por cliente** (isola o cliente barulhento — foi um
  cliente grande que causou o pico) + **auto-scaling de consumidores com teto**
  (absorve picos sem estourar o orçamento, graças ao limite). A DLQ entra como **rede de
  segurança para overflow real**, garantindo o inegociável (não perder telemetry) —
  mas não como mecanismo primário, porque reprocessar depois não protege o SLA de tempo
  real do Sentinel.

**Por que não cada uma sozinha (previsão):**
- *Só DLQ:* garante não-perda, mas o dado reprocessado chega atrasado — não segura o SLA
  de 60s do Sentinel no momento do pico. Rede de segurança, não solução primária.
- *Só auto-scaling:* combate o volume, mas escalar sem teto colide com o orçamento 8%
  acima, e não protege contra um cliente barulhento específico; leva tempo para subir
  consumidores (pode não pegar os 25min de pico).
- *Só particionar por cliente:* isola o ruidoso, mas sozinho não prioriza Sentinel sobre
  Forge nem garante não-perda no pico; é estrutural e lento de implementar.
- *Só prioridade:* protege o SLA de imediato, mas não isola o cliente barulhento nem, por
  si, garante o não-descarte se a retenção estourar — precisa da DLQ como piso.

**Restrição que amarra a resposta:** como *nenhuma opção sozinha* respeita as duas
restrições rígidas (SLA 60s **e** zero perda) sob o pico, a resposta correta é
**combinação** — exatamente o que a regra "se nenhuma opção sozinha respeita o
inegociável, proponha a combinação" força o modelo a produzir.

### Verificação da execução real (não foi simulação) — ✅ item entregue

A saída da §3 é a **execução manual verificada** no `claude-sonnet-4-6`. O teste real
**confirmou a previsão e passou em todos os critérios de pronto** — o item está entregue,
sem necessidade de ajuste no prompt:

- ✅ **Não cuspiu resposta única.** Os quatro caminhos (A, B, C, D) foram desenvolvidos em
  ramos independentes, cada um avaliado nos cinco critérios do default, **antes** da
  comparação. O ToT segurou: nada de pular para a conclusão.
- ✅ **Restrições inegociáveis como filtro.** A seção "Checagem de restrições" testou cada
  caminho contra as quatro restrições, e o passo 0 já tinha isolado o duplo inegociável
  (SLA 60s + zero perda), eliminando "descartar" logo de cara. Foi o filtro que forçou a
  combinação: *"só B garante zero perda; A sozinha arrisca perda se o pico exceder a
  retenção"* → recomendação A+B.
- ✅ **Trade-off honesto.** Linha "Preço de cada caminho" explícita para todos — nenhuma
  opção apareceu sem desvantagem.
- ✅ **Recomendação faseada com os dois porquês.** 🔴 A+B agora × 🟢 C/D estrutural, com
  "por que não as alternativas" caminho a caminho.
- ✅ **`falta medir <X>` funcionou.** O modelo se recusou a bater o martelo em C sem dado:
  *"falta medir se o pico veio de um cliente concentrado"* — anti-alucinação na prática,
  em vez de inventar que o incidente foi causado por um cliente específico.
- ✅ **Confiança + riscos residuais + o que validar** declarados.

**Divergências vs. minha previsão — todas benignas, nenhuma exige mudança no prompt:**
- **Convergência forte no núcleo:** eu previa A + DLQ agora, com C/D estruturais — o
  modelo chegou exatamente a A+B agora e C/D adiados. O raciocínio bateu no ponto-chave
  ("nenhuma opção sozinha satisfaz SLA 60s **e** zero perda → combinação obrigatória").
- **O modelo foi mais disciplinado que eu ao adiar C e D.** Eu havia colocado
  particionamento + auto-scaling como recomendação estrutural quase certa; o modelo os
  condicionou a **evidência** ("só se o próximo incidente mostrar cliente concentrado") e
  a **orçamento normalizado**. É mais defensável — não compromete capital estrutural sem
  dado, exatamente o comportamento que a regra `falta medir` deveria induzir.
- **Nuance de risco que eu não havia previsto:** o modelo levantou que a **própria DLQ
  vira problema novo** se acumular backlog sem alarme — um risco de segundo nível que
  enriquece a saída e valida a exigência de "riscos residuais".

### Ganchos para os próximos checkpoints (avaliação)

Item pronto para o módulo de avaliação: **rubrica** (≥3 caminhos desenvolvidos? cada
restrição rígida testada? recomendação com "por que ela e por que não as outras"? preço
de cada caminho nomeado? riscos declarados?), **3 perguntas** (a recomendação respeita
todas as restrições rígidas? algum caminho ficou sem trade-off? a fase 🔴/🟢 faz sentido
de custo?) e **golden-answer** frouxa (o gabarito não é uma opção única, e sim
"combinação que respeita SLA + não-perda começando barato" — avaliar por critérios, não
por string exata).
