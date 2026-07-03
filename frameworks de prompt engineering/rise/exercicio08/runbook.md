# Runbook Operacional: Mitigação de Instabilidade Chronos API (v2.48.0)
**Código do Incidente**: INC-20260424-01  
**Serviço**: `chronos-api`  
**Severidade**: SEV1  

Este runbook descreve os passos práticos para diagnóstico, execução do rollback emergencial e validação pós-mitigação do serviço `chronos-api` no cluster Kubernetes.

---

## Fases do Runbook

1. [Diagnóstico Rápido e Validação do Estado](#1-diagnóstico-rápido-e-validação-do-estado)
2. [Execução do Rollback Emergencial](#2-execução-do-rollback-emergencial)
3. [Monitoramento e Validação Pós-Rollback](#3-monitoramento-e-validação-pós-rollback)
4. [Procedimento de Escalonamento e Rollback da Fila](#4-procedimento-de-escalonamento-e-rollback-da-fila)

---

## 1. Diagnóstico Rápido e Validação do Estado

Execute estes comandos para confirmar se o sintoma é de exaustão de pool e saturação de conexões no RDS do Ledger.

### 1.1. Verificar o Estado Geral dos Pods e HPA
Valide se os pods estão saudáveis, se há reinicializações constantes (OOMKilled ou CrashLoopBackOff) e se o HPA atingiu o teto.
```bash
# Verificar status dos pods e reinicializações no namespace de produção (ex: prod-chronos)
kubectl get pods -n prod -l app=chronos-api

# Verificar utilização atual e limites do HPA
kubectl get hpa -n prod chronos-api-hpa
```

### 1.2. Verificar Logs em Tempo Real buscando Erros de Conexão e Timeout
Filtre logs recentes buscando padrões de exaustão do pool de conexões do Ledger:
```bash
# Buscar erros de esgotamento de pool nos logs de um pod específico
kubectl logs -n prod deployment/chronos-api --tail=1000 | grep -E "connection pool exhausted|query timeout|context deadline exceeded"

# Visualizar logs em tempo real (streaming) buscando circuit breaker aberto
kubectl logs -n prod deployment/chronos-api -f --tail=200 | grep -i "circuit-breaker"
```

### 1.3. Verificar a Versão Ativa (v2.48.0)
Confirme a imagem de container atualmente em execução para garantir que o deploy causador é o v2.48.0:
```bash
kubectl get deployment -n prod chronos-api -o jsonpath='{.spec.template.spec.containers[*].image}'
```

---

## 2. Execução do Rollback Emergencial

Como estamos usando o **Argo CD** como ferramenta de GitOps, o rollback feito diretamente via `kubectl` pode ser desfeito pelo controlador do Argo CD caso o Auto-Sync esteja ativo. Portanto, devemos desabilitar o Auto-Sync temporariamente ou usar o fluxo do Argo CD.

### Opção A: Via CLI do Argo CD (Recomendado)
Se você tiver acesso ao CLI do Argo CD configurado, execute o rollback e suspenda o auto-sync:

```bash
# 1. Desabilitar o auto-sync temporariamente para evitar reconciliação imediata
argocd app set chronos-api --sync-policy none

# 2. Executar rollback para a revisão/versão v2.47.0 anterior estável
argocd app rollback chronos-api --history-id $(argocd app history chronos-api | grep "v2.47.0" | awk '{print $1}' | head -n 1)
```

### Opção B: Via Kubectl (Bypass Emergencial)
Caso não tenha o CLI do Argo CD instalado, desative o auto-sync editando o recurso `Application` do Argo CD e force o rollback do deployment do Kubernetes.

```bash
# 1. Desabilitar o auto-sync patcheando o recurso Application do Argo CD
kubectl patch application chronos-api -n argocd --type='json' -p='[{"op": "replace", "path": "/spec/syncPolicy", "value": null}]'

# 2. Executar o rollback manual da imagem do container da chronos-api para v2.47.0
kubectl set image deployment/chronos-api -n prod chronos-api=your-registry/chronos-api:v2.47.0 --record

# 3. Forçar o rollout imediato (reinício rápido dos pods)
kubectl rollout restart deployment/chronos-api -n prod

# 4. Acompanhar o progresso do rollout
kubectl rollout status deployment/chronos-api -n prod
```

---

## 3. Monitoramento e Validação Pós-Rollback

Após o rollback iniciar, execute a validação para confirmar a restauração dos serviços.

### 3.1. Validar Versão da Imagem Atualizada
Verifique se todos os pods ativos estão rodando a imagem correta:
```bash
kubectl get pods -n prod -l app=chronos-api -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].image}{"\n"}{end}'
```

### 3.2. Acompanhar Conexões no Banco de Dados
Com a v2.47.0 em execução, as conexões ativas devem começar a cair. Acompanhe a contagem de conexões estabelecidas nos pods (ou execute query administrativa no Postgres se tiver acesso):
```bash
# Verificar se os logs mostram mensagens de sucesso e conexões livres
kubectl logs -n prod deployment/chronos-api --tail=100 | grep -i "connected"
```

### 3.3. Monitorar Latência dos Pods
Valide a latência de p99 nos pods restaurados através do log de requisições:
```bash
# Monitorar logs de requisições buscando tempo de resposta HTTP
kubectl logs -n prod deployment/chronos-api -f --tail=100 | grep -E "POST /v2|GET /"
```

---

## 4. Procedimento de Escalonamento e Rollback da Fila

O Reactor acumulou **50.127 mensagens** na fila `chronos-transactions` com lag de **18 minutos**. Agora que a API está estável, os consumers/workers precisam processar essa fila o mais rápido possível sem sobrecarregar o banco de dados.

### 4.1. Escalar Workers do Reactor (Se aplicável)
Se os workers do Reactor forem um deployment separado, podemos escalá-los horizontalmente de forma temporária para acelerar o consumo das mensagens acumuladas:
```bash
# Verificar réplicas atuais dos workers do Reactor
kubectl get deployment -n prod reactor-worker

# Escalar temporariamente os workers para aumentar o throughput de consumo
kubectl scale deployment/reactor-worker -n prod --replicas=8
```
> [!WARNING]
> Monitore constantemente o consumo de CPU e conexões do banco de dados ao escalar os workers. Se o banco começar a se aproximar de 240 conexões novamente, reduza as réplicas imediatamente.

### 4.2. Monitorar o Lag da Fila
Acompanhe a diminuição do lag através de comandos ou queries no sistema de filas (ex: RabbitMQ, Kafka ou Redis, dependendo da tecnologia do Reactor).
Se for baseado em Prometheus, valide o lag via query (a ser executada no painel do Grafana/Prometheus):
```promql
# Query recomendada para monitorar lag de consumo no Grafana
sum(kafka_consumergroup_lag{topic="chronos-transactions"}) by (consumergroup)
# ou
rabbitmq_queue_messages{queue="chronos-transactions"}
```

### 4.3. Restaurar a Escala Padrão do Reactor
Assim que o consumer lag zerar (lag < 1 minuto e mensagens acumuladas próximas a 0), retorne o deployment de workers ao tamanho padrão para economizar recursos:
```bash
# Retornar o número de réplicas ao padrão estável
kubectl scale deployment/reactor-worker -n prod --replicas=4
```

---

## 5. Rollback de Contingência (Fallback Plan)
Caso o rollback da aplicação chronos-api falhe ou a latência não diminua imediatamente após o deploy da v2.47.0:

1. **Cortar Tráfego de Batch**:
   Se por qualquer motivo o tráfego do endpoint `/v2/transactions/batch` ainda estiver ativo e enviando requisições que causam timeout, aplique uma regra de bloqueio no Ingress ou API Gateway para retornar erro HTTP 503 imediatamente:
   ```bash
   # Exemplo: Editar o Ingress ou regras de rate-limit para bloquear requisições em /v2/transactions/batch
   kubectl edit ingress chronos-api-ingress -n prod
   ```
2. **Reiniciar Conexões Presas (RDS Failover)**:
   Se conexões "órfãs" continuarem presas no RDS e bloqueando novas conexões da v2.47.0, um failover do RDS pode ser iniciado via console AWS ou CLI da AWS para fechar todas as sessões e reiniciar o banco no nó secundário (tempo estimado de interrupção: 30 a 60 segundos):
   ```bash
   # Comando AWS CLI para forçar reboot do RDS com failover (Multi-AZ requerido)
   aws rds reboot-db-instance --db-instance-identifier ledger-rds-production --force-failover
   ```
