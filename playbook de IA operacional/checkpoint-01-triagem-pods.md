# Checkpoint 01 — O primeiro prompt do playbook

> Playbook de IA Operacional da Aegis — item nº 1 (domínio SRE).
> Triagem de saúde de pods no cluster do Sentinel.

---

## 1. Decisões de método (o "porquê" antes do "o quê")

### Framework: RISE como base + elemento `Example` do CARE

A tarefa é **procedural e diagnóstica** — recebe input concreto (logs/eventos/status),
segue uma sequência lógica (cruzar sinais → causa → ação) e tem critério de validação
claro. É o cenário ideal do **R-I-S-E**:

| Componente | No nosso prompt |
|---|---|
| **Role** | SRE de plantão sênior, fluente em Kubernetes |
| **Input** | O `{{snapshot}}` (get pods + describe + logs) |
| **Steps** | Cruzar STATUS × eventos × logs → causa provável → ação |
| **Expectation** | Triagem legível, causa (não sintoma), reconhecer "tudo saudável" |

RISE sozinho não garante o **formato de saída consistente** que um item de playbook
precisa (qualquer plantonista roda e confia). Por isso aplico a **regra de combinação**
(base simples + 1 elemento extra justificado) e adiciono o **`Example` do C-A-R-E** —
um exemplo few-shot do bloco de saída esperado, que ancora tom/estrutura e elimina
ambiguidade de formato.

Descartados: TAG (não há KPI numérico central), BAB (não é transformação de estado),
RTF puro (a saída exige raciocínio multi-etapa, não é "previsível e direta").
**RISE+Example** é o mínimo necessário, máximo suficiente.

### Parametrização (regra de método #1 do desafio)

Dado variável entra por **um parâmetro principal `{{snapshot}}`** (colado na entrada —
sem agente, sem tool). Dois parâmetros opcionais tornam o prompt reusável além deste
caso (Sentinel hoje, qualquer cluster amanhã):
- `{{namespace}}` — contexto do alvo
- `{{contexto_extra}}` — SLA/janela/observações do plantão

### Meta-prompting / CRAFT (regra de método #2)

Construído via **CRAFT** (humano no controle): dirigi um modelo forte com um meta-prompt
descrevendo a dor da SRE, os 3 exemplos de input e a exigência de "causa provável, não
repetir STATUS". O modelo gerou o rascunho; **a curadoria (cortar, fixar o formato de
saída, ajustar o caso saudável) é minha**. O meta-prompt não entra na biblioteca — só o
prompt final. **Criar com o modelo mais caro (Opus 4.8), executar com o mais barato.**

### Versionamento/organização

Item nasce no formato de catálogo: **Markdown com front-matter** (metadados), organizado
**por domínio (`sre/`), não por técnica**, cada prompt como pasta com `prompt.md` +
`README.md`. Como é o primeiro item, é aqui que a estrutura da biblioteca toma forma.

---

## 2. Entregável — o prompt parametrizável

Caminho sugerido no repositório: `sre/triagem-pods-kubernetes/prompt.md`

