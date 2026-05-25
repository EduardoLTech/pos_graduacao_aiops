# Exercício 07 - Framework RISE

## 1. Prompt
O prompt completo está registrado no arquivo `prompt.txt` e a conversa completa no arquivo `JanelaContexto.md`.

## 2. Modelo
O modelo utilizado inicialmente foi o **Claude Sonnet 4.6 (Thinking)** por ser necessario alto raciocinio para criar um runbook mais completo.

## 3. Output
Os arquivos gerados estão na pasta `exercicio07/`:
- `RUNBOOK_chronos_high_memory.md` — Runbook operacional completo e estruturado para triagem e mitigação do incidente de uso elevado de memória da API Chronos.

## 4. Justificativa
Os componentes do framework **RISE** foram organizados no prompt da seguinte maneira:
- **Role:**Aqui eu precisava de um papel com muita experiencia para um runbook completo e estruturado. E bem especifico para o caso.
- **Input:** Contextualizado o ambiente, as dependências, observabilidade e descricao do problema recorrente.
- **Steps:** Definido a sequência lógica e detalhada de investigação dividida em 9 passos para identificar causas raiz (banco de dados, filas, sidecar, sizing, deploys) e guiar na mitigação.
- **Expectation:** Determinado as saídas desejadas (runbook com comandos executáveis copy-paste, queries PromQL prontas, SLAs por etapa, regras de escalação claras, critérios de sucesso e pós-fix).
