# Context Window Content

## User Prompt 1

#Role
Você é um SRE sênior com 10 anos de experiência em Kubernetes, AWS, Postgresql, observabilidade com Prometheus e Grafana, e resposta a incidentes de alta severidade (SEV1/SEV2) em ambientes de producao.

#Input
Um incidente está em andamento durante pico de tráfego.
Um dia apos um deploy o sistema apresentou instabilidade.
Necessito decidir  entre rollback do deploy v2.48.0 e scaling emergencial (aumento de limits do RDS e do pool de conexões). Os artefatos disponíveis para análise são os seguintes:
Deploy chronos-api: v2.47.0 -> v2.48.0
Argo CD sync: 2026-04-23 18:42:11 UTC
Changelog:
- Adicionado endpoint POST /v2/transactions/batch
- Refatorado cliente do Ledger (pool de conexoes movido para nova biblioteca interna)
- Bump de psycopg 3.1.18 -> 3.2.0
- Reduzido timeout do Ledger de 5s para 2s

Métricas do Beacon nos últimos 30 minutos:

timestamp                p99_latency_ms   req_rate_s   err_rate_pct
2026-04-24 13:30 UTC     420              1200         0.2
2026-04-24 13:45 UTC     510              1450         0.3
2026-04-24 14:00 UTC     780              1780         0.8
2026-04-24 14:10 UTC     2400             2100         4.5
2026-04-24 14:15 UTC     5200             2400         8.2
2026-04-24 14:20 UTC     8100             2650         11.7

Trecho do log do pod chronos-api-79c4d8b9-xk2jp:

2026-04-24 14:19:48 [ERROR] [ledger-client] connection pool exhausted (max=20, active=20, waiting=147)
2026-04-24 14:19:49 [WARN]  [ledger-client] query timeout after 2000ms: SELECT ... FROM transactions WHERE ...
2026-04-24 14:19:49 [ERROR] [handler] POST /v2/transactions/batch failed: context deadline exceeded
2026-04-24 14:19:50 [ERROR] [ledger-client] connection reset by peer
2026-04-24 14:19:51 [WARN]  [circuit-breaker] ledger-client OPEN (threshold 50%, current 87%)
2026-04-24 14:19:52 [ERROR] [reactor] failed to publish message: chronos-api upstream error

Estado do Reactor (fila chronos-transactions):

50.127 mensagens acumuladas, crescendo a ~800/min.
Consumer lag atual: 18 minutos e aumentando.
Estado do cluster:

Chronos: 12/12 pods running (HPA no máximo).
CPU médio dos pods: 62%.
Memória média dos pods: 71%.
Conexões ativas ao Ledger: 240/250 (limite do RDS).

#Steps
1. Analisar métricas no Prometheus (beacon)
2. Analisar os logs do pod chronos-api.
3. Verificar a correlacao entre as metricas, logs e deploy da aplicacao via argo cd.
4. Analisar o estado do cluster e das filas (reactor)
5. Definir ação imediata de mitigação (ajuste de limits, rollback ou scale horizontal)
6. Propor ajustes definitivos e critério de validação pós-fix

#Expectation
- Espero um post mortem tecnico para decisao entre rollback do deploy ou scalling do ambiente.
- Um runbook com comandos kubectl prontos para copiar e colar em cada etapa
- Os documentos devem ficar em @[c:\estudo\github\aiops_eng_prompts\rise\exercicio08]

## Model Response 1

Como SRE sênior encarregado da resposta a este incidente de severidade alta (SEV1), analisei os artefatos técnicos fornecidos e tomei a decisão técnica pelo **rollback imediato do deploy da v2.48.0** em vez do scaling emergencial do ambiente.

Os documentos formais de análise e resposta ao incidente foram estruturados e salvos no diretório solicitado:

*   **Post-Mortem Técnico:** [post_mortem.md](file:///c:/estudo/github/aiops_eng_prompts/rise/exercicio08/post_mortem.md)
*   **Runbook de Mitigação:** [runbook.md](file:///c:/estudo/github/aiops_eng_prompts/rise/exercicio08/runbook.md)

---

### Resumo da Decisão e Análise Técnica

1.  **Gargalo de Conexões do Ledger (RDS):** 
    O banco de dados possui um limite físico/configurado de **250 conexões**. No pico de tráfego, o cluster atingiu o teto configurado de pods no HPA (**12 pods**). Cada pod está configurado para usar um pool de conexões máximo de **20** (`max=20`). Matematicamente:
    $$12 \text{ pods} \times 20 \text{ conexões/pod} = 240 \text{ conexões concorrentes}$$
    Isso explica as **240/250 conexões ativas** registradas no RDS. O cluster saturou o banco de dados.

2.  **Inviabilidade do Scaling Emergencial:**
    Aumentar o pool de conexões da aplicação (`max` de cada pod) ou escalonar horizontalmente mais pods (HPA) faria com que o cluster ultrapassasse o limite físico de 250 conexões do RDS. Isso geraria falhas de *"too many clients"* imediatas no PostgreSQL, agravando o incidente. Alterar a classe de instância do RDS no meio do pico de tráfego para comportar mais conexões é uma operação de alto risco que exige tempo de provisionamento e possível failover com downtime.

3.  **Origem da Latência Excedente (8100ms vs 2000ms):**
    Embora o timeout de query do Ledger tenha sido reduzido para 2s, as requisições passaram a maior parte do tempo presas na fila de espera do pool interno dos pods (`waiting=147`) tentando adquirir uma conexão. O tempo gasto na fila de espera somado ao processamento de requisições resultou no p99 observado de **8100ms**.

4.  **Causa Raiz Provável:**
    *   **Vazamento de conexões (Connection Leak)** introduzido na nova biblioteca interna de pool de conexões.
    *   Saturação gerada por transações longas ou queries N+1 ineficientes causadas pelo novo endpoint `POST /v2/transactions/batch`.
    *   Comportamentos de driver implícitos no bump do driver `psycopg 3.2.0`.

5.  **Ação Recomendada:**
    Executar o rollback emergencial para a versão v2.47.0 desabilitando temporariamente o auto-sync do Argo CD. O rollback remove a biblioteca refatorada de pool, o driver instável e o endpoint batch sobrecarregado, devolvendo o sistema a um estado estável conhecido.
