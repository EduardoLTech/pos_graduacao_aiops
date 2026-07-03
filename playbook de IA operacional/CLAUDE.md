# CLAUDE.md

Guia para o Claude Code (claude.ai/code) e para qualquer engenheiro ao trabalhar neste
diretório — o **Playbook de IA Operacional da Aegis**.

## Propósito do repositório

Biblioteca de prompts **parametrizáveis**, versionada e tratada como código: cada item é
um prompt reusável que qualquer engenheiro do time pega, preenche os parâmetros e confia
no resultado. Não há código executável, build ou runtime — a qualidade é medida pela
clareza dos prompts, pela consistência da estrutura e pela rastreabilidade das versões.

As convenções aqui são compatíveis com o template público
[`prompt-registry`](https://github.com/fabricioveronez/prompt-registry) (pasta por
categoria, `prompt.md` + `README.md`, frontmatter, commits semânticos), com um frontmatter
mais rico adaptado à operação (campos `dominio`, `framework`, `modelo_recomendado`).

## Estrutura

```
playbook de IA operacional/
├── CLAUDE.md                       ← este contrato de convenções
├── README.md                       ← índice geral (checkpoints + catálogo por domínio)
├── checkpoint-NN-<slug>.md         ← resposta completa de cada item do desafio (método + execução + curadoria)
└── <dominio>/<slug>/               ← item de catálogo reusável
    ├── prompt.md                   ← frontmatter + texto puro do prompt (com {{placeholders}})
    └── README.md                   ← mesmo frontmatter + documentação humana
```

Regras de estrutura:

- **Domínio** = pasta na raiz, em kebab-case, por **área de negócio/funcionalidade**
  (`sre/`, `arquitetura/`, `data/`, `seguranca/`, `dev/`…) — **nunca pela técnica** de
  construção (proibido `chain-of-thought/`, `few-shot/`). Não aninhar domínios.
- **Item** = subpasta dentro de um domínio, nomeada pelo **resultado** que entrega
  (`triagem-pods-kubernetes/`, não `prompt-cot/`).
- **`prompt.md`** = frontmatter YAML + o texto do prompt, preservado integralmente. Nenhuma
  explicação sobre o prompt entra aqui — só metadados + o texto que será copiado e colado.
- **`README.md`** = o **mesmo frontmatter** do `prompt.md` seguido da documentação humana:
  objetivo, público-alvo, como usar, parâmetros, casos de uso validados e limitações.

### Variantes de item

- **Cadeia de prompts encadeados** (ex.: `data/migracao-incremental-encadeada/`): um arquivo
  por elo — `prompt-1-<papel>.md`, `prompt-2-<papel>.md`, … Cada elo tem seu próprio
  frontmatter, acrescido de `cadeia`, `elo`, `consome` e `produz` para deixar o fluxo
  explícito. O `README.md` documenta a cadeia inteira e o gate entre os elos.
- **Ciclo de verificação/refino** (ex.: `seguranca/endurecer-networkpolicy/`): o
  `prompt.md` é o elo de geração; prompts irmãos (`prompt-verificacao.md`, `prompt-refino.md`)
  cobrem a auditoria isolada e a revisão. O `README.md` documenta a volta completa.

## Frontmatter padrão

Bloco YAML no topo de `prompt.md` **e** de `README.md`, **idêntico nos dois arquivos**.

```yaml
---
nome: Nome humano do prompt
dominio: sre
objetivo: Uma ou duas linhas dizendo o que o prompt entrega e a partir de quê.
quando_usar: Em que situação o time pega este item, em uma ou duas linhas.
inputs:
  parametro_obrigatorio: O que este parâmetro representa.
  parametro_opcional: (opcional) O que representa; comportamento quando vazio.
modelo_recomendado: claude-sonnet-4-6 (execução); criado com claude-opus-4-8
versao: 1.0.0
framework: RISE + Example (CARE)   # framework/técnica de construção
tags: [dominio, acao, tecnica]
---
```

Regras dos campos:

- **`nome`** — título humano curto, capitalizado. Não é o slug da pasta.
- **`dominio`** — o mesmo da pasta pai.
- **`objetivo`** / **`quando_usar`** — o `objetivo` alimenta o índice; o `quando_usar` diz o
  gatilho de uso.
- **`inputs`** — um item por placeholder `{{...}}` do corpo. Chave = nome do parâmetro (sem
  `{{}}`); valor = descrição. Parâmetros opcionais começam com `(opcional)`.
- **`modelo_recomendado`** — modelo de execução recomendado (barato) e o de criação (forte).
  Filosofia: **criar com modelo forte, executar com modelo barato**.
- **`versao`** — semver `MAJOR.MINOR.PATCH`. Todo item **nasce em `1.0.0`**. Incrementar ao
  evoluir; registrar a mudança no `## Changelog` do `README.md`.
- **`framework`** — o framework/técnica que estrutura o prompt (RTF, TAG, BAB, CARE, RISE +
  técnica). É metadado de rastreabilidade; **não** vira critério de organização de pasta.
- **`tags`** — 3 a 5 termos livres (domínio, ação, técnica).

Nos itens de cadeia, acrescentar `cadeia`, `elo`, `consome`, `produz`.

## Ao adicionar ou alterar um item

1. Escolher o **domínio** existente que melhor encaixa antes de criar um novo.
2. Nomear a pasta pelo **resultado**, não pela técnica.
3. Manter o **corpo do prompt autocontido** — não referenciar o `README.md` nem outros
   arquivos; o prompt é extraído do contexto. O frontmatter é estrutura e não viola isso.
4. Placeholders no corpo usam `{{nome_variavel}}` e aparecem listados em `inputs` (mesma
   lista nos dois arquivos).
5. Toda causa/afirmação nos prompts precisa de sinal que a sustente; sem evidência, o item
   marca `indeterminado — coletar X` em vez de chutar. Reconhecer o caso saudável sem
   inventar problema.

## Manutenção da documentação

Toda inclusão ou alteração de item revisa, na mesma entrega:

1. **`README.md` do item** — objetivo, exemplo e limitações alinhados ao `prompt.md`;
   frontmatter idêntico ao do `prompt.md`.
2. **`README.md` da raiz** — tabela de checkpoints e catálogo por domínio atualizados.
3. **`CLAUDE.md`** — se a mudança criar um domínio, uma variante de item ou um campo de
   frontmatter novo, refletir aqui.

## Convenções de conteúdo

- Português (pt-BR), conciso, legível para quem está sob pressão de plantão.
- Os documentos são escritos na voz do engenheiro que curou a biblioteca. Justificativas de
  método citam o **conceito** (ex.: "o RISE é indicado para tarefas procedurais com input
  concreto") ou o `id` da referência interna — nunca a origem didática.

## Testes e CI

- **Todo item tem `promptfooconfig.yaml` na sua pasta** — o teste viaja junto com o prompt.
  Saída estruturada → asserts determinísticos (regex/contains/javascript + `latency`/`cost`);
  saída aberta → `llm-rubric` (rubrica de 4 critérios 0–2, corte ≥ 6, nenhum zerado, gerado
  e julgado em famílias distintas). O `rubrica-juiz.md` acompanha o config do juiz.
- **Não versionar** artefatos de execução (`*.json` de `--output`, `.last-eval.json`) — são
  saída de run, não fonte; ficam no `.gitignore`.
- O pipeline é `.github/workflows/promptfoo.yml`, **na raiz do repositório git** (o playbook
  é subpasta). Roda a suíte inteira a cada PR/push que toque o playbook e barra a regressão
  pelo exit code do `promptfoo eval`. Chaves em repo secrets, nunca no YAML. Ao adicionar um
  item, o `find . -name 'promptfooconfig.yaml'` já o inclui — sem editar o workflow.

## Git

- Commit semântico, mensagem de uma linha.
- Escopo do commit = o domínio (ex.: `feat(sre): adiciona prompt de triagem de pods`,
  `feat(seguranca): endurece NetworkPolicy com ciclo de verificação`).
- Fluxo GitHub Flow: branch por mudança, avaliação, PR, merge na principal.
