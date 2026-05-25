# RUNBOOK: [CRITICAL] High Memory Usage — Chronos API Pods

> **Versão:** 1.0  
> **Mantido por:** Time de Plantão / SRE  
> **Última revisão:** 2026-05-24  
> **SLA de resolução:** 15 min (triagem) · 60 min (mitigação)  
> **Canal de plantão:** `#oncall-chronos`  
> **Escalação:** `@chronos-core` (15 min horário comercial · 30 min fora)

---

## 🔴 Alerta Disparado

```
[CRITICAL] High memory usage on Chronos API pods (>85% for 10min)
```

**O que isso significa:** Um ou mais pods do Chronos API estão com uso de memória acima de 85% do seu `limit` configurado por mais de 10 minutos. Sem ação, o pod pode ser OOMKilled (reiniciado pelo kubelet), causando degradação ou indisponibilidade do serviço.

---

## ⏱️ Visão Geral das Etapas

| # | Etapa | Tempo Máximo |
|---|-------|-------------|
| 1 | Confirmar estado atual dos pods | 2 min |
| 2 | Analisar métricas de memória no Prometheus | 3 min |
| 3 | Correlacionar com banco de dados e filas SQS | 4 min |
| 4 | Verificar correlação com deploys Argo CD | 1 min |
| 5 | Identificar container problemático | 1 min |
| 6 | Avaliar subdimensionamento de recursos | 1 min |
| 7 | Executar ação imediata de mitigação | 3 min |
| **TOTAL** | | **≤ 15 min** |

---

## ETAPA 1 — Confirmar Estado Atual dos Pods (≤ 2 min)

### 1.1 — Visão geral dos pods

```bash
# Listar todos os pods do Chronos e seu status
kubectl get pods -n production -l app=chronos-api \
  -o wide \
  --sort-by='.status.startTime'
```

**O que observar:**
- Coluna `RESTARTS` > 0 → indica OOMKills anteriores
- `STATUS` = `OOMKilled` ou `CrashLoopBackOff` → situação crítica
- Pods com `AGE` muito recente → pode ser restart automático

---

### 1.2 — Uso atual de CPU e memória (top)

```bash
# Consumo real de recursos por pod
kubectl top pods -n production -l app=chronos-api \
  --containers \
  --sort-by=memory
```

**O que observar:**
- Coluna `MEMORY` próxima ou acima do `limit` configurado → risco de OOMKill iminente
- Comparar CPU vs. memória: se CPU está baixa mas memória alta → problema de memory leak, não de carga

---

### 1.3 — Inspecionar eventos recentes de OOMKill

```bash
# Eventos dos últimos 30 minutos no namespace
kubectl get events -n production \
  --field-selector reason=OOMKilling \
  --sort-by='.lastTimestamp' | tail -20

# Verificar OOMKills por pod específico (substituir <POD_NAME>)
kubectl describe pod <POD_NAME> -n production | grep -A5 "OOM\|Last State\|Exit Code"
```

---

### 1.4 — Verificar limites configurados

```bash
# Exibir requests e limits de todos os containers do deployment
kubectl get deployment chronos-api -n production \
  -o jsonpath='{range .spec.template.spec.containers[*]}{.name}{"\t"}{.resources}{"\n"}{end}'
```

**🟡 CRITÉRIO DE ESCALAÇÃO IMEDIATA:** Se `RESTARTS` ≥ 3 em qualquer pod nas últimas 2h, acionar `@chronos-core` imediatamente via `#oncall-chronos`.

---

### 1.5 — Coletar logs dos pods com maior consumo

```bash
# Logs das últimas 2 horas do container principal (substituir <POD_NAME>)
kubectl logs <POD_NAME> -n production \
  -c chronos-api \
  --since=2h \
  --timestamps=true \
  | grep -iE "error|warn|out of memory|heap|gc|exception|timeout" \
  | tail -100

# Para todos os pods simultaneamente (requer stern instalado — alternativa abaixo)
kubectl logs -n production -l app=chronos-api \
  -c chronos-api \
  --since=2h \
  --prefix=true \
  --timestamps=true \
  | grep -iE "error|oom|heap|gc|timeout" \
  | tail -200
```

---

## ETAPA 2 — Analisar Métricas de Memória no Prometheus (≤ 3 min)

> Acesse o Beacon (Prometheus) em: `https://beacon.internal/graph`  
> Ou use a API diretamente com `curl` se disponível.

---

### 2.1 — Uso atual de memória por pod (% do limit)

```promql
# Percentual de uso de memória em relação ao limit configurado
(
  container_memory_working_set_bytes{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }
  /
  container_spec_memory_limit_bytes{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }
) * 100
```

