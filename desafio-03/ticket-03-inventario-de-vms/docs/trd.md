# TRD — Inventário e drift de VM por SSH

> Documento técnico global do projeto. Granularidade baixa: cobre o que é global e estável.
> Regras finas ficam em ADRs.

## Stack

| Dimensão | Valor |
|---|---|
| Linguagem principal | Python (ADR 001) |
| Runtime/plataforma | Linha de comando na máquina de quem opera (Windows ou Linux); Python ≥ 3.11 declarado no `pyproject.toml`, validado em 3.14.3 |
| Framework principal | Não aplicável |
| Banco de dados | Não aplicável |
| Dependências | paramiko ≥ 4, < 6 (validado 5.0.0); PyYAML 6 (validado 6.0.3) |
| Ferramentas de build | setuptools, via `pyproject.toml`; ponto de entrada `inventario-vm` |
| Gerenciador de pacotes | pip, em ambiente virtual (`.venv`, fora do git) |

## Arquitetura

### Padrão arquitetural
Ferramenta de linha de comando, um host por execução, sem componente no host auditado: conecta
por SSH com biblioteca embutida (ADR 002), coleta só por leitura com o usuário da conexão
(ADR 003), avalia regra a regra contra o `baseline.yaml` e emite JSON e Markdown do mesmo dado.

### Estrutura de pastas dominante
```
docs/           PRD, TRD e ADRs
openspec/       ciclo OpenSpec (specs vigentes e changes arquivadas)
inventario_vm/  código da ferramenta e o baseline.yaml padrão
tests/          testes; amostras_lab/ tem saídas brutas reais da VM de validação
laboratorio/    scripts gcloud do host de validação e da coleta de evidência (ADR 005)
evidencia/      saídas das execuções reais, com valores sintéticos
```

### Módulos / camadas principais

A parte que depende do host (conexão e leitura) fica isolada; interpretação, regras e relatório
são funções puras sobre texto, testáveis sem host.

| Módulo | Responsabilidade |
|---|---|
| `cli.py` | Parâmetros, validação de uso, fluxo, códigos de saída, silêncio de bibliotecas |
| `baseline.py` | Carga e validação do `baseline.yaml` (versão 1, 11 regras) |
| `conexao.py` | paramiko: carga da chave, política de chave de host, classificação de falha por tipo, leitura com limite de tempo e tamanho |
| `coleta.py` | Tabela fixa de comandos de leitura, com idioma fixo; desfecho lida / falha |
| `inventario.py` | Interpretação das saídas brutas em inventário; falta de privilégio e saída irreconhecível viram evidência de cada leitura |
| `regras.py` | As 11 regras, os três vereditos, resumo e código de saída |
| `relatorio.py` | JSON e Markdown do mesmo objeto; neutralização do texto vindo do host; gravação atômica do JSON |
| `erros.py` | Erros que encerram com código 2 e 3 |

### Rotas

Não aplicável — ferramenta de linha de comando, sem interface HTTP.

### Modelo de dados

Não aplicável — sem persistência. A forma da saída (JSON e Markdown) é contrato de
comportamento e está no PRD-0001.

## Requisitos Não-Funcionais

| Dimensão | Requisito |
|---|---|
| Performance | Limites por execução definidos no PRD-0001 (P7, P9) |
| Disponibilidade/SLA | Não aplicável — execução sob demanda |
| Escalabilidade | Não aplicável — um host por execução |
| Segurança | Credencial e dado do host definidos no PRD-0001 (I2, I6, I7); chave de host no ADR 004; coleta sem privilégio no ADR 003 |
| Observabilidade | Não aplicável — execução sob demanda; o resultado é o próprio relatório e o código de saída |

## Dependências Externas

| Serviço / Sistema | Tipo | Constraint relevante | Dono |
|---|---|---|---|
| Host auditado (VM Ubuntu do parque) | Servidor SSH | Acesso só por chave, com usuário comum sem privilégio (ADR 003); chave de host aceita na primeira conexão (ADR 004) | Plataforma |
| Google Cloud (laboratório de validação) | Nuvem, via `gcloud` | Rede própria, VM sem conta de serviço, SSH só do IP do operador (ADR 005) | Operador do laboratório |

## Padrões

### Testes

| Item | Valor |
|---|---|
| Framework | pytest |
| Comando completo | `.venv/Scripts/python -m pytest -q` (Linux: `.venv/bin/python`), a partir da pasta do ticket |
| Cobertura mínima | Não definida; um teste por cenário das specs |
| Estratégia | Unitário sobre saídas brutas (escritas à mão e gravadas na VM real); integração local contra servidor SSH em processo (`tests/servidor_ssh.py`), sem `sshd`/systemd; validação real contra VM pelo `laboratorio/coletar-evidencia.sh` |

### Estilo de código
- Linter: Não definido
- Formatter: Não definido
- Convenções de nomenclatura: identificadores e mensagens em português, sem abreviação

### Error handling
Falha de conexão classificada por tipo de exceção, não por texto (ADR 002), e mapeada para os
códigos de saída do PRD-0001 (P5): `2` uso, `3` host, `5` defeito da ferramenta. Falha de uma
leitura afeta só as regras que dependem dela (ADR 003). Mensagens nunca repetem texto de
exceção de terceiros (pode trazer o caminho da chave).

### Logging
A ferramenta não registra log. O logger do paramiko é silenciado, avisos são ignorados e
exceção de thread não é impressa (PRD I2): o único texto no stderr é a linha de erro final.

### Autenticação / autorização
A ferramenta autentica no host por chave privada informada pelo operador, sem agente de chaves
nem chaves padrão (ADR 002). Não há autorização própria: o alcance da coleta é o do usuário da
conexão (ADR 003).

## Decisões Globais (ADRs)

| # | Título | Data | Status | Link |
|---|---|---|---|---|
| 001 | A ferramenta de inventário é escrita em Python | 2026-09-26 | aceito | [ADR 001](./adrs/001-linguagem-python.md) |
| 002 | A conexão SSH é feita por biblioteca embutida (paramiko), não pelo cliente `ssh` do sistema | 2026-09-26 | aceito | [ADR 002](./adrs/002-transporte-ssh-por-biblioteca.md) |
| 003 | A coleta usa só leituras já disponíveis no host, com o usuário comum, e o que não se lê vira `nao_verificado` por regra | 2026-09-26 | aceito | [ADR 003](./adrs/003-coleta-sem-escrita-e-sem-privilegio.md) |
| 004 | Chave de host desconhecida é aceita e registrada, salvo quando o operador informa o fingerprint esperado | 2026-09-26 | aceito | [ADR 004](./adrs/004-chave-de-host-desconhecida.md) |
| 005 | O host de validação é uma VM Ubuntu no GCP, provisionada por script `gcloud` | 2026-09-26 | aceito | [ADR 005](./adrs/005-laboratorio-vm-gcp-via-gcloud.md) |
