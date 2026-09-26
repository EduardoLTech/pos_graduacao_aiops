# Revisão crítica do Ticket 01

Revisão feita em 2026-09-24 pelo subagente `critical-code-analyst` (Claude Code, Opus 5.5),
a pedido do autor, depois da primeira entrega. O revisor só leu e rodou testes: não
escreveu na entrega. Os casos de teste dele ficaram fora do repositório.

Abaixo, os achados e o que foi feito com cada um. Estado: **críticos, altos e médios M1–M4
corrigidos**, e também os achados da revisão focada do delta (seção no fim), menos o B4,
que foi aceito. O M5 (narrativa) foi ajustado no README. Os baixos estão registrados e **não**
foram corrigidos.

## Veredito do revisor

> Tem problema material, mas é corrigível. A ordem do fluxo é real: o Trivy rodou antes do
> script, e o script antes do SKILL.md. As decisões de projeto nos manifests se sustentam.
> Três coisas pesam contra: o script dá "OK" e código 0 para regras do Trivy sem ter
> conferido nada; as duas execuções medem reprodução do que já estava na skill, não
> generalização; e a regra "banco da plataforma em prod" foi inventada e contradiz o
> Ticket 04. Eu não entregaria como está.

## Altos: corrigidos

| # | Achado (provado pelo revisor) | Correção | Evidência da correção |
|---|---|---|---|
| A1 | As regras 2.1, 3.1, 3.2 e 3.6 saíam OK sem nenhum workload. Um `values.yaml` sem objeto saía com código 0. Um `kind: List` com `nginx:latest` e senha literal passava nessas regras, porque nem o script nem o Trivy expandem `items` | O script expande `List.items`. Arquivo sem objeto de Kubernetes sai com código 2. As regras do Trivy só viram OK se havia container que ele leu: sem workload saem `NAO_SE_APLICA`, com workload dentro de List saem `NAO_VERIFICADO` | `fluxo-manual/05-correcoes-pos-revisao/`: `values.yaml` → código 2; `list.yaml` → 3.3 e 3.7 BARRA, regras do Trivy NAO_VERIFICADO; ConfigMap sozinho → NAO_SE_APLICA. Regressão: barrado 1, fake-shop 0, nyx-corrigido 0, `--sem-trivy` 3 |
| A2 | As execuções provavam reprodução, não o método. `leitura-do-projeto.md` trazia as respostas dos dois projetos, e o prompt da escrita entregou dono e digest | A referência ficou genérica: saíram `sequelize.sync`, `/unhealth`, `/metrics`, `/tmp/metrics`, gunicorn e `PROMETHEUS_MULTIPROC_DIR`, e ficaram os padrões de decisão. Nova execução no **encontros-tech**, projeto que não entrou no fluxo, **sem dono nem imagem** no prompt e com a sessão restrita às permissões da skill | `execucoes/03-escrita-encontros-tech/`: código 0 no script. Decisões próprias do projeto (readiness `/api/events/?limit=1` com a barra final, `create_all` no import, `error.html` inexistente). Dono e imagem ficaram como pendência, não inventados |
| A3 | "Banco da plataforma em prod" era uma política inventada e contradizia o Ticket 04, que pede o par aplicação + banco | A regra saiu do `SKILL.md`. Agora a skill gera o banco junto (StatefulSet no padrão), a menos que o usuário informe um banco existente. Em prod, a réplica única é tratada como exceção à 2.3, que Segurança precisa aprovar, sem contornar a regra | `SKILL.md`, seção Limites. A execução 03 gerou o `encontros-tech-postgres.yaml` |

As execuções 01 e 02 ficaram como estavam. Os dois modos foram refeitos com a skill
corrigida: a escrita nas execuções 03 e 04, e a conferência na 05, sobre o mesmo nyx da 02.
As duas antigas são o registro do que a skill produziu na
versão anterior. O README aponta onde elas dependiam da regra removida.

## Médios

- **M1 Permissões: corrigido em 2026-09-25.** As execuções 01 e 02 rodaram com mais
  permissões que o `allowed-tools`. A execução 03 rodou no envelope da skill e teve
  **8 negações**, entre elas uma chamada do próprio script feita com `cd ... &&`, o
  `curl` para inspecionar a imagem de origem e o `trivy config` avulso. A referência
  mandava usar `curl`, que o `allowed-tools` não concede.
  *Correção:*
  - `scripts/inspecionar_imagem.py` substitui o `curl`;
  - `--verificar-ambiente` faz o preflight;
  - a mensagem do Trivy passa a sair no relatório;
  - o SKILL.md manda usar um comando por chamada.

  *Evidência:* `execucoes/04-escrita-fake-shop-stg/`, no mesmo envelope: 0 negações, e a
  imagem de origem foi inspecionada dentro da skill.