---

### 2.2 — Série histórica: memória nas últimas 4 semanas

```promql
# Máximo de uso de memória por dia nas últimas 4 semanas
max_over_time(
  container_memory_working_set_bytes{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }[1d]
)
```

```promql
# Percentil 95 de uso de memória nas últimas 4 semanas (range: 28d)
quantile_over_time(0.95,
  container_memory_working_set_bytes{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }[28d]
)
```

---

### 2.3 — Taxa de crescimento de memória (detectar leak)

```promql
# Taxa de crescimento de memória por hora (bytes/s) — sinal de memory leak
rate(
  container_memory_working_set_bytes{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }[1h]
)
```

> **Interpretação:** Taxa positiva e crescente ao longo do tempo (ex: +50 MB/h por vários dias) → forte indício de **memory leak**. Taxa alta mas estável → carga pontual.

---

### 2.4 — Número de OOMKills nas últimas 4 semanas

```promql
# Contador de OOMKills por pod
increase(
  kube_pod_container_status_restarts_total{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }[28d]
)
```

---

### 2.5 — Uso de CPU correlacionado (descartar sobrecarga de CPU)

```promql
# Percentual de uso de CPU em relação ao limit
(
  rate(
    container_cpu_usage_seconds_total{
      namespace="production",
      pod=~"chronos-api-.*",
      container="chronos-api"
    }[5m]
  )
  /
  container_spec_cpu_quota{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }
  * container_spec_cpu_period{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }
) * 100
```

---

### 2.6 — HPA: estado atual e histórico de scaling

```bash
# Estado atual do HPA
kubectl get hpa chronos-api -n production

# Histórico detalhado de eventos de scaling
kubectl describe hpa chronos-api -n production
```

```promql
# Número de réplicas ao longo do tempo
kube_horizontalpodautoscaler_status_current_replicas{
  namespace="production",
  horizontalpodautoscaler="chronos-api"
}
```

---

## ETAPA 3 — Correlacionar com Banco de Dados e Filas SQS (≤ 4 min)

> Analisar janela de **2h antes** de cada evento de alerta para identificar padrões.

---

### 3.1 — Queries lentas no PostgreSQL (Ledger)

```promql
# Número de queries lentas no banco Ledger (>1s) — últimas 4 semanas
increase(
  pg_stat_activity_count{
    datname="ledger",
    state="active",
    wait_event_type!="Client"
  }[5m]
)
```

```promql
# Queries em execução por mais de 30 segundos no momento atual
pg_stat_activity_count{
  datname="ledger",
  state="active"
} > 30
```

```promql
# Uso de memória do PostgreSQL (shared_buffers + work_mem aproximado)
pg_settings_shared_buffers_bytes{instance=~"ledger.*"}
```

```promql
# Número de conexões ativas vs. max_connections
(
  pg_stat_activity_count{datname="ledger", state="active"}
  /
  pg_settings_max_connections{instance=~"ledger.*"}
) * 100
```

**Correlação manual:**
1. Anotar o timestamp exato do alerta de memória
2. No Grafana, abrir painel do Ledger e ir para T-2h até T+0h
3. Verificar picos de `pg_stat_activity_count` ou `pg_stat_bgwriter_buffers_alloc`
4. Se houver pico de queries simultâneas antes do pico de memória → **possível causa: consultas pesadas retornando grandes datasets para a aplicação**

---

### 3.2 — Filas SQS (Reactor) — mensagens paradas

```bash
# Listar atributos da fila SQS do Reactor (substituir QUEUE_URL)
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/<ACCOUNT_ID>/chronos-reactor \
  --attribute-names \
    ApproximateNumberOfMessages \
    ApproximateNumberOfMessagesNotVisible \
    ApproximateNumberOfMessagesDelayed \
  --region us-east-1

# Verificar DLQ (Dead Letter Queue) associada
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/<ACCOUNT_ID>/chronos-reactor-dlq \
  --attribute-names \
    ApproximateNumberOfMessages \
  --region us-east-1
```

```promql
# Mensagens visíveis na fila (via CloudWatch Exporter ou custom metric)
aws_sqs_approximate_number_of_messages_visible_average{
  queue_name=~"chronos-reactor.*"
}
```

**Correlação manual:**
1. Verificar se pico de mensagens na fila SQS (`ApproximateNumberOfMessages` alto) ocorre **antes** do pico de memória
2. Se sim → a aplicação pode estar fazendo batch processing de mensagens acumuladas, sobrecarregando a memória
3. Correlacionar com horários recorrentes (ex: processamento em lote noturno ou de final de hora)

---

