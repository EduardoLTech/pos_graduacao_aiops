# Evidência — execução real contra host Linux por SSH

Coletada em 2026-09-26 por `laboratorio/coletar-evidencia.sh`, com o código final, contra uma VM
Ubuntu 24.04.5 (kernel 7.0.0-1011-gcp) criada por `laboratorio/criar.sh` (ADR 005). O usuário
da coleta é comum, criado por `useradd`, sem sudo. As execuções que chegam a conectar usaram
`--fingerprint` com a chave de host obtida pelo GCP, não pela primeira conexão; 04 e 05 não
chegam a conectar.

**Valores sintéticos:** IP externo (`203.0.113.10`, faixa de documentação), fingerprint da chave
de host e nome do host foram trocados por `laboratorio/publicar_evidencia.py`, que recusa
publicar se sobrar um valor real. O IP interno (`10.10.0.2`) é privado e ficou. Os comentários
de chave são do laboratório.

Cada execução tem quatro arquivos: `.md` (stdout), `.json` (arquivo do `--json`), `.err`
(stderr) e `.rc` (código de saída e duração).

| # | Cenário | Código | Resultado |
|---|---|---|---|
| 01 | Host conforme | 4 | Nenhum desvio; `chaves_ssh.emitidas_por` e `ssh.login_de_root` `nao_verificado` (exigem privilégio); stderr vazio |
| 02 | Repetição de 01, sem acesso administrativo entre as duas | 4 | `conformidade`, `resumo` e `inventario` idênticos a 01; só `coletado_em` muda |
| 03 | Host com desvios | 1 | 7 desvios (4 críticos, 2 altos, 1 médio) com a severidade do baseline; login de root `nao_verificado` |
| 04 | Nome que não resolve | 3 | "o nome do host não resolve"; stdout vazio; JSON anterior intacto |
| 05 | Endereço sem resposta (porta bloqueada no firewall) | 3 | "o host não respondeu em 6 s", em 6,6 s |
| 06 | Chave recusada | 3 | "autenticação recusada" |
| 07 | Fingerprint esperado errado | 3 | mostra esperado e apresentado; não autentica |
| 08 | SSH fora do ar (parado no host) | 3 | "conexão recusada na porta 22" |

Nos casos 04–08 o `.json` contém `anterior`: o arquivo existia antes com esse texto e a
ferramenta não o tocou.

### O que o cenário 03 exercita

- `swap.habilitado`: swap de 1 GiB, reportado `1G` (o `/proc/swaps` desconta 4 KiB de cabeçalho).
- `portas_em_escuta.somente_rede_interna`: node_exporter em todos os endereços (`9100 em *`).
- `portas_em_escuta.publicas_permitidas`: o `rpcbind` abre a 111 em todos os endereços.
- `servicos.proibidos` e `servicos.ativos`: `rpcbind.socket` ativo, chrony parado.
- `ntp.sincronizado`: relógio marcado como não sincronizado.
- `chaves_ssh.emitidas_por`: três chaves fora da plataforma — uma pessoal (`neo@laptop`), uma
  com comentário hostil (`\x1b[2K`, `|`), escapado no Markdown sem quebrar a tabela, e uma numa
  conta de serviço com shell `nologin` (`legado@fornecedor`), que também autentica e por isso
  também é lida.
- `ssh.login_de_root`: o host foi posto em `prohibit-password`, mas o valor efetivo exige root
  para ser lido e sai `nao_verificado` — como previsto no PRD. O desvio de login de root só é
  provado nos testes (`tests/test_regras.py`); nenhuma execução real com usuário comum o vê.

Pelo mesmo motivo, **nenhuma execução real sai com código 0**: com usuário comum, um host
conforme sai `4`.

No JSON, `encontrado` vai com tipo (booleano, lista de nomes, lista de `{porta, bind}`); a frase
(`true (1G)`, `ausente: chrony`) é só do Markdown. Cada porta traz `conta` e `unidade` (dono do
socket e unidade do systemd, legíveis por usuário comum); `processo` fica `null` quando o
processo é de outro usuário.

## A ferramenta só lê (PRD I1)

- `00-controle-*` — rodada de controle: mesma janela e mesmos acessos administrativos, sem a
  ferramenta.
- `01-marca.txt` — instante da marca criada no host antes de 01.
- `02-arquivos-alterados.txt` — o que mudou no disco desde a marca, depois de 01, 02 e 35 s de
  espera: os mesmos arquivos do controle (`auth.log`, journal, `syslog`, cache da mensagem de
  login) mais o journal do usuário de coleta, que é o próprio login. Nenhum arquivo fora dos
  registros de login.
- `02-servicos-iniciados.txt` — journal no mesmo intervalo: sessões de login, o gerenciador de
  sessão do usuário, e `gce-workload-cert-refresh.service`, disparado por timer do GCP a cada 10
  minutos (15:22, 15:32, 15:42, 15:53, 16:03), sem relação com a ferramenta.

Uma versão anterior da ferramenta lia o NTP com `timedatectl`, que ativava o
`systemd-timedated` no host; a medição com este mesmo método levou à troca (ver
`../curadoria.md`). O `timedatectl` que ainda aparece nos scripts do laboratório é da conta
administrativa, fora das janelas medidas.

## A chave privada não sai (PRD I2)

`09-busca-da-chave.txt`: nas 24 saídas (`.md`, `.json`, `.err`) das 8 execuções, a busca por cada
linha das duas chaves privadas usadas (a de coleta e a recusada em 06) e pelo caminho de cada
uma deu zero ocorrências. O stderr só tem conteúdo nos casos de código 3, sempre uma linha, sem
stack trace.
