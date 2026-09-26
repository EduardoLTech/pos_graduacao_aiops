## Context

O comportamento está no PRD-0001 e nas specs desta change; as decisões que atravessam o projeto
estão nos ADRs: Python (001), paramiko em vez do `ssh` do sistema (002), coleta só por leitura
e sem privilégio com três desfechos para dado ausente (003), chave de host aceita e registrada
com fingerprint esperado opcional (004) e laboratório em VM no GCP por `gcloud` (005). Este
documento decide o que os ADRs deixaram aberto: estrutura do código, o comando que coleta cada
dado, como a falta de privilégio é reconhecida, e como o laboratório é montado.

Restrições que moldam o desenho: a ferramenta roda em Windows e Linux; o host é Ubuntu com
systemd; o usuário da coleta é comum; nada é escrito no host.

## Goals / Non-Goals

**Goals:**
- Separar a parte que depende do host (conexão e leitura) da parte pura (interpretação,
  avaliação, relatório), para que quase todo o comportamento das specs seja testável sem host.
- Cada leitura com desfecho explícito — lida, sem privilégio ou falha — que a avaliação consome
  sem saber como a leitura foi feita.
- Laboratório reproduzível por script, com estado conforme e estado com desvios.

**Non-Goals:**
- Suporte a distribuição sem systemd ou sem `ss`/`iproute2`: a leitura falha e a regra sai
  `nao_verificado`, que é o comportamento especificado.
- Paralelismo, vários hosts, cache de chave de host (fora do escopo do PRD).
- Empacotamento para distribuição (PyPI, binário).

## Decisions

### D1 — Estrutura em camadas puras em volta de uma camada de transporte

```
inventario_vm/
  cli.py         parâmetros, validação de uso, códigos de saída, captura de erro final
  baseline.py    carga e validação do baseline.yaml (versao 1, regras conhecidas)
  conexao.py     paramiko: carga da chave, política de chave de host, classificação de
                 falha, execução de leitura com limite de tempo e tamanho
  coleta.py      tabela fixa de leituras; devolve Leitura(status, saida, motivo) por nome
  inventario.py  interpretação pura das saídas brutas → campos do inventário
  regras.py      avaliação pura das 11 regras → entradas de conformidade e resumo
  relatorio.py   JSON e Markdown, neutralização de texto do host
  erros.py       erros que encerram com código próprio (2 e 3)
  baseline.yaml  cópia versionada do padrão do enunciado, instalada junto do pacote
                 (corrigido na implementação: na raiz, o padrão só funcionaria rodando do
                 diretório do projeto)
tests/           unitários com saídas brutas gravadas; integração opcional contra host
laboratorio/     scripts gcloud (ADR 005)
```

Por que assim: `inventario.py`, `regras.py` e `relatorio.py` recebem texto e devolvem dados;
testam-se com saídas reais gravadas do laboratório, sem rede. Alternativa descartada: uma
classe por regra que coleta e avalia — acopla leitura e veredito e obriga host em todo teste.

### D2 — Uma leitura por comando fixo, com idioma fixo

Cada leitura é um `exec_command` com string constante, prefixada por `LC_ALL=C` (o servidor
SSH não é obrigado a aceitar variáveis de ambiente do cliente, então o prefixo vai no próprio
comando). Nenhuma string enviada ao host é montada a partir de dado do host (PRD I7).

| Leitura | Comando | Alimenta |
|---|---|---|
| hostname | `cat /proc/sys/kernel/hostname` | `host.hostname` |
| os-release | `cat /etc/os-release` | `so` (ID; versão pontual de `VERSION` quando começa por `VERSION_ID`, senão `VERSION_ID`) |
| kernel | `uname -r` | `kernel.versao` |
| unidades | `systemctl list-units --type=service,socket --state=active --no-legend --plain --no-pager` | `servicos`, `ntp.mecanismo` |
| swap | `cat /proc/swaps` | `swap` (tamanho em KiB → unidade) |
| portas | `ss -Hltnpe` | `portas_em_escuta`: `-p` dá o processo só das portas do próprio usuário; `-e` dá uid do dono (omitido quando é 0) e cgroup (unidade systemd) de todas |
| contas | `getent passwd` | nome da `conta` dona de cada porta, a partir do uid |
| chaves | script constante que percorre as contas, ver D4 | `chaves_ssh`, `chaves_ssh_fontes_nao_lidas` |
| sshd | `sshd -T`, ver D3 | `ssh.login_de_root` |
| ntp | `python3 -c` constante que chama `adjtimex` só leitura e imprime retorno e `status` | `ntp.sincronizado` (mesmo critério do `systemd-timedated`: não sincronizado se `TIME_ERROR` ou `STA_UNSYNC`) |

