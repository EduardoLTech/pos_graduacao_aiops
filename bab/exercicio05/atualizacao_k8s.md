# Guia de Atualização e Operação do Manifest Kubernetes - `chronos-api`

Este diretório contém os manifests Kubernetes refatorados da API `chronos-api` para o ambiente de `production`, alinhados com as melhores práticas de segurança corporativa, resiliência, alta disponibilidade e controle de recursos.

---

## 📋 Resumo das Atualizações

O arquivo de deployment original apresentava diversas vulnerabilidades de segurança e riscos operacionais. Abaixo estão as melhorias implementadas:

### 1. Alta Disponibilidade (HA) e Resiliência
*   **Múltiplas Réplicas (`replicas: 3`):** Distribuição de carga e resiliência a falhas de hardware ou reinicialização de nós.
*   **Anti-Afinidade de Pod (`podAntiAffinity`):** Configurada para preferir agendar réplicas do `chronos-api` em nós físicos diferentes (`topologyKey: kubernetes.io/hostname`), prevenindo indisponibilidade se um nó cair.
*   **Pod Disruption Budget (`pdb.yaml`):** Garante que pelo menos 2 das 3 réplicas estejam sempre ativas durante manutenções voluntárias no cluster (ex: drenagem de nós para atualização do Kubernetes).

### 2. Segurança e Isolamento (SecurityContext)
*   **Execução como Não-Root (`runAsNonRoot: true`):** O container é impedido de executar processos como usuário root (UID 0). Foi definido o UID `10001` (`runAsUser: 10001`).
*   **Sistema de Arquivos Read-Only (`readOnlyRootFilesystem: true`):** Protege a integridade da imagem do container, impedindo modificações e escritas arbitrárias. Para suportar arquivos temporários comuns da API, criamos um volume temporário em memória (`emptyDir`) montado em `/tmp`.
*   **Remoção de Privilégios (`allowPrivilegeEscalation: false`):** Impede que processos filhos ganhem mais privilégios do que o processo pai.
*   **Drop de Capabilities (`capabilities.drop: [ALL]`):** Remove todas as capacidades do kernel Linux não estritamente necessárias.
*   **Perfil Seccomp (`seccompProfile`):** Configurado como `RuntimeDefault` para restringir chamadas de sistema (syscalls) do kernel.

### 3. Gerenciamento Seguro de Secrets
*   **Isolamento de Credenciais (`secret.yaml`):** As variáveis de ambiente confidenciais (`DB_PASSWORD` e `JWT_SECRET`) foram removidas do manifest do Deployment.
*   **Referência Dinâmica (`secretKeyRef`):** O deployment agora referencia chaves específicas criadas no recurso `Secret` do Kubernetes, permitindo a rotação de segredos e impedindo o vazamento no repositório Git.

### 4. Controle de Recursos (Resource Requests & Limits)
*   **Resource Requests (`cpu: 100m`, `memory: 128Mi`):** Garante a reserva de recursos mínimos para o agendamento correto no nó (evita sobrecarga por disputa de recursos).
*   **Resource Limits (`cpu: 500m`, `memory: 256Mi`):** Impede que vazamentos de memória ou loops infinitos de CPU da aplicação afetem os demais serviços que compartilham o mesmo nó do cluster.

### 5. Monitoramento de Ciclo de Vida (Probes)
*   **Readiness Probe (`/healthz`):** O Kubernetes só direciona tráfego do `Service` para o Pod quando ele passa neste teste, garantindo que usuários não recebam erros HTTP 502/503 durante o início da aplicação.
*   **Liveness Probe (`/healthz`):** Detecta se a aplicação travou (deadlock) ou parou de responder, reiniciando o container de forma automática em caso de falha persistente.

### 6. Rede e Acesso (NetworkPolicy e ServiceAccount)
*   **ServiceAccount Dedicado (`serviceaccount.yaml`):** Isola a identidade da aplicação dentro do cluster e desativa a montagem automática do token da API do Kubernetes (`automountServiceAccountToken: false`), bloqueando acessos indevidos à API do cluster.
*   **NetworkPolicy (`networkpolicy.yaml`):** Bloqueia tráfego externo direto. Permite conexões de entrada na porta `8080` apenas vindas do Ingress Controller e limita a comunicação de saída (Egress) ao DNS do cluster (`kube-dns`) e ao banco de dados corporativo.

