# Exercício 04 - Framework TAG

## 1. Prompt
O prompt completo está registrado no arquivo prompt.txt e a resposta no arquivo JanelaContexto.md

## 2. Modelo
O modelo utilizado é o **Gemini 3.5 Flash (Medium)**, rodando na IDE Antigravity, escolhido por sua eficiência na estruturação de queries SQL robustas e aplicação correta das regras do banco PostgreSQL.

## 3. Output
A resposta gerada pelo modelo está no arquivo JanelaContexto.md e a query SQL no arquivo query.sql

## 4. Justificativa
Os componentes do framework TAG estão no prompt estruturados da seguinte forma:
* **Task:** Define que uma execucao precisa ser feita para criar uma query sql que traga informacoes dos ultimos 6 meses do crescimento das transacoes organizados por categoria.
* **Action:** Define as informacoes que precisam ser consideradas para criar a query sql. Indicando as tabelas para a criacao das querys.
* **Goal:** Trazer o query sql pronta para ser executada.