### 3.3 — Script de correlação rápida

```bash
# Registrar timestamps dos alertas das últimas 4 semanas
# (adaptar conforme sistema de alertas — exemplo com arquivo de log)
grep "High memory usage on Chronos" /var/log/alertmanager/alerts.log \
  | awk '{print $1, $2}' \
  | sort

# Listar horários de restart dos pods nas últimas 4 semanas
kubectl get events -n production \
  --field-selector reason=OOMKilling \
  -o json \
  | jq -r '.items[] | [.lastTimestamp, .involvedObject.name, .message] | @tsv' \
  | sort
```

> **Padrão esperado para diagnóstico:** Se ≥ 3 dos 4 eventos semanais ocorrem no **mesmo intervalo de horário** (ex: entre 22h-23h), há correlação com jobs agendados, processamento de filas ou batch de banco de dados.

---

## ETAPA 4 — Verificar Correlação com Deploys via Argo CD (≤ 1 min)

```bash
# Histórico de deploys do Chronos via Argo CD (últimas 4 semanas)
argocd app history chronos-api \
  --grpc-web \
  | head -30

# Verificar revisão atual deployada
argocd app get chronos-api --grpc-web \
  | grep -E "Revision|Deployed At|Health|Sync"

# Comparar timestamp de deploys com timestamps dos alertas
# (cruzar saída acima com os alertas do Etapa 3.3)
argocd app history chronos-api --grpc-web \
  | awk 'NR>1 {print $1, $2, $3}' \
  | sort
```

**O que observar:**
- Alerta ocorre **dentro de 30 min após um deploy** → possível regressão introduzida no código
- Alerta ocorre independentemente de deploys → problema estrutural (leak, sizing, carga)
- Padrão: mesmo commit em deploys que precedem incidentes → escalar para `@chronos-core`

---

## ETAPA 5 — Identificar o Container Problemático (≤ 1 min)

```bash
# Comparar consumo entre container principal e sidecar istio-proxy/envoy
kubectl top pods -n production -l app=chronos-api --containers
```

```promql
# Uso de memória separado por container (chronos-api vs istio-proxy)
container_memory_working_set_bytes{
  namespace="production",
  pod=~"chronos-api-.*"
}
```

```promql
# Percentual de memória do sidecar istio-proxy
(
  container_memory_working_set_bytes{
    namespace="production",
    pod=~"chronos-api-.*",
    container="istio-proxy"
  }
  /
  container_spec_memory_limit_bytes{
    namespace="production",
    pod=~"chronos-api-.*",
    container="istio-proxy"
  }
) * 100
```

**Diagnóstico:**
| Resultado | Ação |
|-----------|------|
| `chronos-api` > 85% e `istio-proxy` < 50% | Problema no código/config da aplicação |
| `istio-proxy` > 70% | Problema no Envoy — verificar `istio-proxy` config e `concurrency` |
| Ambos altos | Investigar limite total do pod vs. node pressure |

---

## ETAPA 6 — Avaliar Subdimensionamento de Recursos (≤ 1 min)

```bash
# Verificar requests e limits atuais do deployment
kubectl get deployment chronos-api -n production \
  -o jsonpath='{.spec.template.spec.containers[*].resources}' | python3 -m json.tool
```

```promql
# Uso real vs. request configurado (VPA recommendation base)
max_over_time(
  container_memory_working_set_bytes{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }[7d]
)
/
container_spec_memory_limit_bytes{
  namespace="production",
  pod=~"chronos-api-.*",
  container="chronos-api"
}
```

**Critérios de avaliação:**
| Uso real / Limit | Diagnóstico |
|------------------|-------------|
| > 85% consistente | **Subdimensionado** — aumentar limit |
| 60–85% com spikes | **Sizing adequado** — investigar leak ou carga |
| < 60% | Sizing ok — problema é pontual/comportamental |

```bash
# Verificar pressão de memória nos nodes (eviction risk)
kubectl describe nodes \
  | grep -A5 "Conditions:\|Allocatable:\|memory"

kubectl get nodes -o custom-columns=\
"NAME:.metadata.name,\
MEMORY_CAPACITY:.status.capacity.memory,\
MEMORY_ALLOCATABLE:.status.allocatable.memory"
```

---

## ETAPA 7 — Ação Imediata de Mitigação (≤ 3 min)

> **Escolha UMA das opções abaixo com base no diagnóstico das etapas anteriores.**

---

### 🟢 Opção A: Scale Horizontal Imediato (PREFERIDA — sem downtime)

**Quando usar:** Carga legítima alta, sem sinal de leak, HPA não reagiu rápido o suficiente.

