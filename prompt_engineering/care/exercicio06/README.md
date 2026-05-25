# Exercício 06 - Framework CARE

## 1. Prompt
O prompt completo está registrado no arquivo `prompt.txt` e a conversa completa no arquivo `JanelaContexto.md`.

## 2. Modelo
O modelo utilizado é o **Claude Sonnet 4.6 (Thinking)**, rodando na IDE Antigravity, escolhido por ser mais forte em codificacao em relacao ao Gemini 3 Flash e com melhor custo x beneficios em relacao ao Opus.

## 3. Output
Os arquivos gerados pelo modelo estão em `exercicio06/`:
- `main.tf` — 6 recursos AWS como sub-recursos separados
- `variables.tf` — 11 variáveis com `type`, `description` e blocos `validation`
- `outputs.tf` — 7 outputs com ARN e nome do bucket
- `README_S3.md` — exemplo de uso

## 4. Justificativa
Os componentes do framework CARE estão no prompt separados por:
* **Context:** Define o padrão interno da empresa, separação por ambientes e convenções de naming.
* **Action:** Define o que precisa ser feito: construção de um módulo reutilizável de S3 com tags obrigatórias e controles de segurança exigidos.
* **Result:** Define os entregáveis: arquivos `main.tf`, `variables.tf`, `outputs.tf` e `README_S3.md` com exemplo de uso.
* **Exemple:** Define a referência para construção dos arquivos.
