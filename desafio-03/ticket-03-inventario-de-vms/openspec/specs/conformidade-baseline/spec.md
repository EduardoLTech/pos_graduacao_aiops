# conformidade-baseline Specification

## Purpose
Como cada uma das 11 regras do baseline.yaml versão 1 é avaliada, os três vereditos e o resumo (PRD-0001 P1–P4, P16–P27, I3, I4).

## Requirements
### Requirement: Uma entrada por regra, com resumo coerente
A conformidade MUST ter exatamente uma entrada por regra do `baseline.yaml` versão 1 (11), na
ordem em que as regras aparecem em `esperado`, cada uma com `regra`, `esperado`, `encontrado` e
`veredito`. O `resumo` MUST somar o total de entradas por veredito, e `por_severidade` MUST
contar só os desvios, com `critico`, `alto` e `medio` sempre presentes (PRD P3, I3).

#### Scenario: Contagem do resumo
- **WHEN** a conformidade tem 6 `conforme`, 3 `desvio` e 2 `nao_verificado`
- **THEN** `resumo` soma 11, e `por_severidade` soma 3

#### Scenario: Severidade sem desvio
- **WHEN** nenhum desvio é `medio`
- **THEN** `por_severidade.medio` é `0`, e não ausente

### Requirement: Desvio carrega a severidade do baseline
Uma regra violada MUST sair com `veredito: desvio`, `severidade` igual à que o baseline atribui
à regra e `esperado` e `encontrado` preenchidos (PRD P2).

#### Scenario: Swap ligado
- **WHEN** o host tem swap ativo
- **THEN** `swap.habilitado` sai `desvio` com severidade `critico`

### Requirement: Não verificado é distinto de conforme
Uma regra cuja evidência exige privilégio que o usuário não tem, ou cuja leitura falhou, MUST
sair `nao_verificado`, sem `severidade`, com `motivo` "exige privilégio que o usuário da coleta
não tem" ou "falha de coleta: <o que falhou>". `encontrado` MUST ser `null` quando nada foi lido
e trazer o que foi lido quando a evidência é parcial. Uma regra só sai `conforme` quando toda a
evidência que ela exige foi lida (PRD P4, I4).

#### Scenario: Leitura sem permissão
- **WHEN** a configuração efetiva do SSH não é legível pelo usuário da coleta
- **THEN** `ssh.login_de_root` sai `nao_verificado` com o motivo de privilégio e `encontrado:
  null`

#### Scenario: Leitura que falhou
- **WHEN** o comando de uma leitura não existe no host
- **THEN** as regras que dependem dela saem `nao_verificado` com motivo "falha de coleta" e as
  demais regras são avaliadas

### Requirement: Versões comparadas numericamente
As regras `so.versao_minima` e `kernel.versao_minima` MUST comparar componente a componente como
número, nunca como texto; o sufixo do kernel é ignorado na comparação e mantido em `encontrado`
(PRD P16).

#### Scenario: Kernel 6.11 contra mínimo 6.5
- **WHEN** o kernel é `6.11.0-1015-gcp`
- **THEN** `kernel.versao_minima` sai `conforme` e `encontrado` é `6.11.0-1015-gcp`

#### Scenario: Kernel abaixo do mínimo
- **WHEN** o kernel é `5.15.0-118-generic`
- **THEN** `kernel.versao_minima` sai `desvio` com severidade `medio`

### Requirement: Distribuição e versão do SO
`so.distribuicao` MUST sair `desvio` quando a distribuição do host for diferente de `ubuntu`;
nesse caso `so.versao_minima` MUST sair `nao_verificado` com motivo "distribuição diferente da
esperada" e `encontrado` com a versão lida (PRD P17).

#### Scenario: Host Debian
- **WHEN** o host se identifica como `debian` versão `12`
- **THEN** `so.distribuicao` sai `desvio` `alto` e `so.versao_minima` sai `nao_verificado` com
  `encontrado: "12"`

### Requirement: Serviços ativos
Cada nome de `servicos.ativos` MUST ser satisfeito por uma unidade `<nome>.service` ou
`<nome>.socket` em estado `active`; qualquer outro estado conta como não ativo, e nome diferente
não satisfaz. Se faltar algum, a regra sai `desvio` com `encontrado` listando os ausentes (PRD
P18).

#### Scenario: SSH ativado por socket
- **WHEN** só `ssh.socket` está ativo
- **THEN** o nome `ssh` está satisfeito

#### Scenario: Nome de pacote diferente
- **WHEN** `prometheus-node-exporter.service` está ativo e `node_exporter.service` não existe
- **THEN** `servicos.ativos` sai `desvio` listando `node_exporter`

### Requirement: Serviços proibidos
`servicos.proibidos` MUST sair `desvio` se alguma unidade listada estiver `active`; unidade
inexistente, inativa ou mascarada é conforme (PRD P19).

#### Scenario: rpcbind ativo
- **WHEN** `rpcbind.socket` está ativo
- **THEN** `servicos.proibidos` sai `desvio` `alto` com `rpcbind.socket` em `encontrado`

### Requirement: Swap desligado
`swap.habilitado` MUST sair `desvio` quando houver swap ativo, com o tamanho total em
`encontrado` (ex.: `true (4G)`) (PRD P20).

#### Scenario: Sem swap
- **WHEN** o host não tem swap ativo
- **THEN** `swap.habilitado` sai `conforme`

