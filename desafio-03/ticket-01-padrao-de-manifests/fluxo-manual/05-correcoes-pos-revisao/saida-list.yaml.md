# Conferencia - Padrao de Manifests da Metacortex

Trivy: executado · BARRA: 4 · JUSTIFICAR: 2 · OK: 5 · NAO_VERIFICADO: 4 · NAO_SE_APLICA: 3

| Regra | Nivel | Conferido por | Veredito |
|---|---|---|---|
| 1.1 Nome de recurso em kebab-case | obrigatorio | script | OK |
| 1.2 Namespace <cliente>-<ambiente> | obrigatorio | script | OK |
| 1.3 Quatro rotulos app.kubernetes.io/* | obrigatorio | script | OK |
| 1.4 Seletor casa com rotulos do pod | obrigatorio | script | OK |
| 1.5 Anotacao metacortex.io/owner | recomendado | script | JUSTIFICAR |
| 1.6 Nome de container igual ao componente | recomendado | script | OK |
| 2.1 requests e limits de CPU e memoria | obrigatorio | trivy | NAO_VERIFICADO |
| 2.2 readinessProbe e livenessProbe | obrigatorio | script | BARRA |
| 2.3 replicas >= 2 em prod | obrigatorio | script | NAO_SE_APLICA |
| 2.4 RollingUpdate maxUnavailable 0 / maxSurge 1 em prod | obrigatorio | script | NAO_SE_APLICA |
| 2.5 PodDisruptionBudget em prod | recomendado | script | NAO_SE_APLICA |
| 3.1 Tag :latest proibida | proibido | trivy | NAO_VERIFICADO |
| 3.2 securityContext da casa | obrigatorio | trivy | NAO_VERIFICADO |
| 3.3 Segredo em texto puro | proibido | script | BARRA |
| 3.4 automountServiceAccountToken: false | obrigatorio | script | BARRA |
| 3.5 ServiceAccount dedicada | recomendado | script | JUSTIFICAR |
| 3.6 hostNetwork, hostPID e privileged | proibido | trivy | NAO_VERIFICADO |
| 3.7 Imagem so de registry.metacortex.io | obrigatorio | script | BARRA |

## Achados

### 1.5 Anotacao metacortex.io/owner - JUSTIFICAR
- Deployment/orion-web (list.yaml (List)): sem anotacao metacortex.io/owner

### 2.1 requests e limits de CPU e memoria - NAO_VERIFICADO
- nao verificado: trivy nao expande kind: List (Deployment/orion-web); separe os objetos em documentos YAML

### 2.2 readinessProbe e livenessProbe - BARRA
- Deployment/orion-web (list.yaml (List)): container 'web' sem readinessProbe e livenessProbe

### 3.1 Tag :latest proibida - NAO_VERIFICADO
- nao verificado: trivy nao expande kind: List (Deployment/orion-web); separe os objetos em documentos YAML

### 3.2 securityContext da casa - NAO_VERIFICADO
- nao verificado: trivy nao expande kind: List (Deployment/orion-web); separe os objetos em documentos YAML

### 3.3 Segredo em texto puro - BARRA
- Deployment/orion-web (list.yaml (List)): container 'web' env DB_PASSWORD com valor literal; use valueFrom.secretKeyRef

### 3.4 automountServiceAccountToken: false - BARRA
- Deployment/orion-web (list.yaml (List)): automountServiceAccountToken nao e false

### 3.5 ServiceAccount dedicada - JUSTIFICAR
- Deployment/orion-web (list.yaml (List)): usa a ServiceAccount default do namespace

### 3.6 hostNetwork, hostPID e privileged - NAO_VERIFICADO
- nao verificado: trivy nao expande kind: List (Deployment/orion-web); separe os objetos em documentos YAML

### 3.7 Imagem so de registry.metacortex.io - BARRA
- Deployment/orion-web (list.yaml (List)): container 'web' usa 'nginx:latest' fora de registry.metacortex.io/

## Conferencia que exige ler o projeto

- [ ] 2.2 Deployment/orion-web (list.yaml (List)) 'web': descobrir no projeto quais endpoints usar nas probes (ou se nao existem).
- [ ] 3.4 Deployment/orion-web (list.yaml (List)): confirmar no projeto se a aplicacao fala com o apiserver; se nao fala, o token nao monta.
- [ ] 2.6 Deployment/orion-web (list.yaml (List)): conferir no projeto se a aplicacao trata SIGTERM e se 30s bastam para drenar.

Codigo de saida: 1
