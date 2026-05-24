# Context Window Content

## User Prompt 1

#Role
Você é um SRE sênior com 10 anos de experiência em Kubernetes, AWS, Postgresql, observabilidade com Prometheus e Grafana, e resposta a incidentes de alta severidade (SEV1/SEV2) em ambientes de producao.

#Input
Ambiente do sistema Chronos:
Chronos roda no EKS, namespace production, 6 réplicas com HPA configurado (min 4, max 12, CPU target 70%).
Deploy via Argo CD a partir do repositório hvt/chronos-api.
Dependências diretas: database Ledger (PostgreSQL) e Reactor (filas SQS).
Observabilidade: métricas expostas em /metrics, logs centralizados no prometheus Beacon, dashboards em Grafana.
Ferramentas disponíveis para o plantão: kubectl, aws cli, argocd cli.
Canal de plantão: #oncall-chronos no Slack.
Time sênior de escalação: @chronos-core (SLA de resposta: 15 minutos em horário comercial, 30 fora).
Problema: Toda semana, em média 4 vezes, o Beacon dispara o mesmo alerta no canal de plantão: [CRITICAL] High memory usage on Chronos API pods (>85% for 10min).

# Steps
1. Confirmar o estado atual dos pods e coletar logs de uso de processamento e memoria
2. Analisar métricas de memória no Prometheus (últimas 4 semanas)
3. Analisar a partir de 2 horas antes de cada evento de disparo dos alertas, o estado do banco de dados (querys em execucao, uso de memoria), e se há mensagens paradas nas filas SQS. Fazer correlacao entre o uso destes componentes e o momento que ocorrem o alto consumo de memoria. 
4. Verificar se pode haver correlacao entre horario dos incidentes com deploys via argo cd.
5. Verificar se o problema é no container principal ou no sidecar (istio-proxy/envoy)
6. Avaliar se o sizing está subdimensionado
7. Definir ação imediata de mitigação (ajuste de limits, rollback ou scale horizontal)
8. Documentar critérios de escalação (quando envolver o time de desenvolvimento)
9. Propor ajustes definitivos e critério de validação pós-fix

# Expectation
Espero um runbook operacional completo com:
- Comandos kubectl prontos para copiar e colar em cada etapa
- Queries PromQL para investigação de consumo de memoria e processamento, assim como informacoes de filas e uso de querys no banco de dados
- Tempo máximo por etapa (total não deve passar de 15 minutos)
- Critérios claros de quando escalar para SEV1 e acionar o canal de plantao do slack.
- Critério de sucesso: o runbook tem que permitir que qualquer plantonista consiga seguir de ponta a ponta sem depender de quem conhece o sistema.
- Os documentos devem ficar em exercicio07

## Model Response 1

Runbook operacional completo criado e salvo em `exercicio07/RUNBOOK_chronos_high_memory.md` contendo as seguintes definições:

**Estrutura de 9 Etapas de Investigação e Resolução rápida (≤ 15 min total):**
- **Etapa 1: Confirmar o estado atual dos pods** — Comandos `kubectl get pods`, `kubectl top pods`, `kubectl get events --field-selector reason=OOMKilling` e filtragem estruturada de logs.
- **Etapa 2: Analisar métricas de memória no Prometheus** — 6 queries PromQL incluindo análise de working set %, série histórica de 4 semanas, taxa de crescimento/leak, contador de OOMKills, uso de CPU e comportamento do HPA.
- **Etapa 3: Correlacionar com banco de dados Ledger (Postgres) e filas SQS (Reactor)** — PromQLs e comandos `aws sqs get-queue-attributes` para buscar conexões ativas, querys longas (>30s), uso de memória buffers e acúmulo de mensagens na fila principal ou DLQ com correlação a partir de 2h antes de cada alerta.
- **Etapa 4: Verificar correlação com Deploys Argo CD** — Uso de `argocd app history` para cruzar logs de release com as janelas dos incidentes.
- **Etapa 5: Identificar container problemático** — Diferenciação de consumo de recursos por container (`chronos-api` vs sidecar `istio-proxy/envoy`).
- **Etapa 6: Avaliar subdimensionamento (Sizing)** — Relação entre uso real/limit, pressão sobre nodes e VPA recommendations.
- **Etapa 7: Mitigação Imediata** — Três rotas de ação claras com comandos prontos:
  - *Opção A:* Scale horizontal manual (`kubectl scale`).
  - *Opção B:* Patch temporário de limits (`kubectl patch`).
  - *Opção C:* Rollback rápido via cli (`argocd app rollback`).
- **Etapa 8: Critérios de Escalação** — Regras explícitas para acionamento de SEV1 e SEV2 no Slack `@chronos-core` com template pronto para mensagens.
- **Etapa 9: Ajustes Definitivos e Critérios de Validação** — Plano pós-fix para vazamento de memória (profiling), subdimensionamento (VPA/HPA custom metrics), filas SQS (circuit breaker) e sidecar, além do query PromQL para validação de sucesso por 14 dias (baseline vs. target).
