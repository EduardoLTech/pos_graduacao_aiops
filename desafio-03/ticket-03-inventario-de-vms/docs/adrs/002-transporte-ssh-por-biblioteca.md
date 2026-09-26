---
adr_number: "002"
status: aceito
created: 2026-09-26
supersedes: ""
superseded_by: ""
---

# ADR 002: A conexão SSH é feita por biblioteca embutida (paramiko), não pelo cliente `ssh` do sistema

## Contexto
A linguagem é Python (ADR 001). A ferramenta precisa abrir uma sessão SSH com a chave recebida
e executar leituras no host. Três exigências do PRD pesam sobre como essa conexão é feita:

- host inalcançável tem de falhar com mensagem que **nomeia a causa** (endereço errado, chave
  recusada, SSH fora do ar), sem stack trace e sem ser confundido com host conforme (PRD P7);
- a ferramenta autentica **só** com a chave informada, sem recorrer a outras chaves nem a agente
  da máquina de quem opera (PRD I6);
- a chave privada não aparece em saída, log ou mensagem de erro (PRD I2).

A ferramenta roda em Windows e em Linux.

## Alternativas Consideradas
- **Biblioteca SSH embutida (paramiko)** — as falhas chegam como exceções distinguíveis por
  tipo: autenticação recusada e chave com passphrase têm exceção própria da biblioteca; conexão
  recusada, tempo esgotado e nome que não resolve chegam como exceções de rede do próprio
  Python (ou agregadas pela biblioteca) — em todos os casos, tipo e não texto, e se traduzem
  direto em mensagem e código de saída; uso de agente e de chaves padrão se desliga por parâmetro; a
  chave de host apresentada fica acessível para registrar o fingerprint (ADR 004); o
  comportamento é o mesmo em Windows e Linux. Contra: dependência de terceiro no caminho da
  credencial; não herda a configuração `~/.ssh/config` do operador (proxy, jump host).
- **Cliente `ssh` do sistema, chamado como subprocesso** — reaproveita `~/.ssh/config`, jump
  host e algoritmos do OpenSSH instalado. Contra: a causa de uma falha só existe como texto do
  stderr, que muda entre versões, idiomas e entre o OpenSSH do Windows e o do Linux; separar
  "chave recusada" de "host fora do ar" vira interpretação de texto; desligar agente e chaves
  padrão depende de opções que precisam ser repetidas em toda chamada.

## Decisão
Biblioteca embutida (paramiko). O que pesou foi o PRD P7: a mensagem que diz o que houve tem de
ser confiável, e erro tipado é contrato, enquanto stderr de outro programa é texto que pode
mudar sem aviso. Verificado em 2026-09-26: paramiko 5.0.0 (PyPI, publicado em 2026-05-09)
instala e importa em Python 3.14.3, carrega chave Ed25519, reconhece chave com passphrase por
exceção própria e expõe os parâmetros para desligar agente e busca de chaves.

## Consequências
- **Positivas:** classificação de falha de conexão sem parsing de texto; mesma lógica em Windows
  e Linux; controle explícito de qual chave é usada.
- **Negativas:** `~/.ssh/config` do operador é ignorado — host atrás de jump host ou proxy não é
  alcançável sem trabalho adicional; a biblioteca pode ficar atrás do OpenSSH em algoritmos
  novos; Python 3.14 não é versão declarada pela biblioteca (só testada aqui); a biblioteca
  registra log próprio (inclusive de uma thread de transporte em segundo plano) que pode citar o
  arquivo da chave ou imprimir traceback no stderr — precisa ser silenciado para cumprir PRD I2.
- **Neutras / trade-offs aceitos:** a política de chave de host desconhecida deixa de ser herdada
  do `known_hosts` do sistema e passa a ser decisão da ferramenta (ADR 004).
