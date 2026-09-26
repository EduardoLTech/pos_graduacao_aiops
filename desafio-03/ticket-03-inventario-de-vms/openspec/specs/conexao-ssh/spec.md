# conexao-ssh Specification

## Purpose
Como a ferramenta recebe parâmetros, conecta ao host por SSH com a chave informada, verifica a chave de host, classifica falhas e protege a credencial; e os códigos de saída para pipeline (PRD-0001 P5, P7–P11, I2, I6).

## Requirements
### Requirement: Parâmetros de entrada
A ferramenta MUST receber endereço do host, usuário e caminho do arquivo da chave privada como
parâmetros obrigatórios, e aceitar como opcionais o fingerprint esperado da chave de host, o
caminho do arquivo JSON de saída e o caminho do `baseline.yaml`. A chave MUST entrar só como
caminho de arquivo, nunca como conteúdo em parâmetro ou variável de ambiente (PRD I2d).

#### Scenario: Execução com os parâmetros obrigatórios
- **WHEN** o operador informa endereço, usuário e caminho de uma chave válida
- **THEN** a ferramenta conecta ao host e produz o relatório em Markdown no stdout

#### Scenario: Chave passada como conteúdo não é aceita
- **WHEN** o operador tenta informar o conteúdo da chave em vez do caminho
- **THEN** não existe parâmetro nem variável de ambiente que aceite esse conteúdo

### Requirement: Erro de uso encerra antes de conectar
A ferramenta MUST terminar com código `2`, mensagem no stderr que nomeia o problema e o
parâmetro, e sem abrir conexão quando: faltar parâmetro obrigatório; o arquivo de chave não
existir, for ilegível ou estiver protegido por passphrase; o fingerprint esperado estiver em
formato inválido; ou o `baseline.yaml` for ilegível, tiver `versao` diferente de 1 ou regra
desconhecida (PRD P10).

#### Scenario: Chave com passphrase
- **WHEN** o arquivo de chave informado está protegido por passphrase
- **THEN** a ferramenta termina com código `2`, a mensagem cita o parâmetro da chave e nenhuma
  conexão é aberta

#### Scenario: Baseline de versão desconhecida
- **WHEN** o `baseline.yaml` informado tem `versao: 2`
- **THEN** a ferramenta termina com código `2` sem conectar

#### Scenario: Parâmetro obrigatório ausente
- **WHEN** o usuário não é informado
- **THEN** a ferramenta termina com código `2` e a mensagem nomeia o parâmetro ausente

### Requirement: Autenticação só com a chave informada
A ferramenta MUST autenticar exclusivamente com a chave recebida, sem recorrer a agente de
chaves nem a chaves padrão da máquina de quem opera (PRD I6).

#### Scenario: Agente de chaves disponível
- **WHEN** a máquina de quem opera tem um agente de chaves com outra chave aceita pelo host e a
  chave informada é recusada
- **THEN** a ferramenta termina com código `3` por chave recusada, sem autenticar com a chave
  do agente

### Requirement: Chave de host aceita e registrada, salvo fingerprint esperado
Sem fingerprint esperado, a ferramenta MUST aceitar qualquer chave de host e registrar seu
algoritmo e fingerprint SHA256 no relatório, sem gravar no `known_hosts` de quem opera. Com
fingerprint esperado, a ferramenta MUST comparar antes de autenticar e, se divergir, terminar
com código `3`, stderr mostrando o fingerprint esperado e o apresentado, e sem relatório (PRD
P11, ADR 004).

#### Scenario: Fingerprint esperado diverge
- **WHEN** o operador informa um fingerprint esperado diferente do apresentado pelo host
- **THEN** a ferramenta não autentica, termina com código `3`, mostra os dois fingerprints no
  stderr e não escreve nada no stdout nem no arquivo JSON

#### Scenario: Fingerprint esperado confere
- **WHEN** o operador informa o fingerprint que o host apresenta
- **THEN** a ferramenta autentica e segue a execução normalmente

#### Scenario: Sem fingerprint esperado
- **WHEN** nenhum fingerprint esperado é informado
- **THEN** a execução segue e o relatório traz algoritmo e fingerprint da chave de host