*Corrigido na validação:* o desenho previa `timedatectl show -p NTPSynchronized`. Medido na VM,
ele ativa o `systemd-timedated` pelo D-Bus, que sobe, cria diretórios privados em `/tmp` e
`/var/tmp` e os apaga ao sair — a leitura ligava um serviço no host, contra o PRD I1. O
`adjtimex` lê o mesmo dado do kernel sem ativar nada; custa depender de `python3` no host (no
Ubuntu, prioridade `important`), e sem ele a regra sai `nao_verificado` por falha de coleta.

Alternativa descartada: um único script com todas as leituras numa ida e volta — mais rápido,
mas um erro no meio perde todas as leituras seguintes e mistura saídas; várias idas e voltas já
eram consequência aceita no ADR 003.

### D3 — "Sem privilégio" reconhecido por fato do host, não por texto de erro

A mensagem de erro de um comando muda entre versões e idiomas; o ADR 002 recusou interpretar
texto na conexão e a mesma razão vale aqui. Para `sshd -T`, que precisa ler as chaves de host
e só roda como root: se o comando falha e a própria sessão informa `id -u` diferente de `0`, o
desfecho é "sem privilégio"; qualquer outra falha é "falha de coleta". Para arquivos de chave,
o desfecho vem do teste do shell (`test -r` / `test -e`), não da mensagem de `cat`.

### D4 — Fontes de chave: o que se lê e o que se declara não lido

1. Todas as contas de `getent passwd`. *Corrigido após revisão:* o desenho pulava contas com
   shell `nologin` e `false`, mas o shell não impede a chave de autenticar nem de abrir túnel;
   com coleta como root isso dava falso `conforme` numa regra crítica. Conta com diretório
   inexistente conta como sem chave (`ausente`), como o `sshd` a veria.
2. Uma única leitura com script de shell **constante**, que percorre `getent passwd` no próprio
   host e emite, por conta, uma linha `<conta em base64> <status> <conteúdo em base64>`, com
   status `lida`, `ausente` (diretório atravessável e arquivo inexistente) ou `sem_permissao`
   (decidido por `test -r`/`test -x`). O nome e o diretório da conta nunca saem do host para
   compor comando (PRD I7), e o base64 impede que um nome ou comentário hostil quebre o formato
   da saída. Alternativa descartada: um comando por conta montado com o nome lido — exigiria
   provar o escape de texto hostil, e um erro nele vira execução de comando no host.
3. A configuração efetiva de fontes (`AuthorizedKeysFile`, `AuthorizedKeysCommand`) vem de
   `sshd -T`; sem ela, a fonte "configuração efetiva do servidor SSH" entra em
   `chaves_ssh_fontes_nao_lidas`. Com usuário comum isso sempre acontece, e a regra sai
   `nao_verificado` salvo desvio encontrado — como o PRD P25 prevê.

### D5 — Conexão e classificação de falha

- Chave: carregador de cada classe (`Ed25519Key`, `ECDSAKey`, `RSAKey`);
  `PasswordRequiredException` → código 2. *Corrigido na implementação:* o desenho previa
  `PKey.from_path`, mas com chave protegida ele levanta `TypeError` genérico, e só o carregador
  por classe distingue passphrase por tipo. PKCS#8 não é aceito por nenhum dos dois.
- Erro não previsto: código 5 ("erro interno"), só com o tipo da exceção. *Lacuna do PRD:* P5
  não define código para defeito da própria ferramenta, e nenhum dos cinco existentes serve
  sem mentir sobre o host.
- `SSHClient.connect(..., pkey=..., allow_agent=False, look_for_keys=False, timeout=10,
  banner_timeout=10, auth_timeout=10)` dentro de um orçamento total de 15 s.
