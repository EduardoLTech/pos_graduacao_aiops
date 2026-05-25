# Exercício 08 - Framework RISE

## 1. Prompt
O prompt completo está registrado no arquivo [prompt.txt] e a conversa completa no arquivo [JanelaContexto.md].

## 2. Modelo
O modelo utilizado foi o **Gemini 3.5 Flash** para a estruturação técnica da resposta, elaboração de comandos complexos de Kubernetes e análise matemática das métricas do pool de conexões PostgreSQL. Se apresentou mais rapido que o Claude Sonnet 4.6.

## 3. Output
Os arquivos gerados estão na pasta `exercicio08/`:
- [post_mortem.md] — Documento técnico de Post-Mortem detalhando os gargalos do pool de conexões do Ledger, justificativa matemática para a decisão de rollback em relação ao scaling emergencial, e as ações corretivas de longo prazo (como PgBouncer e correção de leaks).
- [runbook.md] — Runbook operacional contendo comandos executáveis via `kubectl` e CLI do Argo CD organizados em fases (Diagnóstico, Rollback, Monitoramento e Escalonamento de Fila do Reactor).

## 4. Justificativa
Os componentes do framework **RISE** foram organizados no prompt da seguinte maneira:
- **Role**: Ao dar uma funcao especialista e detalhada, garante-se uma análise técnica precisa do gargalo e da decisão mais segura para confiabilidade e disponibilidade do sistema.
- **Input**: Entrega de dados detalhados fornece todos os subsídios necessários para a decisão.
- **Steps**: Sequência lógica de ações  instruindo a análise de métricas, correlação de logs com deploy, avaliação das filas ajuda na definição clara da ação imediata e ajustes pós-fix.
- **Expectation**: Expectativa de entrega de um Post-Mortem serve para justificar a escolha entre rollback e scale-up, além de um runbook com comandos `kubectl` práticos prontos para copy-paste no Runbook para auxiliar na resolução do incidente.


**RTF**
Embora o RTF seja mais simples e rápido de escrever, eu perderia os passos estruturados, fazendo com que o diagnóstico do incidente fosse feito sem ordem investigativa e nao haveria maior precisao tecnica no relatorio final em relacao a meu ambiente.

**BAB**
Focado em transição de estado, seria ótimo para definir um final idealizado. Mas sem colocar uma funcao de especialista e definicao de passos, perco a precisao tecnica podendo ocorrer decisoes sem afinidade como meu ambiente. Alem de nao ajudar muito no troubleshooting pois neste caso é um incidente nao uma migracao.
