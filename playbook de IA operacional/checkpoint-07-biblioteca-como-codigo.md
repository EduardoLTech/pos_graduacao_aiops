# Checkpoint 07 — A biblioteca vira código

> Playbook de IA Operacional da Aegis — Meta/organização. Consolida os itens dos
> checkpoints 01–06 num ativo versionado e tratado como código, com um contrato de
> convenções (`CLAUDE.md`) que faz a biblioteca sobreviver à saída de qualquer pessoa
> do time.

## 1. Decisões de método

**A dor.** O Nick Fury não aceita a coleção de prompts espalhada e informal: o playbook
precisa virar um **ativo versionado**, com estrutura, nomenclatura e fluxo de mudança
previsíveis — algo que qualquer engenheiro pegue e confie, e que não dependa de quem
escreveu. A referência de estrutura é o template
[`prompt-registry`](https://github.com/fabricioveronez/prompt-registry): categorias como
pastas, um prompt por pasta (`prompt.md` + `README.md`), frontmatter com metadados,
versionamento por `versao` + commits semânticos.

**A decisão central — adotar as convenções in-place, não forkar um repo paralelo.** Os
itens 01–06 já nasceram, ao longo do playbook, na forma que o template propõe:
`<dominio>/<slug>/` com `prompt.md` parametrizado (`{{placeholders}}`) + `README.md`
documentado + frontmatter, tudo sob Git. Manter um segundo repositório forkado só do
template criaria **duas fontes da verdade** para os mesmos prompts — o oposto do que o
versionamento resolve. A escolha curada foi **fixar as convenções no próprio repositório
do playbook** e materializá-las num contrato explícito, em vez de duplicar os arquivos.

**O artefato central da entrega é o [`CLAUDE.md`](CLAUDE.md).** É ele que transforma
convenção implícita em contrato: descreve a estrutura de pastas, o schema do frontmatter,
a regra de organização por domínio, as variantes de item (cadeia encadeada; ciclo de
verificação/refino), a manutenção dos índices, o versionamento e os commits semânticos.
Um arquivo de convenções é, de fato, o mecanismo que faz a biblioteca "sobreviver à saída
de qualquer pessoa" — o objetivo que o Fury cobra.

**Mapa das convenções do template → como o playbook as satisfaz.**

| Convenção do `prompt-registry` | Como o playbook cumpre |
|---|---|
| Categoria = pasta na raiz, kebab-case, uma por domínio, sem aninhar | `sre/`, `arquitetura/`, `data/`, `seguranca/` — por **negócio**, nunca por técnica |
| Um item por pasta, nomeada pelo resultado (não pela técnica) | `triagem-pods-kubernetes/`, `endurecer-networkpolicy/`, … (nunca `chain-of-thought/`) |
| `prompt.md` = frontmatter + texto puro com `{{placeholders}}` | idêntico; parâmetros como `{{snapshot}}`, `{{alerta}}`, `{{manifesto}}`… |
| `README.md` = mesmo frontmatter + documentação humana | idêntico; objetivo, casos de uso, exemplo, limitações |
| Frontmatter com `nome`, `descricao`, `versao` (semver), `tags`, `inputs` | superconjunto: acrescenta `dominio`, `quando_usar`, `modelo_recomendado`, `framework` |
| `versao` inicia em `1.0.0`; muda por commit semântico | itens em `1.0.0` (triagem em `1.1.0` após evolução registrada no changelog) |
| Índices nos READMEs mantidos | `README.md` raiz com tabela de checkpoints + catálogo por domínio |
| Commits semânticos com escopo na categoria | `feat(sre): …`, `feat(seguranca): …` |

**Divergências conscientes (curadoria, não descuido).** Duas, ambas documentadas no
`CLAUDE.md`:
1. **Organização por domínio de negócio** (`sre/`, `data/`, `seguranca/`, `arquitetura/`)
   em vez de colapsar tudo na categoria única `devops/` do template. A regra de ouro de
   organização é agrupar por **área/funcionalidade** — e domínios distintos dão índices
   mais navegáveis para um time que cresce.
2. **Frontmatter mais rico** que o mínimo do template. Os campos extras (`dominio`,
   `framework`, `modelo_recomendado`, `quando_usar`) carregam rastreabilidade que a
   operação usa (qual técnica sustenta o item, com que modelo executar). O limite é a
   regra prática: se organizar o metadado custasse mais que criar o prompt, seria
   burocracia — não é o caso aqui.

## 2. Entregável

**Repositório.** O playbook vive versionado em
`github.com/EduardoLTech/pos_graduacao_aiops`, na pasta `playbook de IA operacional/`. O
template `prompt-registry` foi clonado como referência das convenções
(`github.com/EduardoLTech/prompt-registry`); as convenções foram adotadas no repositório
do playbook, e não num fork paralelo — pela decisão de fonte única acima.

**Contrato de convenções.** [`CLAUDE.md`](CLAUDE.md) — o artefato que formaliza a
biblioteca como código.

**Um item já no formato completo, como exemplo dos demais:**
[`sre/triagem-pods-kubernetes/`](sre/triagem-pods-kubernetes/)

- [`prompt.md`](sre/triagem-pods-kubernetes/prompt.md) — frontmatter + o prompt com os
  placeholders `{{snapshot}}`, `{{namespace}}`, `{{contexto_extra}}`.
- [`README.md`](sre/triagem-pods-kubernetes/README.md) — o mesmo frontmatter + objetivo,
  como usar, parâmetros, casos de uso validados, limitações e changelog.

Frontmatter do exemplo (o mesmo bloco encabeça os dois arquivos):

```yaml
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
versao: 1.1.0
framework: RISE + Example (CARE)
tags: [kubernetes, sre, triagem, oncall, troubleshooting]
---
```

**Catálogo migrado (os seis itens dos checkpoints 01–06).**

| # | Item | Domínio | Formato |
|---|---|---|---|
| 01 | [`triagem-pods-kubernetes`](sre/triagem-pods-kubernetes/) | sre | `prompt.md` + `README.md` |
| 02 | [`nota-triagem-padronizada`](sre/nota-triagem-padronizada/) | sre | `prompt.md` + `README.md` |
| 03 | [`analise-causa-raiz`](sre/analise-causa-raiz/) | sre | `prompt.md` + `README.md` |
| 04 | [`decisao-arquitetural-tradeoff`](arquitetura/decisao-arquitetural-tradeoff/) | arquitetura | `prompt.md` + `README.md` |
| 05 | [`migracao-incremental-encadeada`](data/migracao-incremental-encadeada/) | data | cadeia de 3 elos + `README.md` |
| 06 | [`endurecer-networkpolicy`](seguranca/endurecer-networkpolicy/) | seguranca | geração + verificação + refino + `README.md` |

## 3. Verificação da estrutura

Este item não produz saída de modelo — o entregável é a **estrutura do repositório**, não
a execução de um prompt. O que foi verificado:

- os seis itens existem, cada um com `prompt.md` (frontmatter + corpo) e `README.md`
  (mesmo frontmatter + documentação);
- o `README.md` raiz indexa checkpoints e catálogo por domínio de forma consistente;
- placeholders do corpo batem com o `inputs` do frontmatter em cada item;
- o `CLAUDE.md` descreve as convenções **realmente** praticadas (incluindo as variantes de
  cadeia e de ciclo de verificação/refino), sem contradizer os arquivos.

## 4. Curadoria

**A decisão honesta que registro.** O pedido literal listava, como primeiro entregável, "o
link de um repositório forkado do template". A curadoria substituiu isso por **adotar as
convenções do template no próprio repositório do playbook** — para não criar duas fontes
da verdade dos mesmos prompts. É uma troca deliberada, não uma lacuna: o valor cobrado
(biblioteca versionada, tratada como código, que sobrevive à rotatividade) está entregue
no `CLAUDE.md` + na estrutura já versionada. O fork do template permanece disponível como
referência das convenções, caso o time decida publicar o catálogo no layout enxuto do
`prompt-registry` (categoria única `devops/`, frontmatter mínimo).

**O que a formalização fixou.** Antes, as convenções estavam implícitas e espalhadas pelo
`README.md`; agora há um contrato único (`CLAUDE.md`) que um novo integrante — ou uma
ferramenta — lê para entender onde um item vive, que campos ele carrega e como versioná-lo.
Esse é o salto de "pasta de prompts" para "ativo de engenharia".

**Ganchos para os próximos itens.** Com a biblioteca fixada como código, o passo natural é
o **fluxo de avaliação**: rubrica por item (a triagem já sugere as 4 perguntas — causa
correta? sinal citado? ação segura? reconheceu o saudável?), casos golden-answer e uma
pipeline que rode os prompts em PR antes do merge. É o que fecha o ciclo "prompt como
código": mudou o prompt, a avaliação valida antes de entrar na principal.