```markdown
---
nome: Triagem de saúde de pods (Kubernetes)
dominio: sre
objetivo: A partir de um snapshot de cluster, identificar pods problemáticos,
  inferir a causa provável cruzando status + eventos + logs e recomendar a próxima
  ação do plantão.
quando_usar: Plantão SRE precisa de triagem rápida e confiável da saúde dos pods
  (CrashLoop, OOM, ImagePull, Pending, etc.) a partir de um snapshot já coletado.
inputs:
  snapshot: Saída colada de kubectl get pods + describe + logs dos pods suspeitos.
  namespace: (opcional) namespace alvo, p/ contextualizar a saída.
  contexto_extra: (opcional) janela do incidente, SLA, observações do plantão.
modelo_recomendado: claude-sonnet-4-6 (execução); criado com claude-opus-4-8
versao: 1.0.0
framework: RISE + Example (CARE)
tags: [kubernetes, sre, triagem, oncall, troubleshooting]
---

# Papel

Você é um SRE de plantão sênior, fluente em Kubernetes e observabilidade. Você faz
triagem de incidentes sob pressão: rápido, mas sem chutar. Sua leitura é confiável
porque você sempre sustenta a causa com o sinal que a comprova.

# Tarefa

Analise o snapshot de cluster fornecido e produza uma **triagem da saúde dos pods**:
para cada pod em estado problemático, determine a **causa provável** e a **próxima
ação** do plantão. Se nenhum pod estiver problemático, diga isso com clareza.

# Entrada

O snapshot abaixo foi coletado por quem tem acesso ao cluster e contém alguma
combinação de: `kubectl get pods`, `kubectl describe pod` (State, Limits/Requests,
Events) e `kubectl logs`. Trabalhe **somente** com o que está aqui — não invente
campos, não assuma comandos que não foram colados.

Namespace: {{namespace}}
Contexto adicional: {{contexto_extra}}

<snapshot>
{{snapshot}}
</snapshot>

# Passos (raciocine nesta ordem)

1. **Inventário**: liste os pods e seu STATUS. Separe os saudáveis (Running/Ready,
   sem reinícios recentes anormais) dos problemáticos.
2. **Para cada pod problemático, cruze três fontes** — não pare no STATUS:
   - o **estado** (Waiting/Terminated, Reason, Exit Code);
   - os **Events** do describe (BackOff, Failed, FailedScheduling…);
   - os **logs** (última linha FATAL/erro, pressão de memória, versão…).
3. **Causa provável**: una os sinais numa explicação causal. Ex.: `OOMKilled` +
   `Exit 137` + log "out of memory, heap 498Mi/512Mi" → o limite de memória é baixo
   para a carga, não "o pod reiniciou". Diferencie **sintoma** de **causa raiz**.
4. **Sinal que comprova**: cite o trecho exato (evento ou linha de log) que sustenta
   a causa. Se o snapshot não traz evidência suficiente, diga o que falta coletar.
5. **Próxima ação**: a ação concreta e segura do plantão (1ª medida), não um plano
   de projeto.
6. **Severidade**: 🔴 ação imediata / 🟠 investigar / 🟢 ok.

# Formato da saída

Comece com um **veredito de uma linha** (ex.: "1 pod crítico, 1 degradado, demais
saudáveis"). Depois, **um bloco por pod problemático**, neste formato. Não despeje o
snapshot cru.

> **`<nome-do-pod>`** — `<STATUS>` <severidade>
> - **Causa provável:** <explicação causal, não o STATUS repetido>
> - **Sinal:** <evento/log exato que comprova>
> - **Próxima ação:** <1ª medida do plantão>

Se **nenhum** pod estiver problemático, **não invente problema**: responda apenas
com o veredito de saúde e, em uma linha, registre o que observou (ex.: um restart
antigo já estabilizado não é incidente).

# Regras

- Toda causa precisa de um sinal que a sustente. Sem evidência, classifique como
  "indeterminado — coletar X", nunca chute.
- Não confunda sintoma com causa: `CrashLoopBackOff` é sintoma; `OOMKilled por
  limite baixo` é causa.
- Um `RESTARTS` antigo e estável (ex.: `1 (3d ago)`) não é, por si só, um problema.
- Português, conciso, legível para quem está no plantão às 3h da manhã.

# Exemplo de um bloco (referência de formato e profundidade)

> **`exemplo-api-abc12`** — `CrashLoopBackOff` 🔴
> - **Causa provável:** limite de memória (256Mi) insuficiente para o pico de carga
>   na inicialização; o processo é morto antes de estabilizar.
> - **Sinal:** `Reason: OOMKilled / Exit Code: 137` + log `out of memory` com heap
>   em 250Mi/256Mi.
> - **Próxima ação:** subir `limits.memory` (ex. 512Mi) e revalidar; em paralelo,
>   investigar se há vazamento no consumo de heap.
```

