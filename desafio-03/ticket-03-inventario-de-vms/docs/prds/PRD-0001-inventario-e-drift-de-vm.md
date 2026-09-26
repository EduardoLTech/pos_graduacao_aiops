# PRD — Inventário e drift de VM por SSH · Roster da Metacortex

**Feature:** ferramenta que, da máquina de quem opera, entra numa VM por SSH, levanta o retrato
real do host e compara com o `baseline.yaml`, apontando cada desvio e sua gravidade.
**Data:** 2026-09-26
**Fonte:** brainstorm na sessão de 2026-09-26, revisado criticamente e em segurança na mesma
sessão
**Restringido por:** ADR 003 (coleta só por leitura, sem privilégio) e ADR 004 (chave de host
desconhecida aceita e registrada; fingerprint esperado opcional)
**Escopo do documento:** comportamento e regra de negócio. Escolhas de implementação
(linguagem, biblioteca SSH, comando usado para coletar cada dado, estrutura do código)
pertencem ao ADR/TRD.

---

## 1. Contexto

**Produto.** Primeiro pedaço da substituição do Roster manual: uma ferramenta de linha de
comando que audita **uma** VM do parque por vez contra o padrão declarado (`baseline.yaml`) e
devolve inventário e conformidade em JSON (para consumo automático) e Markdown (para leitura
no terminal).

**Estado atual.**
- O inventário é uma página mantida à mão desde que o parque tinha trinta hosts; envelheceu
  (papel de host mudado, agente instalado em incidente e não registrado, chave SSH esquecida).
- Não há agente instalado nas VMs, e ninguém vai instalar um só para isso. O que existe em toda
  VM é acesso por chave SSH.
- O padrão do parque existe e está versionado (`baseline.yaml`, `versao: 1`, 11 regras em
  três severidades).
- Não existe hoje nenhuma forma automática de dizer se uma VM está conforme.

**Problema de negócio.** À pergunta "quantas VMs estão fora do padrão?" (Segurança) e "quanto o
parque custa a mais por estar assim?" (Finanças) a resposta honesta é "não sei". Sem um retrato
verificável por host, não há como priorizar correção nem medir o custo do desvio.

---

## 2. Atores

| Ator | Papel nesta feature |
|---|---|
| **Operador** | Roda a ferramenta na própria máquina, informando endereço, usuário, chave privada e, se tiver, o fingerprint esperado do host; lê o Markdown |
| **Plantão** | Lê o Markdown no terminal, fora de hora, para decidir se age |
| **Pipeline** | Executa a ferramenta sem humano e decide pelo código de saída |
| **Roster (futuro)** | Consome o JSON automaticamente |
| **Host auditado** | VM Linux do parque; responde por SSH a um usuário comum, sem privilégio. O que ele devolve é dado não confiável |
| **`baseline.yaml`** | Define o esperado e a severidade de cada regra; é a única fonte do padrão |

---

## 3. Predicados verificáveis (Dado / Quando / Então)

### Execução e códigos de saída

**P1 — Host sem desvio sai sem desvio**
- **Dado** um host que não viola nenhuma das 11 regras do baseline
- **Quando** a ferramenta é executada contra ele
- **Então** nenhuma entrada da conformidade tem `veredito: desvio`, a seção "Desvios" do
  Markdown mostra "Nenhum.", e o código de saída é `0` se todas as entradas forem `conforme`
  ou `4` se alguma for `nao_verificado`. Com usuário comum, o esperado na prática é `4`: as
  regras de chaves (P25) e de login de root (P26) exigem leitura privilegiada

**P2 — Desvio classificado pela severidade do baseline**
- **Dado** um host que viola uma regra
- **Quando** a ferramenta é executada
- **Então** a entrada daquela regra traz `veredito: desvio` e `severidade` igual à que o
  `baseline.yaml` atribui à regra (`critico`, `alto` ou `medio`), com `esperado` e `encontrado`
  preenchidos, e o código de saída é `1`

**P3 — Uma entrada por regra, sempre**
- **Dado** o `baseline.yaml` versão 1
- **Quando** qualquer execução termina com relatório
- **Então** a conformidade tem exatamente uma entrada por regra do baseline (11), na ordem em
  que as regras aparecem em `esperado`; o `resumo` soma exatamente o total de entradas por
  veredito, e `por_severidade` conta só os desvios, com as três severidades sempre presentes
  (zero quando não houver)