M2 a M4 foram corrigidos em 2026-09-25. Os casos que reproduzem cada um estão em
`fluxo-manual/06-correcoes-medios/`: `antes.md` e `depois.md` saem do mesmo
`rodar-casos.sh`.

- **M2 KSV-0125: corrigido.** Com o `trivy-config-data` vazio, a KSV-0125 barrava a 3.7
  pelo mapeamento, o que contradiz "KSV-0125 é só evidência". Ela saiu do mapeamento. Se
  o script já barrou a 3.7, ela vira evidência dentro do achado; se não barrou, aparece
  só como informativo. Execução 04 com a lista vazia: antes código 1 (3.7 BARRA), depois
  código 0, com a KSV-0125 listada como informativo.
- **M3 Codificação: corrigido.** Arquivo em UTF-16 ou Latin-1 dava traceback com código 1,
  o mesmo de "barra". Agora UTF-8 com ou sem BOM e UTF-16/32 com BOM são lidos. Outra
  codificação sai com código 2 e mensagem pedindo a conversão. **Achado da correção:**
  o Trivy lê UTF-16 sem erro e sem achado nenhum, então as regras dele sairiam OK sem
  conferência (a classe da A1). O `trivy-direto.md` mostra isso: o mesmo manifesto dá 3
  falhas em UTF-8 e 0 em UTF-16. O Trivy passou a receber sempre uma cópia em UTF-8
  (gravada em bytes; ver C1 abaixo). O caso `m3-utf16-com-latest.yaml` prova isso: 3.1 e
  3.2 barram.
- **M4 Heurística de segredo: corrigido.** O script não pegava senha em `args`, `DB_PWD`
  nem senha em comentário sem URL, barrava `TOKEN_TTL` por engano e a 2.5 aceitava PDB
  com `minAvailable: 0`. Depois da correção (já com os ajustes da revisão do delta, A1,
  M1 e B5 abaixo):
  - flag de credencial com valor literal em `command`/`args` barra, inclusive dentro de
    `sh -c "..."` e com flag e valor no mesmo elemento. `$(VAR)` não barra. O nome da
    flag é comparado por palavra e com os mesmos sufixos de parâmetro do `env`
    (`--token-ttl`, `--password-file`, `--no-password`, `--passive` não barram). `-p` fica
    de fora;
  - `_PWD` entra no nome sensível (`PWD` sozinho, o diretório corrente, não);
  - sufixos de parâmetro (`_TTL`, `_TIMEOUT`, `_FILE`, `_HEADER`...) saem do nome
    sensível;
  - PDB com `minAvailable` < 1 ou `maxUnavailable` ≥ réplicas conta como ausente
    (percentual arredondado para cima, como o Kubernetes faz).

  A credencial em comentário sem URL virou **pendência, não barra**: "senha: vem do
  Secret x" casaria com a mesma regex. É heurística de nome, e o que é sensível continua
  sendo decisão de quem lê.

O M5 continua registrado e **não** corrigido no código, porque é narrativa, já ajustada no
README.

## Revisão focada do delta (2026-09-25)

O subagente `critical-code-analyst` revisou só o que mudou desde o commit da primeira
entrega: M1, M2 a M4 e `inspecionar_imagem.py`. Veredito: "não pode ser commitado como
está". Todos os achados foram corrigidos antes do commit, e os casos novos entraram em
`fluxo-manual/06-correcoes-medios/casos/`.