### Requirement: Classificação do bind
Um endereço de bind MUST ser classificado como interno se for loopback (`127.0.0.0/8`, `::1`),
privado (`10/8`, `172.16/12`, `192.168/16`), ULA (`fc00::/7`) ou link-local (`169.254/16`,
`fe80::/10`), e como público em qualquer outro caso, inclusive todos os endereços (`0.0.0.0`,
`::`, `*`). Firewall e tradução de endereço não são considerados (PRD P21).

#### Scenario: Bind em todos os endereços
- **WHEN** uma porta escuta em `0.0.0.0`
- **THEN** o bind é público

#### Scenario: Bind no endereço interno da nuvem
- **WHEN** uma porta escuta em `10.128.0.5`
- **THEN** o bind é interno, mesmo que a nuvem traduza um IP externo para ele

### Requirement: Portas públicas permitidas
`portas_em_escuta.publicas_permitidas` MUST sair `desvio` listando as portas em bind público que
não estão na lista, e `conforme` se todas estiverem; a porta 22 só em bind interno é conforme.
Porta listada em `somente_rede_interna` MUST NOT entrar nesta regra: é julgada só por aquela
(PRD P22).

#### Scenario: 9100 pública conta um desvio só
- **WHEN** a porta 9100 escuta em `0.0.0.0` e a 22 também
- **THEN** `portas_em_escuta.publicas_permitidas` sai `conforme` e só
  `portas_em_escuta.somente_rede_interna` sai `desvio`

#### Scenario: Porta 8080 pública
- **WHEN** a porta 8080 escuta em `0.0.0.0`
- **THEN** `portas_em_escuta.publicas_permitidas` sai `desvio` `critico` citando 8080

### Requirement: Portas somente na rede interna
`portas_em_escuta.somente_rede_interna` MUST sair `desvio` se algum bind de uma porta listada
for público, e `conforme` se todos forem internos ou se ninguém escutar nela (PRD P23).

#### Scenario: 9100 aberta para o mundo
- **WHEN** a porta 9100 escuta em `0.0.0.0`
- **THEN** a regra sai `desvio` `critico` com `encontrado` "9100 em 0.0.0.0"

#### Scenario: 9100 sem ninguém escutando
- **WHEN** nada escuta na porta 9100
- **THEN** a regra sai `conforme`

### Requirement: Chaves emitidas pela plataforma
Uma chave MUST ser considerada emitida pela plataforma só se o comentário terminar em
`@metacortex-platform`. Todas as contas do host MUST ser fontes de chave, inclusive as de
shell `nologin`, `false` ou vazio. A linha MUST ser interpretada como o servidor SSH a interpretaria:
opções antes do tipo não mudam a identificação, o comentário é todo o texto depois da chave, e
linhas em branco, comentários e linhas não reconhecidas como chave são ignoradas. A regra sai
`desvio` se qualquer chave lida não for da plataforma; `nao_verificado` se nenhuma lida estiver
fora do padrão mas houver fonte não lida; `conforme` só se todas as fontes foram lidas e todas as
chaves são da plataforma (PRD P25).

#### Scenario: Chave pessoal esquecida
- **WHEN** a conta da coleta tem uma chave com comentário `neo@laptop`
- **THEN** a regra sai `desvio` `critico` com `neo@laptop` em `encontrado`, mesmo havendo fontes
  não lidas

#### Scenario: Chave com opções
- **WHEN** a linha é `from="10.0.0.0/8" ssh-ed25519 AAAA… ops@metacortex-platform`
- **THEN** a identificação é `ops@metacortex-platform`

#### Scenario: Conta de serviço com shell nologin
- **WHEN** uma conta com shell `/usr/sbin/nologin` tem, legível, uma chave `legado@fornecedor`
- **THEN** a regra sai `desvio` citando `legado@fornecedor`

#### Scenario: Fontes não lidas sem desvio
- **WHEN** todas as chaves lidas são da plataforma e há contas não lidas
- **THEN** a regra sai `nao_verificado` com o motivo nomeando as fontes

### Requirement: Login de root efetivo
`ssh.login_de_root` MUST sair `conforme` só se o valor efetivo for `no`; qualquer outro valor,
inclusive `prohibit-password`, sai `desvio`; se o valor efetivo não for legível, a regra sai
`nao_verificado`, sem deduzir do arquivo (PRD P26).

#### Scenario: prohibit-password
- **WHEN** o valor efetivo é `prohibit-password`
- **THEN** a regra sai `desvio` `alto`

### Requirement: Relógio sincronizado
`ntp.sincronizado` MUST sair `desvio` quando o relógio do host não estiver sincronizado (PRD
P27).

#### Scenario: Relógio não sincronizado
- **WHEN** o host informa que o relógio não está sincronizado
- **THEN** a regra sai `desvio` `medio`

### Requirement: Host sem desvio
Um host que não viola nenhuma regra MUST sair sem nenhuma entrada `desvio`, com código `0` se
todas forem `conforme` ou `4` se alguma for `nao_verificado` (PRD P1).

#### Scenario: Host conforme com usuário comum
- **WHEN** a ferramenta audita, com usuário comum, um host que cumpre todo o baseline
- **THEN** nenhuma entrada é `desvio`, a seção Desvios do Markdown mostra "Nenhum." e o código é
  `4`, porque chaves e login de root exigem leitura privilegiada

