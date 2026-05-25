# Exercício 05 - Framework BAB

## 1. Prompt
O prompt completo está registrado no arquivo prompt.txt e a resposta no arquivo JanelaContexto.md.

## 2. Modelo
O modelo utilizado é o **Gemini 3.5 Flash (Medium)**, rodando na IDE Antigravity, escolhido para testar a nova versdao do Gemini.

## 3. Output
A resposta gerada pelo modelo está no arquivo JanelaContexto.md e o guia de atualização e rollback detalhado está no arquivo atualizacao_k8s.md. Os manifests gerados são:
*   [deployment.yaml]
*   [secret.yaml]
*   [serviceaccount.yaml]
*   [service.yaml]
*   [pdb.yaml]
*   [networkpolicy.yaml]

## 4. Justificativa
Os componentes do framework estão no prompt separados por:
*   **Before:** Descreve a situação atual/legada (um arquivo de deployment K8s desatualizado e sem boas práticas de segurança, com credenciais em texto claro e imagem genérica).
*   **After:** Define os requisitos de segurança e confiabilidade exigidos para a nova versão (alta disponibilidade, versionamento, isolamento de segredos, recursos limitados, probes de vida, etc.).
*   **Bridge:** Detalha a ponte técnica que deve ser construída para sair do estado "Before" e alcançar o "After" (geração dos novos arquivos de infraestrutura, estratégia de zero-downtime e plano de rollback explicados em documento markdown).
