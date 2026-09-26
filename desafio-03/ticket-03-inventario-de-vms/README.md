# Ticket 03 — Inventário e drift de VM por SSH

Ferramenta de linha de comando que entra numa VM por SSH, com usuário comum e só leitura,
levanta o inventário do host e o compara com o `baseline.yaml`, devolvendo Markdown no terminal
e JSON em arquivo.

| O quê | Onde |
|---|---|
| Comportamento (PRD) | `docs/prds/PRD-0001-inventario-e-drift-de-vm.md` |
| Decisões (ADRs) e baseline técnico (TRD) | `docs/adrs/`, `docs/trd.md` |
| Ciclo OpenSpec (specs vigentes; proposta, design, specs e tarefas arquivados) | `openspec/specs/` (vigentes) e `openspec/changes/archive/2026-09-26-inventario-e-drift-de-vm/` |
| Código | `inventario_vm/` |
| Testes | `tests/` |
| Host de validação e coleta de evidência | `laboratorio/` |
| Evidência de execução real | `evidencia/` (ver `evidencia/README.md`) |
| Curadoria: correções nos documentos e o que o agente entendeu diferente | `curadoria.md` |

## Instalar

Python 3.11 ou mais novo.

```sh
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[teste]"   # Linux: .venv/bin/python
```

## Rodar

```sh
inventario-vm --host 10.42.7.14 --usuario coleta --chave ~/.ssh/id_coleta \
  [--fingerprint SHA256:...] [--json relatorio.json] [--porta 22] [--baseline baseline.yaml]
```

- O Markdown sai no stdout; o JSON só é gravado quando `--json` é informado.
- `--fingerprint` fixa a chave de host esperada: se o host apresentar outra, a execução termina
  sem autenticar (ADR 004). Sem ele, a chave apresentada é aceita e registrada no relatório.
- A chave privada entra só como caminho. Formatos aceitos: OpenSSH (o padrão do `ssh-keygen`)
  e PEM tradicional, em Ed25519, ECDSA ou RSA. Chave com passphrase e PKCS#8 são recusados como
  erro de uso.
- Sem `--baseline`, vale o `inventario_vm/baseline.yaml` que acompanha a ferramenta.

### Códigos de saída

| Código | Significado |
|---|---|
| 0 | todas as regras conformes |
| 1 | ao menos um desvio |
| 2 | erro de uso (parâmetro, chave ou baseline inválido); nada foi conectado |
| 3 | host inalcançável, conexão perdida durante a coleta ou chave de host divergente; sem relatório |
| 4 | nenhum desvio, mas ao menos uma regra não verificada |
| 5 | erro interno da ferramenta (defeito, não veredito sobre o host) |

Com usuário comum, o resultado esperado de um host conforme é `4`: chaves de outras contas e
login de root efetivo exigem leitura privilegiada e saem `nao_verificado`.

## Laboratório de validação (ADR 005)

Scripts `gcloud` em `laboratorio/`, rodados em bash com o `gcloud` autenticado no projeto
desejado. Chaves e estado local (IP, known_hosts, fingerprint) ficam em `laboratorio/.chaves/`
e `laboratorio/.estado/`, fora do git.

| Passo | Comando | O que faz |
|---|---|---|
| 1 | `bash laboratorio/criar.sh --confirmo-custo` | Rede própria, firewall só `tcp:22` do IP de quem roda, VM Ubuntu 24.04 sem conta de serviço e sem chaves SSH do projeto; obtém a chave de host pelo GCP (guest attributes), não pela primeira conexão |
| 2 | `bash laboratorio/preparar-conforme.sh` | Cria o usuário `coleta` (sem sudo) e deixa o host conforme ao baseline |
| 3 | `bash laboratorio/preparar-desvios.sh` | Introduz swap, 9100 em `0.0.0.0`, `rpcbind.socket`, chrony parado, chave pessoal e chave com comentário hostil |
| 4 | `bash laboratorio/destruir.sh --confirmo` | Apaga VM, firewall, sub-rede e rede |

A VM tem custo enquanto existir. A usada na evidência de `evidencia/` foi criada, medida e
destruída em 2026-09-26, com a destruição conferida por listagem no GCP. A preparação usa uma conta administrativa separada e roda
fora das janelas de medição: acesso administrativo entre duas execuções quebraria a prova de
repetição.

## Testar

```sh
.venv/Scripts/python -m pytest -q
```

A suíte não precisa de host: as regras e o relatório rodam sobre saídas brutas gravadas, e a
conexão roda contra um servidor SSH em processo (`tests/servidor_ssh.py`), que cobre
autenticação, fingerprint, limites de leitura e queda de conexão. Ele não tem `sshd`, systemd
nem shell: a validação contra host real é a do laboratório.
