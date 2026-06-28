# Playbook de IA Operacional — Aegis

Biblioteca de prompts **versionada, testada e tratada como código** para o time de
engenharia da Aegis (empresa de observabilidade e resposta a incidentes). Cada item é um
prompt **parametrizável**, criado por **meta-prompting** (CRAFT, humano no controle) e
documentado para qualquer engenheiro pegar e confiar.

## Princípios

1. **Parametrização** — todo prompt recebe os dados variáveis por parâmetro
   (`{{snapshot}}`, `{{alerta}}`, `{{artefato}}`, `{{provedor}}`…); os dados vão colados na
   entrada (sem agente, sem tool externa).
2. **Meta-prompting** — o prompt é gerado dirigindo a IA e curado por humano. Cria-se com
   modelo forte (Opus 4.8) e executa-se com modelo barato (Sonnet/Haiku).
3. **Versionado** — Markdown + front-matter, organizado **por domínio** (não por técnica),
   com fluxo Git.

## Organização

```
playbook de IA operacional/
├── README.md                       ← este índice
├── checkpoint-NN-<slug>.md         ← resposta completa de cada checkpoint do desafio
└── <dominio>/<slug>/               ← item de catálogo reusável
    ├── prompt.md                   ← prompt parametrizável + front-matter
    └── README.md                   ← documentação do item
```

Os itens são agrupados por **domínio/negócio** (`sre`, `data`, `seguranca`, `dev`…),
nunca pela técnica de construção.

## Checkpoints do desafio

| # | Título | Domínio | Resposta | Item de catálogo |
|---|--------|---------|----------|------------------|
| 01 | Triagem de saúde de pods (Kubernetes) | SRE | [checkpoint-01-triagem-pods.md](checkpoint-01-triagem-pods.md) | [sre/triagem-pods-kubernetes](sre/triagem-pods-kubernetes/) |
| 02 | _(a definir)_ | — | — | — |
| 03 | _(a definir)_ | — | — | — |
| 04 | _(a definir)_ | — | — | — |
| 05 | _(a definir)_ | — | — | — |
| 06 | _(a definir)_ | — | — | — |
| 07 | _(a definir)_ | — | — | — |
| 08 | _(a definir)_ | — | — | — |
| 09 | _(a definir)_ | — | — | — |
| 10 | _(a definir)_ | — | — | — |

## Catálogo de prompts por domínio

### SRE
- **[Triagem de saúde de pods (Kubernetes)](sre/triagem-pods-kubernetes/)** — recebe um
  snapshot de cluster e devolve a triagem com causa provável e próxima ação do plantão.


