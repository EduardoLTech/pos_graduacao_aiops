# inventario-do-host Specification

## Purpose
O que a ferramenta lê do host, só por leitura e sem privilégio, e a forma de cada campo do inventário, estável entre execuções (PRD-0001 P12–P14, P24, I1, I5).

## Requirements
### Requirement: Coleta só por leitura
A ferramenta MUST executar no host apenas leituras que o sistema base já oferece, com o usuário
da conexão, sem copiar arquivo, sem escrever, sem instalar, sem reiniciar nada e sem tentar
elevação de privilégio. As leituras MUST NOT ativar serviço sob demanda no host (por exemplo,
via D-Bus). Os comandos executados no host MUST ser fixos e MUST NOT incorporar texto vindo do
próprio host (PRD I1, I7, ADR 003).

#### Scenario: Nenhum serviço sobe por causa da leitura
- **WHEN** a ferramenta é executada contra um host
- **THEN** o journal do host não registra início de serviço no intervalo da execução, e nenhum
  arquivo fora dos registros de login muda

#### Scenario: Host não é alterado
- **WHEN** a ferramenta é executada contra um host
- **THEN** nenhum arquivo, unidade ou pacote do host muda por ação dela; só os registros que o
  servidor gera ao aceitar um login aparecem

#### Scenario: Usuário com sudo
- **WHEN** o usuário da conexão tem sudo sem senha
- **THEN** a ferramenta não usa sudo, e o veredito é o mesmo que teria com um usuário sem sudo

### Requirement: Leituras com idioma e formato fixos
As leituras MUST rodar com configuração regional fixa (`LC_ALL=C`), de modo que a saída não
dependa do idioma ou do fuso do host (PRD I5, ADR 003).

#### Scenario: Host com idioma diferente
- **WHEN** o host tem configuração regional em português
- **THEN** o inventário e os vereditos são os mesmos que num host em inglês com o mesmo estado

### Requirement: Bloco host
O relatório MUST trazer `host` com `endereco` (o usado na conexão), `hostname` (o que o host
reporta), `coletado_em` em UTC no formato `AAAA-MM-DDThh:mm:ssZ` medido pelo relógio de quem
opera, e `chave_de_host` com algoritmo e fingerprint SHA256 no formato do OpenSSH (PRD P13).

#### Scenario: Host com relógio errado
- **WHEN** o relógio do host está uma hora adiantado
- **THEN** `coletado_em` reflete o relógio de quem opera, não o do host

#### Scenario: Formato do fingerprint
- **WHEN** o host apresenta chave de host Ed25519
- **THEN** `chave_de_host` é da forma `ssh-ed25519 SHA256:<base64 sem padding>`

### Requirement: Campos do inventário
O inventário MUST trazer cada campo na forma abaixo, com `null` quando o valor não pôde ser
lido (PRD P14):
- `so`: `distribuicao` (identificador, ex.: `ubuntu`) e `versao` (com revisão pontual quando o
  host a informa, ex.: `24.04.1`);
- `kernel`: `versao` como o host reporta;
- `servicos`: unidades do tipo service e socket em estado ativo, com `nome` completo, `tipo`
  (`service` ou `socket`) e `estado`, em ordem alfabética de nome;
- `swap`: `habilitado` (booleano) e `tamanho` (total arredondado para inteiro na maior unidade
  K/M/G/T que dê ao menos 1; `null` sem swap);
- `portas_em_escuta`: portas TCP em escuta com `porta` (número), `bind` (endereço literal),
  `processo`, `conta` (dono do socket) e `unidade` (unidade systemd dona do socket), em ordem de
  porta e depois de bind;
- `chaves_ssh`: chaves lidas com `identificacao` (comentário ou `null`) e `conta` (dono da
  fonte), em ordem de conta e depois de identificação; e `chaves_ssh_fontes_nao_lidas`, lista
  das contas ou fontes que não puderam ser lidas, vazia quando todas foram lidas;
- `ssh`: `login_de_root` com o valor efetivo como o servidor o expressa ou `null`;
- `ntp`: `sincronizado` (booleano) e `mecanismo` (unidade de sincronização ativa ou `null`).

#### Scenario: Swap de 4 GiB
- **WHEN** o host tem 4 GiB de swap ativos
- **THEN** `swap` é `{"habilitado": true, "tamanho": "4G"}`

#### Scenario: Serviço ativado por socket
- **WHEN** `ssh.socket` está ativo e `ssh.service` não
- **THEN** `servicos` traz `ssh.socket` com `tipo: socket`

#### Scenario: Configuração efetiva do SSH ilegível
- **WHEN** o usuário da coleta não consegue ler a configuração efetiva do servidor SSH
- **THEN** `ssh.login_de_root` é `null`, sem valor deduzido do arquivo de configuração

#### Scenario: Contas com chaves ilegíveis
- **WHEN** o usuário da coleta lê as próprias chaves autorizadas mas não as de outras contas
- **THEN** `chaves_ssh` traz as chaves lidas e `chaves_ssh_fontes_nao_lidas` nomeia as contas
  não lidas

### Requirement: Processo dono da porta
Uma porta aberta por processo de outro usuário MUST aparecer com número, bind, `conta` e
`unidade`, e com `processo: null` (PRD P24).

#### Scenario: Porta de processo de root
- **WHEN** a porta 22 é aberta pelo servidor SSH, ativado por `ssh.socket`, que roda como root
- **THEN** a porta aparece com `porta: 22`, o bind lido, `processo: null`, `conta: root` e
  `unidade: ssh.socket`

### Requirement: Mesmo estado, mesma saída
Duas execuções contra o mesmo host sem intervenção humana entre elas MUST produzir
`conformidade` e `resumo` idênticos e inventário idêntico nos campos que as regras avaliam; só
`coletado_em` e unidades transitórias fora do baseline podem variar. Toda lista MUST sair em
ordem estável (PRD P12, I5).

#### Scenario: Duas execuções seguidas
- **WHEN** a ferramenta é executada duas vezes seguidas contra o mesmo host
- **THEN** a comparação das duas saídas, ignorando `coletado_em` e unidades fora do baseline, não
  mostra diferença

