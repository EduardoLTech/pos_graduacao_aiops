# Migração incremental — cadeia de prompts encadeados

Item de catálogo — domínio **data**. Não é um prompt monolítico: é uma **cadeia de três
elos**, em que a saída de cada prompt é a entrada do próximo. Serve para planejar uma
migração grande e arriscada (ex.: pipeline de **lote → orientado a eventos**) em passos
pequenos, ordenados por dependência e reversíveis — sem virada única (big-bang).

## Por que uma cadeia, e não um prompt só

Uma migração dessas tem **mais de uma etapa cognitiva** — diagnosticar, planejar,
detalhar. Jogar tudo num único prompt produz resposta rasa e genérica. A regra prática:
se a tarefa tem mais de uma etapa de raciocínio, quebre em **um prompt por etapa**,
cada um com **uma responsabilidade só**, **output verificável** e **formato definido**
para o próximo consumir. Entre um elo e o outro há um **gate**: você valida a saída antes
de alimentar o próximo, para um erro no elo 1 não contaminar os elos 2 e 3 (efeito
cascata).

## Os três elos

| Elo | Prompt | Consome | Produz | Técnica |
|---|---|---|---|---|
| 1 | [`prompt-1-diagnostico.md`](prompt-1-diagnostico.md) | estado atual + dependentes + restrições | mapa do estado atual (fluxo, contratos, pontos frágeis, pontos de corte) | RISE |
| 2 | [`prompt-2-plano.md`](prompt-2-plano.md) | o mapa do Elo 1 | plano faseado, ordenado por dependência, reversível, sem big-bang | RISE + **Least-to-Most** |
| 3 | [`prompt-3-detalhamento.md`](prompt-3-detalhamento.md) | o plano do Elo 2 + a fase-alvo | runbook executável e reversível de **uma** fase (repetir por fase) | RISE |

O Elo 2 usa **least-to-most**: decompõe a migração do mais fundamental ao mais complexo,
com as dependências mapeadas — o padrão para planos executáveis multi-etapa. O Elo 3
roda **em loop**, uma vez por fase, para não detalhar tudo de uma vez (e não propagar
erro de decomposição).

## Como executar a cadeia

1. Uma conversa por execução. Modelo `claude-sonnet-4-6`.
2. **Elo 1:** cole o corpo do `prompt-1` (sem front-matter), preencha `{{estado_atual}}`,
   `{{dependentes}}`, `{{restricoes_migracao}}`, `{{sistema}}`. **Gate:** leia o mapa; o
   fluxo e os contratos batem com a realidade? Se sim, siga.
3. **Elo 2:** cole o corpo do `prompt-2`; em `{{diagnostico}}` cole a saída do Elo 1
   (na mesma conversa, pode referenciar "o mapa acima"); repita `{{restricoes_migracao}}`
   e informe `{{alvo}}`. **Gate:** cada fase é reversível e tem critério de avanço?
4. **Elo 3:** cole o corpo do `prompt-3`; em `{{plano}}` cole a saída do Elo 2, escolha a
   `{{fase_alvo}}` e, se quiser aterrar em comandos, informe `{{contexto_execucao}}`.
   Repita o Elo 3 trocando a fase até detalhar todas.

## Parâmetros por elo

Ver o front-matter de cada `prompt-N-*.md`. Regra geral: o parâmetro que carrega a saída
do elo anterior (`{{diagnostico}}`, `{{plano}}`) é **obrigatório**; os de contexto
(`{{sistema}}`, `{{alvo}}`, `{{contexto_execucao}}`) são opcionais.

## Método (por que este desenho)

- **Prompt chaining** é a espinha: cada elo com uma responsabilidade, saída verificável e
  formato pensado para o próximo elo ler. Os **gates** entre elos são o controle de
  qualidade da cadeia.
- **Least-to-most no Elo 2** porque planejar migração é decompor por dependência, do
  simples ao complexo — exatamente o caso da técnica.
- **RISE como base de cada elo** porque cada um é procedural, com input concreto e
  critério de pronto próprio.
