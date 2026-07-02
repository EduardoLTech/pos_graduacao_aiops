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
├── CLAUDE.md                       ← contrato de convenções da biblioteca (estrutura, frontmatter, git)
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
| 02 | Nota de triagem padronizada (alertas) | SRE | [checkpoint-02-nota-triagem-padronizada.md](checkpoint-02-nota-triagem-padronizada.md) | [sre/nota-triagem-padronizada](sre/nota-triagem-padronizada/) |
| 03 | Causa-raiz da degradação no Cerebro | SRE | [checkpoint-03-causa-raiz-cerebro.md](checkpoint-03-causa-raiz-cerebro.md) | [sre/analise-causa-raiz](sre/analise-causa-raiz/) |
| 04 | Segurando a sobrecarga do Relay (backpressure) | Arquitetura | [checkpoint-04-backpressure-relay.md](checkpoint-04-backpressure-relay.md) | [arquitetura/decisao-arquitetural-tradeoff](arquitetura/decisao-arquitetural-tradeoff/) |
| 05 | Migrando o Forge de lote para tempo real | Data | [checkpoint-05-migracao-forge-streaming.md](checkpoint-05-migracao-forge-streaming.md) | [data/migracao-incremental-encadeada](data/migracao-incremental-encadeada/) |
| 06 | Endurecendo a NetworkPolicy do Sentinel | Segurança | [checkpoint-06-networkpolicy-sentinel.md](checkpoint-06-networkpolicy-sentinel.md) | [seguranca/endurecer-networkpolicy](seguranca/endurecer-networkpolicy/) |
| 07 | A biblioteca vira código | Meta | [checkpoint-07-biblioteca-como-codigo.md](checkpoint-07-biblioteca-como-codigo.md) | [CLAUDE.md](CLAUDE.md) (contrato de convenções) |
| 08 | Testes determinísticos com promptfoo | Avaliação | [checkpoint-08-testes-determinsticos-promptfoo.md](checkpoint-08-testes-determinsticos-promptfoo.md) | `promptfooconfig.yaml` nos 3 itens de saída estruturada |
| 09 | Gate de qualidade com LLM-as-judge | Avaliação | [checkpoint-09-gate-llm-as-judge.md](checkpoint-09-gate-llm-as-judge.md) | juiz + rubrica em [sre/analise-causa-raiz](sre/analise-causa-raiz/) |
| 10 | _(a definir)_ | — | — | — |

## Catálogo de prompts por domínio

### SRE
- **[Triagem de saúde de pods (Kubernetes)](sre/triagem-pods-kubernetes/)** — recebe um
  snapshot de cluster e devolve a triagem com causa provável e próxima ação do plantão.
- **[Nota de triagem padronizada (alertas)](sre/nota-triagem-padronizada/)** — recebe um
  alerta cru e devolve a nota de triagem no padrão único de plantão (cinco campos fixos).
- **[Análise de causa-raiz de degradação (cross-artefato)](sre/analise-causa-raiz/)** —
  recebe config + métricas + logs e raciocina até a causa-raiz (não o sintoma), com a
  cadeia causal evidenciada, mitigação imediata e correção definitiva.

### Arquitetura
- **[Decisão de engenharia com trade-offs (múltiplos caminhos)](arquitetura/decisao-arquitetural-tradeoff/)**
  — recebe o cenário (estado + restrições) e compara vários caminhos defensáveis,
  pesando trade-offs contra critérios e restrições inegociáveis, antes de recomendar
  (um caminho ou combinação faseada) com o raciocínio à mostra.

### Segurança
- **[Endurecimento de NetworkPolicy (default-deny)](seguranca/endurecer-networkpolicy/)**
  — recebe um manifesto de NetworkPolicy permissivo + as regras do padrão + o mapa de
  serviços e produz a versão endurecida (default-deny explícito, ingress/egress
  mínimos, comentário por regra), submetida a um ciclo de **verificação e refino**
  (Chain-of-Verification factor-revise): geração → auditoria isolada → v2, até aprovar.

### Data
- **[Migração incremental — cadeia de prompts encadeados](data/migracao-incremental-encadeada/)**
  — cadeia de três elos (diagnóstico → plano faseado least-to-most → runbook por fase)
  para planejar uma migração grande (ex.: lote → orientado a eventos) em passos
  reversíveis e sem big-bang, com gate entre os elos.