### Requirement: Host inalcançável falha com causa nomeada
A ferramenta MUST terminar com código `3` em até 15 s quando o nome não resolver, o endereço
não responder, o SSH recusar a conexão ou a chave for recusada, escrevendo no stderr uma linha
que nomeia a causa, sem stack trace, sem nada no stdout e sem criar nem sobrescrever o arquivo
JSON. A causa MUST ser determinada pelo tipo do erro, não pelo texto da mensagem (PRD P7, ADR
002).

#### Scenario: Endereço que não responde
- **WHEN** o endereço informado não responde
- **THEN** a ferramenta termina com código `3` em até 15 s e o stderr diz que o host não
  respondeu

#### Scenario: Chave recusada
- **WHEN** o host recusa a chave informada
- **THEN** a ferramenta termina com código `3` e o stderr diz que a autenticação foi recusada

#### Scenario: SSH fora do ar
- **WHEN** o host responde mas nada escuta na porta SSH
- **THEN** a ferramenta termina com código `3` e o stderr diz que a conexão foi recusada

#### Scenario: JSON anterior preservado
- **WHEN** o arquivo JSON indicado já existe e o host está inalcançável
- **THEN** o arquivo permanece com o conteúdo anterior

### Requirement: Conexão perdida durante a coleta
A ferramenta MUST terminar com código `3`, stderr dizendo que a conexão caiu durante a coleta,
nada no stdout e nenhum JSON quando a conexão cair depois de estabelecida e antes do fim da
coleta (PRD P8).

#### Scenario: Queda no meio da coleta
- **WHEN** a conexão cai depois da autenticação e antes da última leitura
- **THEN** a ferramenta termina com código `3` sem produzir relatório parcial

### Requirement: Limite de tempo e tamanho por leitura
Cada leitura no host MUST ser interrompida ao passar de 20 s ou de 1 MiB de saída; as regras
que dependem dela saem `nao_verificado` com motivo "falha de coleta: limite excedido (<qual>)",
e a execução segue (PRD P9).

#### Scenario: Leitura que devolve saída grande demais
- **WHEN** uma leitura devolve mais de 1 MiB
- **THEN** a leitura é interrompida, as regras dependentes saem `nao_verificado` citando o
  limite de tamanho e as demais regras são avaliadas

### Requirement: Código de saída com precedência
A ferramenta MUST terminar com o primeiro código que se aplica, nesta ordem: `2` erro de uso ·
`3` host inalcançável, conexão perdida ou chave de host divergente · `1` ao menos um desvio ·
`4` nenhum desvio e ao menos um `nao_verificado` · `0` todas as regras conformes. Erro não
previsto da própria ferramenta MUST terminar com `5`, sem relatório (PRD P5).

#### Scenario: Desvio e não verificado juntos
- **WHEN** a conformidade tem um `desvio` e um `nao_verificado`
- **THEN** o código de saída é `1`

#### Scenario: Só não verificado
- **WHEN** nenhuma regra tem `desvio` e ao menos uma tem `nao_verificado`
- **THEN** o código de saída é `4`

### Requirement: A credencial não sai em nenhum canal
A ferramenta MUST NOT emitir no stdout, no stderr, no JSON nem em log, em nenhum desfecho, o
conteúdo da chave privada, material derivado da parte privada ou o caminho do arquivo da chave;
mensagens MUST citar o parâmetro, não o valor. Stack trace e log de biblioteca de terceiros,
inclusive de execução em segundo plano, MUST NOT chegar ao stderr (PRD I2).

#### Scenario: Busca da chave nas saídas
- **WHEN** as saídas de execuções com sucesso, com desvio, com host inalcançável, com chave
  recusada e com fingerprint divergente são examinadas
- **THEN** nenhuma linha do conteúdo da chave privada nem o caminho do arquivo aparece em
  stdout, stderr ou JSON

#### Scenario: Erro inesperado
- **WHEN** ocorre uma exceção não prevista durante a execução
- **THEN** o stderr traz uma linha de erro sem stack trace e sem o caminho da chave