- Política de chave de host própria: registra algoritmo e fingerprint (`SHA256:` + base64 sem
  padding) e, com fingerprint esperado, compara e levanta exceção própria antes da
  autenticação. Nenhum `known_hosts` é carregado nem gravado.
- Mapeamento por tipo: `socket.gaierror` → nome não resolve; `TimeoutError`/`socket.timeout` →
  não respondeu; `NoValidConnectionsError`/`ConnectionRefusedError` → conexão recusada;
  `AuthenticationException` → chave recusada; `SSHException` no banner → o serviço não fala
  SSH; exceção própria → chave de host divergente. Qualquer erro de canal depois da
  autenticação → conexão caiu durante a coleta.
- Leitura com limite: laço de `recv` com prazo de 20 s e teto de 1 MiB + 1 byte; ao estourar,
  fecha o canal e devolve falha com o limite que estourou.

### D6 — Silêncio de bibliotecas e erro final

Logger `paramiko` sem handler e sem propagação; `threading.excepthook` substituído para não
imprimir traceback da thread de transporte; o `main` captura toda exceção e escreve uma linha
com o tipo do erro, sem argumentos que possam conter caminho. As mensagens citam o nome do
parâmetro (`--chave`), nunca o valor.

### D7 — Relatório

Um objeto de relatório é montado uma vez e serializado duas vezes (JSON e Markdown), o que dá
P6 por construção. O JSON só é gravado depois de o relatório existir, num arquivo temporário no
mesmo diretório renomeado sobre o destino — falha antes disso deixa o arquivo anterior intacto.
Neutralização no Markdown: caracteres de controle viram `\xNN`, `|` vira `\|`, quebra de linha
vira `\n` literal, cada valor limitado a 200 caracteres com marcação de corte.

### D8 — Laboratório (ADR 005)

Scripts bash em `laboratorio/`, rodados pelo operador com `gcloud` já autenticado:
- `criar.sh` — VPC e sub-rede próprias; firewall só `tcp:22` a partir do IP do operador; VM
  `e2-small` Ubuntu 24.04 LTS, sem conta de serviço, `block-project-ssh-keys=TRUE`,
  `enable-oslogin=FALSE`; imprime o fingerprint da chave de host a partir da saída serial.
- `preparar-conforme.sh` — usuário de coleta por `useradd` com chave dedicada comentada
  `coleta@metacortex-platform`; containerd, chrony, `node_exporter.service` escutando só no IP
  interno; sem swap; `PermitRootLogin no`.
- `preparar-desvios.sh` — swap de 1 GiB, `node_exporter` em `0.0.0.0:9100`, `rpcbind.socket`
  ativo, chrony parado, chave extra sem comentário da plataforma na conta de coleta.
- `destruir.sh` — apaga VM, firewall, sub-rede e VPC.

A preparação usa uma conta administrativa separada da conta de coleta e só roda fora das
janelas de medição (ADR 005: acesso administrativo entre execuções quebra a prova de
repetição).

## Risks / Trade-offs

- [paramiko em Python 3.14 não é combinação declarada] → a suíte roda em 3.14 e o pipeline pode
  fixar 3.13, a última declarada; registrado no ADR 001.
- [`sshd -T` com usuário comum sempre falha] → login de root e fontes de chave ficam
  `nao_verificado`; é o resultado previsto pelo PRD, não defeito.
- [o script de contas (D4) depende de `getent`, `base64` e `test` no host] → todos são do
  sistema base do Ubuntu; ausência vira falha de coleta da regra de chaves.
- [o laboratório inseguro de propósito tem IP externo] → firewall só do IP do operador; VM
  destruída ao fim; custo só enquanto existe.
- [pacote do Ubuntu instala `prometheus-node-exporter.service`, que não satisfaz
  `node_exporter`] → o laboratório cria a unidade `node_exporter.service` para o estado
  conforme; o nome de pacote diferente fica como caso de teste unitário do P18.

## Open Questions

- Fingerprint da chave de host pela saída serial do GCP: confirmar que a imagem Ubuntu 24.04 o
  imprime; senão, obter pelo primeiro acesso administrativo e registrar como tal.
- Grupos do usuário criado por `useradd` e presença de `ssh.socket` no Ubuntu 24.04: conferir
  na VM (itens não verificados no PRD).