| # | Achado (provado pelo revisor) | Correção | Evidência |
|---|---|---|---|
| C1 crítico | A cópia UTF-8 para o Trivy era gravada com `write_text`. No Windows, CRLF virava `\r\r\n`, o Trivy só lia o primeiro documento e as regras dele saíam OK para o resto (classe da A1). Com `core.autocrlf=true`, todo checkout gera CRLF | `write_bytes` | `m3-crlf-varios-documentos.yaml` (Deployment no 4º documento): 3.1 e 3.2 barram. `trivy-direto.md`: `\r\r\n` → 0 falhas |
| A1 alto | A regex de flag casava substring e não excluía parâmetro: `--token-ttl`, `--password-file`, `--passive`, `--tokenizer` barravam | nome da flag comparado por palavra, com os sufixos de parâmetro do `env` e `--no-*` fora | `m4-args-parametros-ok.yaml` → 3.3 OK |
| M1 médio | `sh -c "app --db-password x"` e `"--password abc"` num elemento só passavam | cada elemento quebrado com `shlex.split` antes da checagem | `m4-args-sh-c.yaml` → 3.3 BARRA |
| M2 médio | O Bearer ia junto no redirect para outro host: `registry.k8s.io` devolvia 401, e o token anônimo do Docker Hub chegava à CDN | `add_unredirected_header` | `registry.k8s.io/pause:3.9` → código 0 |
| B1 baixo | Resposta fora do formato (token sem JSON, sem `realm`, schema1, `platform` ausente, `last_updated` nulo) gerava traceback com código 1 | tratadas como NAO VERIFICADO, código 3 | reproduzido depois com registry simulado: 10 de 10 cenários sem traceback (`fluxo-manual/07-verificacoes-pendentes/saida-b1.md`) |
| B2 baixo | A variante da plataforma era ignorada (`linux/arm/v7`) | comparação com a variante | `nginx:stable --plataforma linux/arm/v7` → digest da v7 |
| B3 baixo | A pendência de comentário repetia a credencial no relatório | a pendência cita só `arquivo:linha` | `m4-senha-em-comentario.yaml` |
| B4 baixo | `ENV_PARAMETRO` deixa passar `GITHUB_TOKEN_ENABLED=ghp_xxx` | **não corrigido**: aceito e documentado; é heurística de nome | — |
| B5 baixo | `env` barrava `$(VAR)`, `args` não | mesmo critério nos dois, e só a expansão inteira conta (`$enh4!` continua literal) | `m4-env-expansao-ok.yaml` OK; `m4-env-dolar-literal.yaml` BARRA |

Afirmações que o revisor derrubou e foram reescritas:
- "os scripts imprimem o código de saída na última linha": não vale para erro de uso;
- "rede só pelo `inspecionar_imagem.py`": o Trivy baixa o bundle no primeiro uso;
- "0 negações" na execução 04: prova a lista passada por `--allowedTools`, não que o
  frontmatter sozinho baste.

Ficaram sem verificação, pelo revisor e por mim:
- o matcher do `allowed-tools`: se `Bash(python *inspecionar_imagem.py*)` casa
  `python -c "<código>" inspecionar_imagem.py`. É anterior ao delta, e o delta repetiu o
  padrão;
- o SSRF via `realm` do registry: só GET, ferramenta local, risco baixo;
- `%TEMP%` em drive diferente do repositório;
- execução em Linux e macOS.

Fechados depois, em 2026-09-25 (`fluxo-manual/07-verificacoes-pendentes/`):
- `%TEMP%` em outro drive: funciona nos dois sentidos;
- Linux: saída idêntica à do Windows nos 30 casos da regressão;
- o frontmatter sozinho só concede as permissões quando o usuário invoca a skill;
- o matcher **casava**: `python -c "<código>" <script>.py` passava. O padrão foi ancorado
  em `${CLAUDE_SKILL_DIR}/scripts/<script>.py`, e depois disso só o script passa.

Segue aberto: o SSRF via `realm`. macOS foi arquivado: não há máquina para testar.

- **M5 Narrativa da origem.** A "escrita à mão" do fake-shop foi um único Write do agente,
  depois do script. O `/skill-creator` em "modo brainstorm" não teve turno humano. Parte
  da evidência de `fluxo-manual/` foi gerada depois das execuções. A saída dos casos de
  borda da KSV-0125 foi apagada.

## Baixos: registrados, não corrigidos

- **Falsos positivos:** `kustomization.yaml` e `selector.matchExpressions`; automount
  desligado só na ServiceAccount também barra.
- **Leniências:** `runAsUser: 20000`, `maxSurge: 50%`, a tag placeholder
  (`:PENDENTE-TAG-LOOM`, `:pendente-loom`) sai com código 0, e a 2.4 não se aplica a
  StatefulSet.
- **Leitura estrita do padrão:** 1.3 exigida no template do pod, `instance == namespace` e
  `part-of == cliente`. Rótulos do `jobTemplate` do CronJob não são conferidos.
- **Generalização exagerada (texto corrigido em 2026-09-25):** a frase "KSV-0125 não
  dispara sem registry explícito" não se sustenta. Só o `nginx` sem organização escapou;
  `fabricioveronez/kube-news` disparou. `regras-da-casa.md` agora diz isso.
- **Secret do nyx:** o comando da conferência não aplica os quatro rótulos.
- **Description:** nunca passou por teste negativo nem de colisão com a skill de triagem do
  Ticket 02. *Testada em 2026-09-25 pela matriz de roteamento do Ticket 02
  (`../ticket-02-triagem-no-cluster/roteamento/`). As três frases de manifests caíram
  nela nas duas rodadas válidas, inclusive a de colisão ("revisa esse deployment antes
  de eu subir"), e as frases de cluster, conceito e VM não a carregaram.*