**P4 — Regra não verificável é distinta de conforme**
- **Dado** uma regra cuja evidência exige privilégio que o usuário da coleta não tem, ou cuja
  leitura falhou
- **Quando** a ferramenta é executada
- **Então** a entrada traz `veredito: nao_verificado`, sem `severidade`, e um `motivo` que diz
  qual dos casos ocorreu ("exige privilégio que o usuário da coleta não tem", ou "falha de
  coleta: <o que falhou>"); `encontrado` é `null` quando nada foi lido e traz o que foi lido
  quando a evidência é parcial (P14, P25); a execução segue para as demais regras

**P5 — Código de saída com precedência**
- **Dado** o resultado de uma execução
- **Quando** a ferramenta termina
- **Então** o código é o primeiro que se aplica, nesta ordem: `2` erro de uso (parâmetro
  ausente, chave ilegível ou protegida por passphrase, baseline inválido) · `3` host
  inalcançável, conexão perdida durante a coleta, ou chave de host diferente da esperada · `1`
  ao menos um desvio · `4` nenhum desvio mas ao menos um `nao_verificado` · `0` tudo conforme.
  Um defeito da própria ferramenta (erro não previsto) termina com `5`, stderr com uma linha só
  com o tipo do erro, sem relatório — nenhum dos outros códigos serve sem afirmar algo falso
  sobre o uso ou sobre o host *(corrigido na implementação, 2026-09-26)*
  *(premissa confirmada em 2026-09-26: `4` separado de `0` porque um pipeline que lê `0` trataria
  regra não verificada como conforme, que o enunciado chama de mentira)*

**P6 — Os dois formatos saem do mesmo dado**
- **Dado** uma execução que produz relatório
- **Quando** o operador informa um arquivo para o JSON
- **Então** o Markdown sai no stdout e o JSON no arquivo indicado, **da mesma coleta**: o
  `coletado_em` é idêntico nos dois e cada veredito do Markdown corresponde ao do JSON. Sem
  arquivo informado, só o Markdown é produzido; o código de saída é o mesmo nos dois casos
  *(premissa confirmada em 2026-09-26: uma execução gera os dois, em vez de uma execução por
  formato, porque duas execuções dariam dois instantes de coleta diferentes; o JSON não vai
  para o stdout para não misturar os dois formatos no mesmo canal)*

**P7 — Host inalcançável falha com mensagem que diz o que houve**
- **Dado** um endereço que não responde, um nome que não resolve, um SSH fora do ar ou uma
  chave recusada
- **Quando** a ferramenta é executada
- **Então** ela termina com código `3` em até 15 s, escreve no stderr uma linha que nomeia a
  causa (sem stack trace), não escreve nada no stdout e não cria nem sobrescreve o arquivo JSON
  *(premissa confirmada em 2026-09-26: 15 s porque o plantão precisa saber rápido que o host não
  responde, e um SSH saudável conecta em poucos segundos; "nenhum JSON" porque um arquivo de
  erro no formato do relatório poderia ser lido pelo Roster como retrato)*

**P8 — Conexão perdida durante a coleta**
- **Dado** uma conexão que foi estabelecida e cai antes de a coleta terminar
- **Quando** a ferramenta detecta a queda
- **Então** ela termina com código `3`, stderr dizendo que a conexão caiu durante a coleta, nada
  no stdout e nenhum JSON — um retrato pela metade não distingue regra ilegível de regra não
  tentada

**P9 — Leitura lenta ou grande demais**
- **Dado** uma leitura no host que não termina em 20 s ou que devolve mais de 1 MiB
- **Quando** a ferramenta a executa
- **Então** a leitura é interrompida e as regras que dependem dela saem `nao_verificado` com
  motivo "falha de coleta: limite excedido (<qual>)"; a execução segue
  *(premissa confirmada em 2026-09-26: 20 s porque toda leitura do baseline é local ao host e
  responde em fração de segundo num host saudável; 1 MiB porque nenhum dado do inventário chega
  perto disso, e sem limite um host pode travar ou esgotar a memória de quem opera)*

**P10 — Erro de uso não tenta conectar**
- **Dado** parâmetro obrigatório ausente, arquivo de chave inexistente ou ilegível, chave
  protegida por passphrase, fingerprint esperado em formato inválido, ou `baseline.yaml`
  ilegível, com `versao` diferente de 1 ou com regra desconhecida
- **Quando** a ferramenta é executada
- **Então** ela termina com código `2` e mensagem que nomeia o problema e o parâmetro, sem abrir
  conexão

**P11 — Chave de host diferente da esperada**
- **Dado** que o operador informou o fingerprint esperado do host
- **Quando** o servidor apresenta chave de host com outro fingerprint
- **Então** a ferramenta não autentica, termina com código `3`, e o stderr mostra o fingerprint
  esperado e o apresentado; sem fingerprint informado, qualquer chave de host é aceita (ADR 004)

**P12 — Execução repetida devolve o mesmo veredito**
- **Dado** duas execuções seguidas contra o mesmo host, sem intervenção humana entre elas
- **Quando** as duas saídas são comparadas
- **Então** `conformidade` e `resumo` são idênticos, e o inventário é idêntico nos campos que as
  regras avaliam (SO, kernel, swap, portas, chaves, SSH, NTP, fingerprint e as unidades citadas
  no baseline); só `coletado_em` e unidades transitórias fora do baseline podem variar
  *(premissa confirmada em 2026-09-26: unidades disparadas por timer do sistema ativam sozinhas
  entre execuções; o enunciado exige o mesmo veredito, não o mesmo inventário completo)*

### Forma da saída

**P13 — Bloco `host`**
- **Dado** qualquer execução que conecta
- **Quando** o relatório é gerado
- **Então** `host` traz `endereco` (o usado na conexão), `hostname` (o que o próprio host
  reporta), `coletado_em` em UTC no formato `AAAA-MM-DDThh:mm:ssZ`, medido pelo relógio de quem
  opera, e `chave_de_host` com o algoritmo e o fingerprint SHA256 no formato que o OpenSSH
  mostra (ex.: `ssh-ed25519 SHA256:…`)
  *(premissa confirmada em 2026-09-26: relógio do operador porque o do host pode estar justamente
  dessincronizado, que é uma das regras)*

**P14 — Bloco `inventario`**
- **Dado** qualquer execução que produz relatório
- **Quando** o inventário é montado
- **Então** cada campo tem esta forma, e o valor é `null` quando não pôde ser lido:
  - `so`: `distribuicao` (identificador do host, ex.: `ubuntu`) e `versao` (com a revisão
    pontual quando o host a informa, ex.: `24.04.1`);
  - `kernel`: `versao` como o host reporta (ex.: `6.8.0-1015-gcp`);
  - `servicos`: todas as unidades do tipo serviço e socket em estado ativo, cada uma com `nome`
    completo, `tipo` (`service` ou `socket`) e `estado`, em ordem alfabética de nome;
  - `swap`: `habilitado` (booleano) e `tamanho` (total, arredondado para o inteiro na maior
    unidade K/M/G/T cujo valor arredondado dê ao menos 1, ex.: `4G`; `null` sem swap). Um
    arquivo de swap de 1 GiB aparece com 4 KiB a menos (cabeçalho) e sai `1G`, não `1024M`
    *(corrigido na validação, 2026-09-26)*;
  - `portas_em_escuta`: portas TCP em escuta, cada uma com `porta` (número), `bind` (endereço
    literal), `processo` (`null` quando o dono não é legível pelo usuário da coleta), `conta`
    (dono do socket) e `unidade` (unidade systemd dona do socket, `null` se não houver), em ordem
    de porta e depois de bind *(`conta` e `unidade` acrescentados na validação, 2026-09-26:
    com usuário comum `processo` sai `null` em toda porta de outro usuário, e os dois são
    legíveis sem privilégio)*;
  - `chaves_ssh`: as chaves lidas, cada uma com `identificacao` (o comentário da chave, `null`
    se não houver) e `conta` (dono do arquivo de onde veio), em ordem de conta e depois de
    identificação; e, ao lado, `chaves_ssh_fontes_nao_lidas`, lista das contas ou fontes de
    chave que não puderam ser lidas — vazia quando todas foram lidas;
  - `ssh`: `login_de_root` com o valor efetivo como o servidor o expressa (`no`,
    `prohibit-password`, `yes`, …) ou `null`;
  - `ntp`: `sincronizado` (booleano) e `mecanismo` (a unidade de sincronização ativa, ex.:
    `chrony`, `systemd-timesyncd`; `null` se nenhuma estiver ativa)
  *(premissa confirmada em 2026-09-26: `login_de_root` como texto em vez de booleano, para não
  perder `prohibit-password`; `chaves_ssh_fontes_nao_lidas` porque o enunciado pede "quantas
  existem", e uma lista parcial sem aviso vira contagem falsa)*

**P15 — Esqueleto do Markdown**
- **Dado** qualquer execução que produz relatório
- **Quando** o Markdown é emitido
- **Então** ele segue exatamente esta estrutura, com as três seções sempre presentes, nesta
  ordem, e "Nenhum." quando a seção não tem itens:

  ```
  # Inventário — <hostname> (<endereco>)
  Coletado em <AAAA-MM-DD hh:mm> UTC · baseline v<versao> · chave de host <algoritmo> <fingerprint>

  ## Desvios

  | Severidade | Regra | Esperado | Encontrado |
  |---|---|---|---|

  ## Não verificado

  | Regra | Motivo |
  |---|---|

  ## Conforme
  <regras separadas por " · ">
  ```

  As linhas de Desvios vêm em ordem de severidade (crítico, alto, médio) e, dentro dela, na
  ordem do baseline; as demais seções seguem a ordem do baseline. A severidade aparece com
  acento no Markdown (`crítico`, `médio`) e sem acento no JSON (`critico`, `medio`), como no
  enunciado

### Regras do baseline

**P16 — Versões comparadas numericamente**
- **Dado** `so.versao_minima: "22.04"` e `kernel.versao_minima: "6.5"`
- **Quando** o host reporta, por exemplo, SO `24.04.1` e kernel `6.11.0-1015-gcp`
- **Então** a comparação é componente a componente como número (`6.11` ≥ `6.5`), nunca como
  texto; o sufixo do kernel é ignorado na comparação e mantido em `encontrado`

**P17 — `so.distribuicao` e `so.versao_minima`**
- **Dado** `distribuicao: ubuntu`
- **Quando** o host se identifica com outra distribuição
- **Então** `so.distribuicao` é desvio `alto`; `so.versao_minima` sai `nao_verificado` com
  motivo "distribuição diferente da esperada" e `encontrado` com a versão lida
  *(premissa confirmada em 2026-09-26: comparar versão do Ubuntu com versão de outra distribuição
  não tem significado)*

**P18 — `servicos.ativos`**
- **Dado** a lista `[ssh, containerd, node_exporter, chrony]`, com nomes sem sufixo
- **Quando** o host é auditado
- **Então** cada nome é satisfeito por uma unidade `<nome>.service` **ou** `<nome>.socket` em
  estado `active` (qualquer outro estado — `activating`, `failed`, `inactive` — conta como não
  ativo); se faltar alguma, desvio `alto` com `encontrado` listando as ausentes; nome
  diferente não satisfaz (`prometheus-node-exporter.service` não satisfaz `node_exporter`)
  *(premissa confirmada em 2026-09-26: `.socket` satisfaz porque o SSH pode estar ativado por
  socket; sem alias porque o baseline é a única fonte do padrão)*

**P19 — `servicos.proibidos`**
- **Dado** a lista `[telnet.socket, rpcbind.socket]`, com nomes exatos
- **Quando** o host é auditado
- **Então** desvio `alto` se alguma dessas unidades estiver `active`; unidade inexistente,
  inativa ou mascarada é conforme
  *(premissa confirmada em 2026-09-26: o inventário do enunciado é de unidades ativas; unidade
  instalada e parada não escuta)*

**P20 — `swap.habilitado`**
- **Dado** `swap.habilitado: false`
- **Quando** o host tem swap ativo
- **Então** desvio `critico`; no JSON `encontrado: true`, no Markdown `true (4G)`, com o
  tamanho total

**P21 — Classificação do endereço de bind**
- **Dado** uma porta TCP em escuta
- **Quando** o endereço de bind é classificado
- **Então** é **interno** se for loopback (`127.0.0.0/8`, `::1`), privado (`10/8`,
  `172.16/12`, `192.168/16`), ULA (`fc00::/7`) ou link-local (`169.254/16`, `fe80::/10`); é
  **público** em qualquer outro caso, inclusive todos os endereços (`0.0.0.0`, `::`, `*`).
  Endereço privado conta como interno mesmo quando a nuvem traduz um IP externo para ele — a
  regra olha o bind, não a tradução nem o firewall (Restrições)
  *(premissa confirmada em 2026-09-26: "rede interna" não é definida no baseline)*

**P22 — `portas_em_escuta.publicas_permitidas`**
- **Dado** `publicas_permitidas: [22]`
- **Quando** alguma porta TCP está em bind público
- **Então** conforme se todas as portas em bind público estiverem na lista; desvio `critico`
  listando as que não estão. A porta 22 em bind só interno é conforme ("permitida" não é
  "exigida"). Porta listada em `somente_rede_interna` não entra nesta regra: é julgada só por
  P23, para que o mesmo bind não vire dois desvios — como no exemplo do enunciado, em que a
  9100 em `0.0.0.0` conta um desvio crítico só *(corrigido na implementação, 2026-09-26)*

**P23 — `portas_em_escuta.somente_rede_interna`**
- **Dado** `somente_rede_interna: [9100]`
- **Quando** a porta 9100 está em escuta
- **Então** conforme se todos os binds dela forem internos; desvio `critico` se algum for
  público (ex.: `9100 em 0.0.0.0`). Porta listada sem ninguém escutando é conforme — a ausência
  do serviço é apanhada por `servicos.ativos`

**P24 — Processo dono da porta**
- **Dado** uma porta em escuta aberta por processo de outro usuário
- **Quando** o inventário é montado
- **Então** a porta aparece com número, bind, `conta` e `unidade`, e `processo: null`; o
  veredito das regras de porta depende só do bind

**P25 — `chaves_ssh.emitidas_por`**
- **Dado** `emitidas_por: metacortex-platform`, e que a identificação de uma chave é o
  comentário dela
- **Quando** o host é auditado
- **Então**:
  - uma chave é **emitida pela plataforma** se o comentário terminar em `@metacortex-platform`;
    chave sem comentário não é;
  - todas as contas do host são fontes de chave, inclusive as de shell `nologin`, `false` ou
    vazio: o shell não impede autenticar nem abrir túnel *(corrigido após revisão, 2026-09-26)*;
  - a linha de chave é interpretada como o servidor SSH a interpretaria: opções antes do tipo
    (`from=`, `command=`, `cert-authority`) não mudam a identificação; o comentário é todo o
    texto depois da chave, espaços incluídos; linhas em branco, comentários (`#`) e linhas que
    o servidor não reconheceria como chave são ignoradas;
  - **desvio** `critico` se qualquer chave lida não for emitida pela plataforma, com
    `encontrado` listando essas identificações;
  - **nao_verificado** se nenhuma chave lida estiver fora do padrão mas
    `chaves_ssh_fontes_nao_lidas` não estiver vazia, com o motivo nomeando as fontes;
  - **conforme** só se todas as fontes de chave do host foram lidas e todas as chaves são
    emitidas pela plataforma
  *(premissa confirmada em 2026-09-26: com usuário comum, o resultado esperado na prática é
  `nao_verificado`, porque as contas de outros usuários e a configuração efetiva de fontes de
  chave não são legíveis)*

**P26 — `ssh.login_de_root`**
- **Dado** `login_de_root: false`
- **Quando** o host é auditado
- **Então** o que vale é a configuração **efetiva** do servidor SSH, não o texto do arquivo:
  conforme só se o login de root estiver efetivamente proibido (`no`); qualquer outro valor —
  inclusive `prohibit-password`, que permite root por chave — é desvio `alto`; se a
  configuração efetiva não puder ser lida pelo usuário da coleta, `nao_verificado`, sem
  deduzir o valor a partir do arquivo
  *(premissa confirmada em 2026-09-26: `prohibit-password` como desvio, porque o baseline pede
  login de root desligado e esse valor ainda o permite)*

**P27 — `ntp.sincronizado`**
- **Dado** `ntp.sincronizado: true`
- **Quando** o host é auditado
- **Então** desvio `medio` se o relógio não estiver sincronizado

### Dado não confiável

**P28 — Texto hostil vindo do host não altera o relatório**
- **Dado** um host com uma chave cujo comentário contém sequência de controle de terminal
  (ex.: `\x1b[2K`), quebra de linha e texto imitando uma linha de tabela
  (`| x | conforme |`)
- **Quando** o relatório é gerado
- **Então** o Markdown mostra o texto de forma literal e visível (caracteres de controle
  escapados, `|` e quebra de linha neutralizados), as tabelas mantêm o número de linhas
  correto, e o JSON representa o texto sem caracteres de controle crus

---

## 4. Invariantes

- **I1 — Só lê.** A ferramenta não instala, escreve, corrige nem reinicia nada no host
  auditado, e não usa elevação de privilégio. Registros que o próprio servidor gera ao aceitar
  um login (log de autenticação, registro de sessão) são efeito do acesso, não escrita da
  ferramenta.
- **I2 — A chave privada é credencial.**
  (a) O conteúdo da chave privada, e qualquer material derivado da parte privada, não aparece em
  nenhum canal (stdout, stderr, JSON, log), em nenhum nível de detalhe.
  (b) O caminho da chave não aparece no relatório nem no stderr; mensagens citam o parâmetro,
  não o valor dele. O caminho não é segredo, mas revela a organização da máquina de quem opera,
  e a regra "o valor nunca sai" é mais simples de testar do que "sai, exceto…".
  (c) Nenhum stack trace, nem log de biblioteca de terceiros, chega ao stderr, inclusive de
  execução em segundo plano.
  (d) A chave entra só como caminho de arquivo, nunca como conteúdo em parâmetro ou variável de
  ambiente.
- **I3 — Nenhuma regra é omitida.** Todo relatório tem uma entrada por regra do baseline;
  uma regra que não pôde ser avaliada aparece como `nao_verificado`, nunca some nem vira
  `conforme`.
- **I4 — `conforme` é afirmação provada.** Uma regra só sai `conforme` quando toda a evidência
  que ela exige foi lida; evidência parcial sem desvio é `nao_verificado`.
- **I5 — Determinismo.** Para o mesmo estado do host, a saída é a mesma, exceto `coletado_em`:
  listas em ordem estável, sem dependência de idioma ou fuso do host.
- **I6 — Só usa a chave informada.** A ferramenta autentica exclusivamente com a chave
  recebida; não recorre a outras chaves nem a agente de chaves da máquina de quem opera.
- **I7 — Dado do host é não confiável.** Todo texto vindo do host é tratado como dado: é
  neutralizado antes de ir para o terminal e para o Markdown, é limitado em tamanho, e nunca é
  usado para compor comando executado no host.

---

## 5. Restrições (de negócio / comportamento)

- Nada é instalado nas VMs: o único acesso é SSH por chave (enunciado).
- A coleta entra com usuário comum, sem privilégio; parte do baseline não será verificável
  com ele, e isso é resultado esperado, não falha (enunciado).
- A forma do JSON segue o exemplo do enunciado; campos adicionais (`chave_de_host`, `motivo`,
  `conta`, `chaves_ssh_fontes_nao_lidas`) acrescentam, não renomeiam.
- No JSON, `encontrado` leva o tipo do dado — booleano, texto, lista de nomes ou lista de
  `{porta, bind}` —, para que o Roster compare com `esperado` sem interpretar frase; a frase
  para o leitor (`true (4G)`, `ausente: chrony`) existe só no Markdown, como no exemplo do
  enunciado *(corrigido após revisão, 2026-09-26: antes o JSON levava a frase)*.
- O exemplo do enunciado tem `resumo` que soma 9 para 11 regras; este PRD segue a regra do
  enunciado (uma entrada por regra) e não o exemplo.
- A regra de portas avalia o **bind no host**. Firewall e tradução de endereço da rede ou da
  nuvem não são considerados: uma porta em bind público atrás de firewall fechado continua
  sendo desvio, e uma porta em endereço privado continua interna mesmo que a nuvem a exponha.

---

## 6. Fora do escopo (com justificativa)

- **Vários hosts por execução** — o enunciado recebe "o endereço da VM"; varrer o parque é
  papel do Roster, que chamará a ferramenta por host.
- **Chave com passphrase e agente de chaves** — o enunciado recebe a chave privada; suportar
  passphrase exige decidir como ela entra sem vazar (I2), o que é decisão à parte. Hoje é erro
  de uso (P10).
- **Elevação de privilégio (`sudo`)** — daria vereditos diferentes conforme quem roda e
  poria a ferramenta em condição de escrever no host, contra I1.
- **Correção de desvio** — a ferramenta aponta; corrigir contraria I1 e é decisão humana.
- **Portas UDP** — limite declarado, não ausência de risco: um socket UDP ligado em todos os
  endereços também está exposto (o `rpcbind` do laboratório abre a 111 em UDP além de TCP), e
  um serviço só UDP em bind público sai `conforme` em `publicas_permitidas`. Fica fora porque o
  baseline não distingue protocolo nem cita porta UDP, e incluí-lo mudaria o significado das
  regras de porta sem decisão de quem mantém o baseline *(justificativa corrigida após
  revisão, 2026-09-26)*.
- **Firewall e tradução de endereço da nuvem** — ver Restrições; incluir exigiria acesso à API
  de cada provedor.
- **Aliases de nome de serviço** — o baseline é a única fonte do padrão; aliases criariam um
  segundo lugar definindo o que é conforme.
- **Prova criptográfica de emissão da chave** — a identificação pelo comentário é forjável;
  provar emissão exige certificado SSH assinado pela plataforma, que o parque não usa hoje.
- **Integridade do host** — um host comprometido pode mentir em todas as leituras; a
  ferramenta mede desvio de configuração de um host que responde honestamente, não detecta
  comprometimento.
- **`known_hosts` completo** — o parque não tem fonte de chaves de host; o fingerprint esperado
  opcional (P11) cobre o caso de quem tem a chave em mãos (ADR 004).
- **Ambiente de laboratório** (VM de teste, usuário de coleta, estados conforme/com desvio) —
  é infraestrutura de validação, não comportamento da ferramenta (ADR 005).
- **Custo do desvio** — a pergunta de Finanças depende do retrato que esta feature produz, mas
  calcular custo é outra feature.

---

## 7. Critérios de aceite (observáveis)

Verificados em 2026-09-26 contra VM Ubuntu 24.04.5 real; arquivos em `../../evidencia/`.

- [x] Execução contra host sem desvio: nenhum `desvio`, código `0` ou `4` conforme P1, 11
      entradas (P1, P3). — `01-conforme`, código `4`. O código `0` só é provado em teste: com
      usuário comum, chaves e login de root não se leem.
- [x] Execução contra host com desvios: cada desvio com a severidade do baseline, código `1`
      (P2). — `03-desvios`, 7 desvios.
- [x] Regra não verificável aparece como `nao_verificado`, com motivo, e não como conforme
      (P4, I3, I4). — `01` e `03`.
- [x] Host inalcançável em três variantes (endereço errado, chave recusada, SSH fora do ar):
      código `3`, mensagem que nomeia a causa, sem stack trace, sem relatório (P7). — `04`,
      `05`, `06`, `08`, todos em até 6,6 s.
- [x] Fingerprint esperado errado: código `3`, sem relatório (P11). — `07`.
- [x] Duas execuções seguidas contra o mesmo host: `conformidade` e `resumo` idênticos, e o
      inventário igual nos campos avaliados (P12). — `01` × `02`: inventário inteiro idêntico.
- [x] Busca, em stdout, stderr e JSON de todas as execuções acima (inclusive as de erro), por
      cada linha do conteúdo da chave privada e pelo caminho dela: zero ocorrências (I2). —
      `09-busca-da-chave.txt`.
- [x] JSON e Markdown da mesma execução com o mesmo `coletado_em` e os mesmos vereditos (P6),
      Markdown no esqueleto de P15.
- [x] Comentário de chave hostil não altera a estrutura do Markdown (P28). — `03-desvios.md`.
- [x] Evidência de que o host não foi alterado pela ferramenta (I1). — `00-controle-*` ×
      `02-arquivos-alterados.txt` e `02-servicos-iniciados.txt`.

## 8. Métricas de sucesso

Não aplicável — esta feature não tem meta de negócio medida. A métrica de negócio (quantas VMs
estão fora do padrão) só existe quando o Roster rodar a ferramenta sobre o parque.
