# Nota de triagem padronizada (alertas)

Item nº 2 do Playbook de IA Operacional da Aegis · domínio **SRE**.

## Descrição

Recebe um **alerta cru** (linha de log / payload do disparo do Sentinel) de qualquer
sistema da plataforma (Relay, Forge, Sentinel, Cerebro) e devolve uma **nota de triagem
no padrão único** do plantão: cinco campos fixos — `ALERTA`, `IMPACTO`,
`HIPÓTESE INICIAL`, `AÇÃO IMEDIATA`, `ESCALAR PARA`.

## Objetivo

Acabar com a variação de formato entre plantonistas (cada um escrevendo a nota do seu
jeito) para que **quem assume o turno seguinte** leia todas as notas no mesmo molde e
entenda o incidente em segundos. Pedido da Carol Danvers (Head of Product).

## Público-alvo

Plantonistas / SRE (time do Sam Wilson) que abrem a nota assim que o Sentinel dispara.

## Como usar

1. Copie o alerta cru (a linha que o Sentinel disparou).
2. Cole no parâmetro `{{alerta}}` do `prompt.md`.
3. (Opcional) Preencha `{{contexto_extra}}` com deploys conhecidos, SLA ou janela.
4. Execute em chat/playground/API. **Sem agente e sem tools** — o dado vai colado.

## Parâmetros de entrada

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `alerta` | sim | O alerta cru colado (sistema, métrica, janela, tenant, pistas). |
| `contexto_extra` | não | Observações do plantão, SLA, deploys recentes conhecidos. |

## Framework e técnica

**R-T-F** (Role · Task · Format) como base — é uma **transformação direta** de alerta
cru em nota com **saída previsível** (cinco rótulos fixos), o caso de uso clássico do
RTF. O padrão é ensinado por **few-shot** (os três exemplos de nota-modelo embutidos no
prompt = o elemento **Example** do CARE): em vez de descrever as regras de formato em
prosa, mostramos exemplos prontos e deixamos o **in-context learning** fixar tom e
estrutura. Construído via **meta-prompting / CRAFT** (humano no controle).

Mapa dos componentes no prompt: **Role** → `# Papel`; **Task** → `# Tarefa`;
**Format** → o gabarito em `# Tarefa` + os exemplos em `# Exemplos do padrão`.

### Por que few-shot e não zero-shot (descrição em prosa)?

O padrão "bom" já está cristalizado em três notas-modelo. Descrever esse padrão em
prosa (zero-shot) deixa tom e formato à interpretação do modelo — o que reproduz
justamente o problema que queremos resolver (cada execução sai um pouco diferente). O
few-shot ancora o formato pelo exemplo, como no caso de commit padronizado. Custo extra
de tokens é aceitável: são **3 exemplos** (faixa recomendada 3–5), curtos e com nuance
diferente (um por sistema), e o "melhor exemplo" fica por último (maior peso).

## Casos de uso validados

| Cenário | Entrada (resumo) | Resultado esperado |
|---|---|---|
| Saturação do Sentinel | autoscaler no teto (60/60), tenant 4x baseline | Nota com IMPACTO na fila do Relay; hipótese = pico do tenant; escalar `@sentinel-core`. |
| Rejeição no Relay pós-deploy | reject 6% por 8min após deploy 02:55 | Hipótese = deploy saturou buffer; ação = rollback; escalar `@relay-core`. |
| Lag no Forge por falha de job | consumer lag 9min subindo, job anterior falhou | Hipótese = falha do job atrasou o batch; ação = reprocessar; escalar `@data-platform`. |

## Limitações

- A nota é só do alerta colado: se o alerta não traz pista de causa, a `HIPÓTESE
  INICIAL` sai como **indeterminada — investigar X** (não chuta).
- O mapeamento sistema→time é fixo no prompt; revisar se a topologia de times mudar.

## Avaliação (próximos passos)

Pronto para o fluxo de avaliação: **rubrica** (5 campos presentes? hipótese ancorada
em sinal? time de escalonamento correto? impacto é consequência?) e **golden-answer**
no promptfoo, comparando contra as notas-modelo.

## Changelog

| Versão | Data | Mudança |
|---|---|---|
| 1.0.0 | 2026-06-30 | Criação do item (Checkpoint 02). |
