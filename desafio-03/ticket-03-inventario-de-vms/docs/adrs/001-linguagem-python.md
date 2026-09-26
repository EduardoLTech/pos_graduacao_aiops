---
adr_number: "001"
status: aceito
created: 2026-09-26
supersedes: ""
superseded_by: ""
---

# ADR 001: A ferramenta de inventário é escrita em Python

## Contexto
O enunciado pede que a linguagem seja uma decisão registrada, não uma escolha feita no meio do
código. A ferramenta roda na máquina de quem opera (Windows ou Linux), conecta por SSH, lê
YAML (`baseline.yaml`), compara versões e emite JSON e Markdown. Não há requisito de
desempenho: é um host por execução, e o tempo é dominado pela rede.

A outra ferramenta de conformidade do mesmo desafio (conferência de manifests do Ticket 01) já é
um script Python, executado pelo mesmo operador na mesma máquina.

## Alternativas Consideradas
- **Python** — mesma stack da ferramenta do Ticket 01; YAML, JSON e SSH têm bibliotecas
  maduras; o operador já tem o interpretador. Contra: exige interpretador e dependências
  instaladas na máquina de quem roda, em vez de um único arquivo.
- **Go** — gera um binário único, sem dependência na máquina do operador, e tem cliente SSH na
  biblioteca estendida da linguagem. Contra: segunda stack no mesmo conjunto de ferramentas, sem
  ganho que o caso de uso cobre — distribuição em binário único não é requisito do enunciado.

## Decisão
Python. O que pesou foi manter uma stack só entre as ferramentas de conformidade que o mesmo
time opera; a vantagem do Go (binário único) resolve um problema de distribuição que o
enunciado não coloca.

## Consequências
- **Positivas:** uma stack só para manter; a máquina de quem opera já tem o necessário para
  rodar o Ticket 01, e passa a rodar este também.
- **Negativas:** a ferramenta depende de dependências de terceiros instaladas no ambiente de
  quem roda; para o pipeline, isso significa preparar um ambiente Python antes da execução.
  A versão do interpretador disponível no ambiente de desenvolvimento (3.14) é mais nova que a
  última declarada pela biblioteca SSH escolhida (ADR 002) — verificado em 2026-09-26 que
  instala e importa, mas não é combinação declarada pelo fornecedor.
- **Neutras / trade-offs aceitos:** se um dia o Roster exigir distribuição sem interpretador,
  isso é realidade nova e gera ADR novo, não ajuste deste.