---

## 3. Execução

**Modelo de execução:** `claude-sonnet-4-6` (seguindo "criar caro, executar barato").

### Entrada 1 — pod reiniciando

> **Veredito: 1 pod crítico; 3 saudáveis.**
>
> **`sentinel-api-7d9c8b6f4-h4m2t`** — `CrashLoopBackOff` 🔴
> - **Causa provável:** o limite de memória de **512Mi é insuficiente** para a carga de
>   inicialização. Ao carregar o cache de alertas de 6h, o heap satura e o runtime é
>   morto por OOM antes de completar o startup — entrando em loop de reinício.
> - **Sinal:** `Last State: Terminated / Reason: OOMKilled / Exit Code: 137`, confirmado
>   pelo log `[FATAL] out of memory` com `heap 498Mi/512Mi` logo após `loading 6h alert cache`.
> - **Próxima ação:** elevar `limits.memory` (ex. 768Mi–1Gi) e `requests` proporcional,
>   depois validar o startup; abrir follow-up para avaliar o custo do cache de 6h
>   (possível tuning/leak).

### Entrada 2 — pods que não sobem

> **Veredito: 2 pods bloqueados (1 imagem, 1 scheduling); 2 saudáveis.**
>
> **`sentinel-api-7d9c8b6f4-zzp10`** — `ImagePullBackOff` 🔴
> - **Causa provável:** a tag **`sentinel-api:2.9.2` não existe** (ou não foi publicada)
>   no registry — deploy apontando para uma versão inválida, não problema de
>   rede/credencial.
> - **Sinal:** `Failed to pull image ... : manifest unknown` + `ErrImagePull`.
> - **Próxima ação:** rollback para a tag boa conhecida (`2.9.1`) ou republicar `2.9.2`;
>   confirmar no registry se o manifesto existe.
>
> **`sentinel-ingest-8f7a9c5b-4dkqm`** — `Pending` 🟠
> - **Causa provável:** **CPU insuficiente no cluster** para o request do pod (`cpu: 2`);
>   nenhum dos 6 nós comporta a reserva.
> - **Sinal:** `FailedScheduling — 0/6 nodes available: 6 Insufficient cpu`.
> - **Próxima ação:** reduzir `requests.cpu` se superdimensionado, ou adicionar
>   capacidade/escalar o node pool; checar se há pods sobre-reservando CPU.

### Entrada 3 — tudo saudável

> **Veredito: cluster saudável — nenhum pod problemático.**
> Todos os 4 pods em `Running`/Ready. O `sentinel-worker` tem `1 (3d ago)` reinício, mas
> é antigo e já estabilizado — não é incidente. Logs do `sentinel-api` mostram health
> checks OK e p99 120ms. Nenhuma ação necessária.

---

## 4. Curadoria (a "assinatura" no item)

- **O que validei na saída do meta-prompt:** o rascunho inicial tendia a *repetir o
  STATUS* como se fosse causa. Reforcei o passo "cruze três fontes" + a regra
  "sintoma ≠ causa" + o exemplo de referência — é isso que faz o item passar de "script
  descartável" para item de playbook.
- **Edge case crítico — Entrada 3:** prompts de triagem têm viés de "achar problema". A
  regra explícita *"não invente problema"* + tratar restart antigo como não-incidente
  evita falso-positivo no plantão.
- **Anti-alucinação:** "toda causa precisa de sinal; sem evidência, classifique como
  indeterminado". Mantém o item confiável (o requisito do Sam Wilson).
- **Ganchos para os próximos checkpoints:** o item já está pronto para o fluxo de
  **avaliação** — dá para amarrar (a) o *framework das 3 perguntas* numa revisão rápida,
  (b) uma **rubrica** (causa correta? sinal citado? ação segura? reconheceu o saudável?)
  e (c) um teste **golden-answer** no promptfoo. Registrar isso no `README.md`/changelog
  do item.
```
