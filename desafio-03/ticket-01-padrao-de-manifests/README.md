# Ticket 01: o padrão do Seraph que ninguém abre

Skill `manifests-metacortex`: empacota o *Padrão de Manifests da Metacortex* em dois
modos, **escrever** manifesto novo já no padrão e **conferir** manifesto existente.
O que é mecânico virou script. O que exige ler o projeto virou instrução.

## Estrutura

```
ticket-01-padrao-de-manifests/
├── skill/manifests-metacortex/       # a skill entregue (cópia instalada em ../.claude/skills/)
│   ├── SKILL.md                      # corpo: divisão de donos, dois modos, limites
│   ├── scripts/conferir_manifests.py # conferência determinística + chamada ao Trivy
│   ├── references/regras-da-casa.md  # regra → nível → quem confere → critério
│   ├── references/leitura-do-projeto.md # o que extrair do código e decisões recorrentes
│   ├── references/instalar-trivy.md
│   ├── assets/modelo-workload.yaml   # esqueleto do workload no padrão
│   └── assets/trivy-config-data/metacortex.yaml # lista de registries da casa p/ KSV-0125
├── fluxo-manual/                     # o fluxo rodado antes da skill (origem) + correções pós-revisão
├── revisao-critica.md                # revisão por subagente crítico e o que foi corrigido
└── execucoes/
    ├── 01-escrita-fake-shop/         # modo escrever, sessão limpa (versão anterior da skill)
    ├── 02-conferencia-nyx/           # modo conferir, sessão limpa (versão anterior da skill)
    └── 03-escrita-encontros-tech/    # teste de generalização, skill corrigida
```

## Origem

- **De qual fluxo nasceu.** De uma sessão de trabalho real no Claude Code, registrada
  em `fluxo-manual/README.md`. O fluxo foi: rodar o Trivy puro sobre o manifesto
  barrado; configurar o Trivy com a lista de registries da casa e testar casos de borda;
  escrever o script só para o que o Trivy não cobre; ler o kube-news e o fake-shop
  (código e configuração da imagem publicada); escrever os manifests do fake-shop
  até o script sair limpo; rodar controles negativos no script. **Todo o fluxo foi rodado
  pelo agente**, com o humano definindo o objetivo, e não passo a passo à mão. A escrita
  do fake-shop foi feita de uma vez, depois de o script existir.
- **Por qual caminho.** Meta, não manual (aula 06-04): a janela de contexto com o
  fluxo executado foi destilada com o `/skill-creator`, como na aula 06-07. Foi o agente
  que o invocou, pedindo "modo brainstorm", mas **não houve turno de brainstorm com o
  humano**: o SKILL.md saiu direto das decisões do fluxo. O script veio do próprio fluxo, e o corpo e as referências vieram das decisões
  tomadas nele.
- **Com qual ferramenta.** Claude Code 2.1.282, modelo Opus 5.5, `skill-creator`; Trivy
  0.74.0; Python 3.14 + PyYAML.

## Execuções

Cada modo rodou numa sessão limpa (`claude -p`, diretório `desafio-03/`, sem o contexto
de criação), com pedido em linguagem natural e sem citar a skill. O prompt, a
transcrição (`transcricao.jsonl`) e a saída estão em cada pasta.

| Execução | Disparo | Turnos | Tempo | Custo | Resultado do script |
|---|---|---|---|---|---|
| Escrever: fake-shop em `orion-prod` | sozinha, pelo pedido | 29 | 163 s | US$ 1,08 | código 0: 18 OK, nada barra nem pede justificativa |
| Conferir: manifesto barrado do nyx | sozinha, pelo pedido | 22 | 151 s | US$ 0,83 | barrado: código 1 (11 barram, 2 justificar); corrigido: código 0 (só a 1.5 pede justificativa, falta o dono) |
| Escrever: encontros-tech em `helio-stg` (generalização, skill corrigida, sem dono/imagem no prompt, só permissões da skill) | sozinha, pelo pedido | 43 | 200 s | US$ 1,25 | código 0: 14 OK, 1.5 justificar (dono não informado), 3 não se aplicam (regras de prod); 8 negações de permissão |

Os resultados foram reconferidos fora da sessão da skill, rodando o script de novo
(`conferencia-independente.md`, `saida-script-barrado.md`, `saida-script-corrigido.md`).

### Modo escrever: `execucoes/01-escrita-fake-shop/`

Entregou `manifests/fake-shop.yaml` (ServiceAccount, ConfigMap, Deployment, Service e
PDB), `manifests/fake-shop-migracao.yaml` (ServiceAccount e Job) e `relatorio.md` com as
decisões, cada uma com `arquivo:linha`. As decisões que o ticket dizia não terem
resposta óbvia:
- **Probes sem endpoint de saúde:** liveness em `/metrics` (não toca no banco);
  readiness em `/shop` (depende do banco e do schema, então o pod só entra no Service
  depois da migração).