---

## 🚀 Estratégia de Deploy Sem Downtime (Zero Downtime)

Para garantir que a atualização ocorra sem nenhuma perda de requisições, o deployment utiliza a estratégia `RollingUpdate` configurada da seguinte forma:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 25%         # Permite criar novos pods antes de destruir os antigos
    maxUnavailable: 0     # Nenhum pod antigo é removido até que o novo esteja saudável
```

### Funcionamento do Fluxo:
1. O Kubernetes inicia um novo Pod com a nova versão da imagem (`chronos-api:1.5.0`).
2. O Pod antigo continua atendendo todas as requisições normais.
3. O Kubernetes aguarda o período do `Readiness Probe` do novo Pod. Somente após a API retornar sucesso no endpoint `/healthz`, o Pod é considerado saudável (Ready).
4. O novo Pod passa a receber tráfego do `Service`.
5. O Kubernetes inicia a terminação de um Pod antigo enviando um sinal `SIGTERM` (permitindo término gracioso das conexões existentes).
6. Esse processo se repete de forma gradativa até que todas as réplicas estejam na nova versão.

---

## 🛠️ Passo a Passo para Aplicação do Deploy

Execute os comandos a partir do diretório onde os manifests estão salvos:

### 1. Criar o Secret com credenciais reais:
Antes de aplicar, altere os placeholders em `secret.yaml` ou crie diretamente via linha de comando:
```bash
# Alternativa por comando (recomendado para segurança em pipelines CI/CD)
kubectl create secret generic chronos-api-secrets \
  --from-literal=DB_PASSWORD="SuaSenhaForteAqui" \
  --from-literal=JWT_SECRET="SeuJwtSecretAqui" \
  -n production --dry-run=client -o yaml | kubectl apply -f -
```

### 2. Aplicar os recursos de suporte:
```bash
kubectl apply -f serviceaccount.yaml
kubectl apply -f service.yaml
kubectl apply -f pdb.yaml
kubectl apply -f networkpolicy.yaml
```

### 3. Aplicar o Deployment (Atualização da Aplicação):
```bash
kubectl apply -f deployment.yaml
```

### 4. Monitorar a atualização em tempo real:
```bash
kubectl rollout status deployment/chronos-api -n production
```
*Se o comando retornar `deployment "chronos-api" successfully rolled out`, a atualização foi concluída com sucesso e sem downtime.*

---

## ↩️ Plano de Retorno (Rollback)

Se durante o monitoramento do deploy (ou via telemetria e logs após o deploy) for identificada alguma anomalia, execute imediatamente os seguintes passos:

### 1. Comando de Rollback Imediato
Execute o comando abaixo para reverter o deployment para a revisão estável anterior:
```bash
kubectl rollout undo deployment/chronos-api -n production
```
*Nota: Este comando também segue o princípio do RollingUpdate (MaxUnavailable=0), garantindo zero indisponibilidade durante o processo de reversão.*

### 2. Validar o status da reversão
```bash
kubectl rollout status deployment/chronos-api -n production
```

### 3. Visualizar histórico de versões (Revisões)
Para verificar qual versão está ativa e o histórico de modificações:
```bash
kubectl rollout history deployment/chronos-api -n production
```

### 4. Investigação pós-incidente (Troubleshooting)
Se precisar examinar o motivo de falha da nova versão, busque os logs do pod que falhou ou os eventos do Kubernetes:
```bash
# Ver eventos de erro recentes
kubectl get events -n production --sort-by='.metadata.creationTimestamp'

# Ver logs do container anterior (se houver reinicialização)
kubectl logs deployment/chronos-api -c api -n production --previous

# Descrever os pods para ver erros de Probes ou ImagePullBackOff
kubectl describe pods -l app=chronos-api -n production
```
