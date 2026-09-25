# Conferencia - Padrao de Manifests da Metacortex

Trivy: executado · BARRA: 11 · JUSTIFICAR: 2 · OK: 4 · NAO_VERIFICADO: 0 · NAO_SE_APLICA: 1

| Regra | Nivel | Conferido por | Veredito |
|---|---|---|---|
| 1.1 Nome de recurso em kebab-case | obrigatorio | script | BARRA |
| 1.2 Namespace <cliente>-<ambiente> | obrigatorio | script | OK |
| 1.3 Quatro rotulos app.kubernetes.io/* | obrigatorio | script | BARRA |
| 1.4 Seletor casa com rotulos do pod | obrigatorio | script | BARRA |
| 1.5 Anotacao metacortex.io/owner | recomendado | script | JUSTIFICAR |
| 1.6 Nome de container igual ao componente | recomendado | script | OK |
| 2.1 requests e limits de CPU e memoria | obrigatorio | trivy | BARRA |
| 2.2 readinessProbe e livenessProbe | obrigatorio | script | BARRA |
| 2.3 replicas >= 2 em prod | obrigatorio | script | BARRA |
| 2.4 RollingUpdate maxUnavailable 0 / maxSurge 1 em prod | obrigatorio | script | BARRA |
| 2.5 PodDisruptionBudget em prod | recomendado | script | NAO_SE_APLICA |
| 3.1 Tag :latest proibida | proibido | trivy | BARRA |
| 3.2 securityContext da casa | obrigatorio | trivy | BARRA |
| 3.3 Segredo em texto puro | proibido | script | BARRA |
| 3.4 automountServiceAccountToken: false | obrigatorio | script | BARRA |
| 3.5 ServiceAccount dedicada | recomendado | script | JUSTIFICAR |
| 3.6 hostNetwork, hostPID e privileged | proibido | trivy | OK |
| 3.7 Imagem so de registry.metacortex.io | obrigatorio | script | OK |

## Achados

### 1.1 Nome de recurso em kebab-case - BARRA
- Deployment/NyxAPI (nyx-barrado.yaml): nome 'NyxAPI' fora de kebab-case

### 1.3 Quatro rotulos app.kubernetes.io/* - BARRA
- Deployment/NyxAPI (nyx-barrado.yaml): faltam app.kubernetes.io/name, app.kubernetes.io/instance, app.kubernetes.io/part-of, app.kubernetes.io/managed-by
- Deployment/NyxAPI (nyx-barrado.yaml) template do pod: faltam app.kubernetes.io/name, app.kubernetes.io/instance, app.kubernetes.io/part-of, app.kubernetes.io/managed-by
- Service/nyx-api (nyx-barrado.yaml): faltam app.kubernetes.io/name, app.kubernetes.io/instance, app.kubernetes.io/part-of, app.kubernetes.io/managed-by

### 1.4 Seletor casa com rotulos do pod - BARRA
- Service/nyx-api (nyx-barrado.yaml): seletor {'app': 'nyx-api'} nao casa com nenhum pod (Deployment/NyxAPI tem {'app': 'nyxapi'}) -> Service sem endpoint

### 1.5 Anotacao metacortex.io/owner - JUSTIFICAR
- Deployment/NyxAPI (nyx-barrado.yaml): sem anotacao metacortex.io/owner

### 2.1 requests e limits de CPU e memoria - BARRA
- nyx-barrado.yaml: [KSV-0011] Container 'api' of Deployment 'NyxAPI' should set 'resources.limits.cpu'
- nyx-barrado.yaml: [KSV-0015] Container 'api' of Deployment 'NyxAPI' should set 'resources.requests.cpu'
- nyx-barrado.yaml: [KSV-0016] Container 'api' of Deployment 'NyxAPI' should set 'resources.requests.memory'
- nyx-barrado.yaml: [KSV-0018] Container 'api' of Deployment 'NyxAPI' should set 'resources.limits.memory'

### 2.2 readinessProbe e livenessProbe - BARRA
- Deployment/NyxAPI (nyx-barrado.yaml): container 'api' sem readinessProbe e livenessProbe

### 2.3 replicas >= 2 em prod - BARRA
- Deployment/NyxAPI (nyx-barrado.yaml): replicas=1 em prod

### 2.4 RollingUpdate maxUnavailable 0 / maxSurge 1 em prod - BARRA
- Deployment/NyxAPI (nyx-barrado.yaml): strategy=ausente (padrao 25%/25%); esperado RollingUpdate maxUnavailable 0, maxSurge 1

### 3.1 Tag :latest proibida - BARRA
- nyx-barrado.yaml: [KSV-0013] Container 'api' of Deployment 'NyxAPI' should specify an image tag

### 3.2 securityContext da casa - BARRA
- nyx-barrado.yaml: [KSV-0001] Container 'api' of Deployment 'NyxAPI' should set 'securityContext.allowPrivilegeEscalation' to false
- nyx-barrado.yaml: [KSV-0003] Container 'api' of Deployment 'NyxAPI' should add 'ALL' to 'securityContext.capabilities.drop'
- nyx-barrado.yaml: [KSV-0012] Container 'api' of Deployment 'NyxAPI' should set 'securityContext.runAsNonRoot' to true
- nyx-barrado.yaml: [KSV-0014] Container 'api' of Deployment 'NyxAPI' should set 'securityContext.readOnlyRootFilesystem' to true
- nyx-barrado.yaml: [KSV-0020] Container 'api' of Deployment 'NyxAPI' should set 'securityContext.runAsUser' > 10000

### 3.3 Segredo em texto puro - BARRA
- Deployment/NyxAPI (nyx-barrado.yaml): container 'api' env DATABASE_URL com valor literal; use valueFrom.secretKeyRef

### 3.4 automountServiceAccountToken: false - BARRA
- Deployment/NyxAPI (nyx-barrado.yaml): automountServiceAccountToken nao e false

### 3.5 ServiceAccount dedicada - JUSTIFICAR
- Deployment/NyxAPI (nyx-barrado.yaml): usa a ServiceAccount default do namespace

## Conferencia que exige ler o projeto

- [ ] 2.2 Deployment/NyxAPI (nyx-barrado.yaml) 'api': descobrir no projeto quais endpoints usar nas probes (ou se nao existem).
- [ ] 3.4 Deployment/NyxAPI (nyx-barrado.yaml): confirmar no projeto se a aplicacao fala com o apiserver; se nao fala, o token nao monta.
- [ ] 2.6 Deployment/NyxAPI (nyx-barrado.yaml): conferir no projeto se a aplicacao trata SIGTERM e se 30s bastam para drenar.

## Trivy fora do padrao da casa (informativo, nao barra por esta pagina)

- KSV-0004 (LOW): Default capabilities: some containers do not drop any
- KSV-0021 (LOW): Runs with GID <= 10000
- KSV-0030 (LOW): Runtime/Default Seccomp profile not set
- KSV-0104 (MEDIUM): Seccomp policies disabled
- KSV-0106 (LOW): Container capabilities must only include NET_BIND_SERVICE
- KSV-0118 (HIGH): Default security context configured

Codigo de saida: 1