- **Migração no start:** saiu do `entrypoint.sh` para um Job versionado. O `command` do
  Deployment ficou só com o gunicorn, que assim vira PID 1 e trata SIGTERM. O
  `entrypoint.sh` original tem `bash` como PID 1.
- **Senha do banco:** vai por `secretKeyRef`. O comando para criar o Secret está no
  relatório, fora do Git. Nesta execução, o banco de prod ficou como "o da plataforma": essa premissa foi uma regra que eu inventei na skill e que **foi removida** depois da revisão crítica (ver "Revisão crítica e correções").

Comparado com a escrita manual do fluxo (`fluxo-manual/03`), as decisões são as
mesmas. **Isso não prova o método:** a referência `leitura-do-projeto.md` daquela versão
já trazia as respostas deste projeto e do kube-news, e o prompt entregou dono e digest.
O teste de generalização é a execução 03 (encontros-tech). As diferenças defensáveis são o nome `fake-shop` em vez de `orion-web`,
`DB_HOST` no Secret em vez de no ConfigMap e uma ServiceAccount própria para o Job. A
skill achou o que a escrita manual não achou: o checkout fecha o pedido aberto de
**outro** cliente, IDOR em `/update_quantity`/`/remove_item`, número de cartão e CVV
gravados em texto puro, `secret_key` fixa no código e o seed do catálogo de demonstração
rodando em prod.

### Modo conferir: `execucoes/02-conferencia-nyx/`

Entregou `conferencia.md` (veredito BARRA, tabela por regra, conferência do projeto com
evidência, pendências P1–P10) e `nyx-corrigido.yaml`. Leu o kube-news para decidir o que
o YAML não diz:
- **Probes:** `/health` não consulta banco e pode ser liveness. `/ready` existe, mas só
  olha um temporizador, então vira pendência para o time.
- **`DATABASE_URL` não é lida pela aplicação,** que lê `DB_*` e cai em `localhost` com
  senha fixa. É o defeito mais grave, e nenhuma regra do padrão o pega.
- **Sem handler de SIGTERM,** com `node` como PID 1. `sequelize.sync({alter:true})` roda
  em cada réplica no start.
- **Endpoints de caos expostos:** `PUT /unhealth` e `/unreadyfor`.
- **A senha já está no histórico do Git:** não basta tirá-la do arquivo, é preciso
  rotacionar.

### Teste de generalização: `execucoes/03-escrita-encontros-tech/`

Rodado depois da revisão crítica (`revisao-critica.md`), com a skill corrigida e a
referência sem as respostas dos projetos anteriores. O encontros-tech não passou pelo
fluxo manual. O prompt não trouxe dono nem imagem, e a sessão teve só as permissões do
`allowed-tools`, mais leitura e escrita. A skill:
- gerou aplicação e PostgreSQL (StatefulSet no padrão, PVC, `emptyDir` para socket e
  nss_wrapper), já pela regra corrigida do banco;
- escolheu a readiness `/api/events/?limit=1` com a barra final, porque sem ela o Flask
  devolve 308 e o kubelet conta o redirect como sucesso;
- percebeu que `create_all` no import torna inútil um Job de migração e levou isso
  para pendência de código antes de prod;
- não inventou dono nem imagem: usou a tag `pendente-loom`, que o script não barra
  (achado baixo da revisão);
- achou no código `error.html` inexistente, `edit_token` logado em INFO e `SECRET_KEY`
  fixa.

Custo do envelope restrito: **8 negações de permissão** (comando composto com `cd &&`,
`curl` para a imagem de origem, `trivy config` avulso). A skill terminou mesmo assim,
mas o `allowed-tools` e a referência precisam se alinhar (achado médio M1, não
corrigido).

### O que as execuções mudaram na skill

Nenhuma das duas sessões inspecionou a imagem de origem no Docker Hub. A de escrita
tentou só `registry.metacortex.io`, que não resolve fora do parque, e deixou `User` e
`WorkingDir` como pendência. No fluxo manual, essa inspeção pela API do registry foi o
que confirmou uid 10001 e `WORKDIR /app`. Correção aplicada em
`references/leitura-do-projeto.md`: inspecionar a imagem de origem pela API do registry,
com o comando pronto. As execuções acima **não** foram refeitas depois desse ajuste.

Um ponto deixei como está: na conferência, a skill usou a tag `:PENDENTE-TAG-LOOM` por
não saber a versão publicada. Nem o script nem o Trivy barram isso. É uma escolha
consciente dela (falha em `ImagePullBackOff` em vez de subir imagem errada), registrada
como pendência P3.

## Curadoria

### Onde passa a linha entre script e instrução

A regra usada foi: **se o YAML sozinho responde, é script; se a resposta está no código
da aplicação, é instrução.** E, dentro do que é script, **o que o Trivy já faz não se
reimplementa**. Isso foi medido rodando o Trivy, não suposto (`fluxo-manual/01` e `02`).