```bash
# Aumentar réplicas manualmente para distribuir carga
kubectl scale deployment chronos-api \
  -n production \
  --replicas=10

# Confirmar que os novos pods subiram saudáveis
kubectl rollout status deployment/chronos-api -n production --timeout=120s

# Verificar distribuição após scale
kubectl top pods -n production -l app=chronos-api --sort-by=memory
```

---

### 🟡 Opção B: Ajuste Temporário de Memory Limit

**Quando usar:** Sizing claramente subdimensionado, sem sinal de leak.

```bash
# Patch de emergência no memory limit (exemplo: de 512Mi para 1Gi)
kubectl patch deployment chronos-api -n production \
  --type=json \
  -p='[
    {
      "op": "replace",
      "path": "/spec/template/spec/containers/0/resources/limits/memory",
      "value": "1Gi"
    },
    {
      "op": "replace",
      "path": "/spec/template/spec/containers/0/resources/requests/memory",
      "value": "768Mi"
    }
  ]'

# Acompanhar o rollout
kubectl rollout status deployment/chronos-api -n production --timeout=180s
```

> ⚠️ **ATENÇÃO:** Este patch será sobrescrito no próximo deploy do Argo CD. Documentar no `#oncall-chronos` e abrir ticket para o time de dev atualizar o manifesto no repositório `hvt/chronos-api`.

---

### 🔴 Opção C: Rollback via Argo CD

**Quando usar:** Pico de memória iniciou logo após um deploy específico (correlação identificada na Etapa 4).

```bash
# Listar histórico de revisões
argocd app history chronos-api --grpc-web

# Rollback para a revisão anterior estável (substituir <REVISION_ID>)
argocd app rollback chronos-api <REVISION_ID> --grpc-web

# Acompanhar sync status
argocd app wait chronos-api --health --grpc-web --timeout 120

# Confirmar versão após rollback
argocd app get chronos-api --grpc-web | grep "Revision\|Health"
```

---

### Verificação pós-mitigação (qualquer opção)

```bash
# Aguardar 2 minutos e verificar uso de memória
sleep 120 && kubectl top pods -n production -l app=chronos-api \
  --containers --sort-by=memory

# Confirmar que o alerta cessou no Beacon/Prometheus
# Query: percentual de memória deve estar abaixo de 75%
```

```promql
# Confirmar queda do uso de memória após ação
(
  container_memory_working_set_bytes{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }
  /
  container_spec_memory_limit_bytes{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }
) * 100
```

**✅ Critério de sucesso da mitigação:** Uso de memória abaixo de 75% em todos os pods por ≥ 5 minutos consecutivos.

---

## ETAPA 8 — Critérios de Escalação

### 🔴 Escalar para SEV1 — `@chronos-core` via `#oncall-chronos` IMEDIATAMENTE se:

| Condição | Ação |
|----------|------|
| ≥ 2 pods em `OOMKilled` ou `CrashLoopBackOff` simultaneamente | SEV1 — escalar agora |
| HPA atingiu `max_replicas=12` e memória ainda > 85% | SEV1 — escalar agora |
| Mitigação (Etapas A, B ou C) não reduziu uso em 5 min | SEV1 — escalar agora |
| Rollback tentado e aplicação ainda instável | SEV1 — escalar agora |
| Impacto em usuários finais confirmado (erros 5xx > 1%) | SEV1 — escalar agora |
| Correlação com falha no banco Ledger (conexões esgotadas) | SEV1 — escalar agora |

### 🟡 Escalar para SEV2 — acionar `@chronos-core` com 30 min de prazo se:

| Condição | Ação |
|----------|------|
| Mitigação funcionou mas causa-raiz não identificada | SEV2 — ticket + notificação |
| Patch de limit aplicado (Opção B) sem fix no código | SEV2 — ticket obrigatório |
| Alerta disparou pela 2ª vez na mesma semana | SEV2 — escalação preventiva |
| Correlação com deploy identificada mas rollback não possível | SEV2 — envolver dev |

### Mensagem padrão para `#oncall-chronos`

```
🔴 [SEV1] Chronos API — High Memory Usage
Hora do alerta: <HH:MM>
Pods afetados: <lista de pods>
Restarts: <número>
Ação tomada: <scale / patch / rollback>
Resultado: <resolvido / não resolvido>
Próximos passos: Aguardando @chronos-core
```

---

## ETAPA 9 — Ajustes Definitivos e Critério de Validação Pós-Fix

### 9.1 — Recomendações definitivas por cenário

