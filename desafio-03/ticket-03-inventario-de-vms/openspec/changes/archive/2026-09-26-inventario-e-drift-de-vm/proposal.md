## Why

O inventário do parque é mantido à mão e envelheceu: não há como responder quantas VMs estão
fora do padrão nem priorizar correção. Não existe agente nas VMs, e ninguém vai instalar um; o
que existe em toda VM é acesso por chave SSH. O comportamento esperado já está especificado no
PRD-0001 e as decisões técnicas nos ADRs 001–005 (`docs/`); esta change leva isso ao código.

## What Changes

- Nova ferramenta de linha de comando, em Python, que recebe endereço, usuário, caminho da chave
  privada e, opcionalmente, o fingerprint esperado da chave de host e o arquivo de saída JSON.
- Conexão SSH por biblioteca embutida (paramiko), usando só a chave informada, com falha de
  conexão classificada por tipo e mapeada para código de saída.
- Coleta só por leitura, com o usuário da conexão, sem copiar nada para o host e sem elevação de
  privilégio.
- Avaliação das 11 regras do `baseline.yaml` versão 1, com veredito `conforme`, `desvio` (com a
  severidade do baseline) ou `nao_verificado` (com motivo).
- Relatório em Markdown no stdout e em JSON no arquivo indicado, gerados da mesma coleta.
- Códigos de saída para pipeline: `0` conforme, `1` desvio, `2` erro de uso, `3` host
  inalcançável, `4` sem desvio mas com regra não verificada.
- Scripts `gcloud` do laboratório de validação (ADR 005), fora da ferramenta.

## Capabilities

### New Capabilities

- `conexao-ssh`: parâmetros de entrada, validação de uso, conexão por chave, verificação
  opcional da chave de host, classificação de falhas, limites de tempo e tamanho, códigos de
  saída e proteção da credencial (PRD P5, P7–P11, I2, I6).
- `inventario-do-host`: coleta só por leitura e forma de cada campo do inventário, incluindo o
  bloco `host` e o determinismo entre execuções (PRD P12–P14, P24, I1, I5).
- `conformidade-baseline`: carga do `baseline.yaml`, uma entrada por regra, avaliação de cada
  uma das 11 regras, os três vereditos e o resumo (PRD P1–P4, P16–P27, I3, I4).
- `relatorio`: emissão de JSON e Markdown do mesmo dado, esqueleto do Markdown e neutralização
  de texto vindo do host (PRD P6, P15, P28, I7).

### Modified Capabilities

Nenhuma — não há specs anteriores neste projeto.

## Impact

- **Código novo:** pacote Python em `ticket-03-inventario-de-vms/` (ferramenta, testes,
  `baseline.yaml`, `pyproject.toml`).
- **Dependências novas:** paramiko (SSH) e PyYAML (baseline); pytest para testes.
- **Laboratório:** scripts `gcloud` que criam, preparam e destroem uma VM Ubuntu no GCP. Criar
  a VM tem custo e só acontece com confirmação de quem opera.
- **Documentos:** o TRD passa a registrar módulos, estrutura de pastas e testes quando o código
  existir. Correções que a implementação exigir no PRD entram na curadoria.