| Dono | Regras | Por quê |
|---|---|---|
| Trivy | 2.1, 3.1, 3.2, 3.6 | o catálogo KSV cobre as mesmas exigências; reimplementar duplicaria veredito |
| Script | 1.1–1.6, 2.2 (presença), 2.3, 2.4, 2.5, 3.3, 3.4, 3.5, 3.7 | é da Metacortex (nomes, rótulos, namespace, prod) ou o Trivy erra: não acha a senha em URL (3.3), deixa passar a ausência de `automountServiceAccountToken` (3.4) e não vê imagem sem registry explícito (3.7) |
| Instrução | 2.1 (tamanho), 2.2 (alvo), 2.6, 3.2 (caminhos de escrita), 3.3 (o que é sensível), 3.4 (fala com a API?) | só o código diz; o script lista cada item como pendência em "Conferência que exige ler o projeto", para que ninguém esqueça de fazer |

Duas decisões de fronteira:
- **1.4 (seletor) ficou no script**, mesmo sendo a regra "silenciosa". Cruzar Service e
  template é mecânico, e é exatamente o que olho humano não pega.
- **A KSV-0125 do Trivy roda configurada, mas não responde pela 3.7.** Ela entra como
  evidência. A KSV-01010 (segredo em ConfigMap) ficou só como informativo porque marcou
  `DB_PORT` como sensível.

O script devolve **veredito por regra** (`BARRA`, `JUSTIFICAR`, `OK`, `NAO_VERIFICADO`,
`NAO_SE_APLICA`), não uma lista crua de achados. O código de saída serve para pipeline:
0 passa, 1 barra, 2 erro de uso, 3 incompleto. Sem Trivy, ele não finge conformidade:
as regras do Trivy saem `NAO_VERIFICADO` e o código é 3.

### O que ficou no corpo e o que foi para arquivo

- **Corpo (`SKILL.md`, ~100 linhas):** quem é dono de quê, preflight, os dois modos
  passo a passo, formato do relatório e limites. É o que vale em todo disparo.
- **`references/regras-da-casa.md`:** a tabela das 19 regras com critério. É lida
  quando o agente precisa explicar ou decidir uma regra, não em todo disparo.
- **`references/leitura-do-projeto.md`:** o que extrair do código e as decisões que se
  repetem (sem endpoint de saúde, migração no start, `emptyDir`, SIGTERM). Só o modo
  escrever e o passo 2 do modo conferir precisam dela.
- **`references/instalar-trivy.md`:** só quando o Trivy falta.
- **`assets/`:** o modelo de YAML (saída, não instrução) e a configuração do Trivy
  (dado do script).

Todas as referências estão a um nível do `SKILL.md`, com nome descritivo. As mais
longas têm sumário.

### O que decidi não empacotar

- **Bloco 4 inteiro (vocabulário).** Não é regra, foi escrito para humano chegando na
  plataforma, e o modelo já sabe o que é Pod, Service e probe. Carregá-lo a cada disparo
  seria custo sem ganho (dica 1 da aula 06-11). A única frase útil dele (ausência do
  campo de endereços em Endpoints) é assunto de triagem de cluster, não de manifesto.
- **Histórico da página.** Só o estado atual vale. A 3.4 entrou já como obrigatória.
- **Regras sem dono verificável:** "tag imutável" além de `:latest` (tag `stable` é
  mutável, mas nada no YAML diz isso) e `metacortex.io/runbook` ("quando existir").
- **Aplicar no cluster.** A skill escreve e confere arquivo. Subir é outro fluxo, e a
  triagem do Ticket 02 é outra skill.

### Permissões que a skill pede

`allowed-tools: Read, Grep, Glob, Write, Edit, Bash(python3 *conferir_manifests.py*),
Bash(python *conferir_manifests.py*), Bash(trivy --version)`

- Leitura e busca livres: o trabalho é ler projeto e manifesto.
- Escrita: o modo escrever grava YAML.
- Bash **só** para o script da skill e para checar a versão do Trivy. O script chama o
  Trivy por dentro, então a skill não precisa de `Bash(trivy *)` genérico.
- **Não** pede `kubectl`, `helm` nem rede. Instalar o Trivy é proposta ao usuário, não
  ação da skill. Nas execuções de teste, `kubectl` estava explicitamente negado
  (`--disallowedTools "Bash(kubectl *)"`).
- A invocação fica aberta ao modelo e ao usuário: conferir é o uso frequente e precisa
  disparar pelo pedido natural ("revisa esse deployment").

## Pendências que atravessam para os próximos tickets

- `registry.metacortex.io` não existe fora do enunciado. Para subir os manifests num
  cluster local (Ticket 04), a imagem precisa de um espelho local ou de uma
  sobrescrita só de laboratório, registrada como desvio da 3.7.
- Os manifests de `orion-prod` (execução 01) não trazem banco. Para o par aplicação +
  banco do Ticket 04, use a execução 03 (encontros-tech em `helio-stg`) ou gere o
  fake-shop de novo em `stg` com a skill corrigida.