#### Cenário A: Memory Leak no código
- [ ] Desenvolver com `@chronos-core` para identificar o leak com profiler (heap dump, pprof, JVM heap analysis)
- [ ] Adicionar endpoint de métricas JVM/Go heap no `/metrics`
- [ ] Implementar alertas de taxa de crescimento de memória no Prometheus

```promql
# Alerta recomendado para taxa de crescimento (adicionar ao Beacon)
# Dispara se memória cresceu >100MB em 1h de forma consistente
increase(
  container_memory_working_set_bytes{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }[1h]
) > 104857600  # 100MB em bytes
```

#### Cenário B: Subdimensionamento
- [ ] Abrir PR em `hvt/chronos-api` para atualizar `resources.limits.memory` e `resources.requests.memory`
- [ ] Ativar VPA (Vertical Pod Autoscaler) em modo `Recommendation` para 30 dias antes de aplicar
- [ ] Revisar HPA: considerar adicionar métrica customizada de memória além de CPU

```bash
# Verificar recomendação do VPA (se instalado)
kubectl get vpa chronos-api -n production -o yaml \
  | grep -A20 "recommendation"
```

#### Cenário C: Carga de mensagens SQS
- [ ] Implementar circuit breaker no consumo de mensagens SQS
- [ ] Adicionar `maxConcurrentConsumers` ou rate limiting no Reactor
- [ ] Configurar alarme CloudWatch para `ApproximateNumberOfMessages > threshold`

#### Cenário D: Problema no istio-proxy
- [ ] Ajustar `concurrency` do Envoy via `ProxyConfig`
- [ ] Atualizar versão do Istio se versão antiga com vazamento conhecido
- [ ] Aumentar limits do sidecar via annotation no pod

```yaml
# Annotation para ajustar resources do istio-proxy
annotations:
  sidecar.istio.io/proxyCPU: "200m"
  sidecar.istio.io/proxyMemory: "256Mi"
  sidecar.istio.io/proxyCPULimit: "500m"
  sidecar.istio.io/proxyMemoryLimit: "512Mi"
```

---

### 9.2 — Critério de Validação Pós-Fix

Após implementação do fix definitivo, monitorar por **2 semanas completas** com os seguintes critérios:

| Métrica | Baseline (pré-fix) | Target (pós-fix) |
|---------|-------------------|-----------------|
| Alertas de memória/semana | ~4 | 0 |
| Uso médio de memória | > 85% | < 70% |
| Restarts por semana | ≥ 1 OOMKill | 0 OOMKills |
| P95 de memória (4 semanas) | > 90% do limit | < 75% do limit |

```promql
# Dashboard de validação pós-fix — rodar após 14 dias
# Meta: linha deve ficar consistentemente abaixo de 75%
(
  quantile_over_time(0.95,
    container_memory_working_set_bytes{
      namespace="production",
      pod=~"chronos-api-.*",
      container="chronos-api"
    }[14d]
  )
  /
  container_spec_memory_limit_bytes{
    namespace="production",
    pod=~"chronos-api-.*",
    container="chronos-api"
  }
) * 100
```

---

## 📋 Checklist Rápido do Plantão

```
□ Alerta recebido em #oncall-chronos
□ Etapa 1: Estado dos pods verificado (kubectl get pods + top)
□ Etapa 2: Métricas Prometheus analisadas (PromQL executadas)
□ Etapa 3: Banco de dados e SQS verificados (correlação anotada)
□ Etapa 4: Deploys Argo CD verificados (correlação anotada)
□ Etapa 5: Container problemático identificado (chronos-api ou istio-proxy)
□ Etapa 6: Sizing avaliado (subdimensionado? leak? carga?)
□ Etapa 7: Mitigação executada (A=scale / B=patch / C=rollback)
□ Mitigação validada: memória < 75% por ≥ 5 min
□ Comunicado no #oncall-chronos com diagnóstico
□ Ticket aberto para fix definitivo (se necessário)
□ Escalação SEV1/SEV2 acionada (se critério atingido)
```

---

## 📎 Referências

| Recurso | URL |
|---------|-----|
| Grafana — Chronos Dashboard | `https://grafana.internal/d/chronos-api` |
| Prometheus Beacon | `https://beacon.internal/graph` |
| Repositório Chronos | `https://github.com/hvt/chronos-api` |
| Argo CD — Chronos App | `https://argocd.internal/applications/chronos-api` |
| AWS Console — SQS Reactor | `https://console.aws.amazon.com/sqs/home?region=us-east-1` |
| Slack Canal Plantão | `#oncall-chronos` |
| Time de Escalação | `@chronos-core` |

---

*Runbook gerado por SRE Sênior — Chronos Platform · Revisão obrigatória a cada 90 dias ou após incidente SEV1*
