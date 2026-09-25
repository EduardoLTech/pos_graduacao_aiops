# Conferencia - Padrao de Manifests da Metacortex

Trivy: pulado (--sem-trivy) · BARRA: 6 · JUSTIFICAR: 3 · OK: 2 · NAO_VERIFICADO: 4 · NAO_SE_APLICA: 3

| Regra | Nivel | Conferido por | Veredito |
|---|---|---|---|
| 1.1 Nome de recurso em kebab-case | obrigatorio | script | BARRA |
| 1.2 Namespace <cliente>-<ambiente> | obrigatorio | script | BARRA |
| 1.3 Quatro rotulos app.kubernetes.io/* | obrigatorio | script | BARRA |
| 1.4 Seletor casa com rotulos do pod | obrigatorio | script | OK |
| 1.5 Anotacao metacortex.io/owner | recomendado | script | JUSTIFICAR |
| 1.6 Nome de container igual ao componente | recomendado | script | JUSTIFICAR |
| 2.1 requests e limits de CPU e memoria | obrigatorio | trivy | NAO_VERIFICADO |
| 2.2 readinessProbe e livenessProbe | obrigatorio | script | OK |
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

### 1.1 Nome de recurso em kebab-case - BARRA
- Secret/orion_db (casos.yaml): nome 'orion_db' fora de kebab-case

### 1.2 Namespace <cliente>-<ambiente> - BARRA
- Secret/orion_db (casos.yaml): sem metadata.namespace (cairia no namespace do contexto)
- Deployment/orion-worker (casos.yaml): namespace 'orion-qa' nao segue <cliente>-<dev|stg|prod>

### 1.3 Quatro rotulos app.kubernetes.io/* - BARRA
- Secret/orion_db (casos.yaml): faltam app.kubernetes.io/name, app.kubernetes.io/instance, app.kubernetes.io/part-of, app.kubernetes.io/managed-by
- Deployment/orion-worker (casos.yaml): faltam app.kubernetes.io/name, app.kubernetes.io/instance, app.kubernetes.io/part-of, app.kubernetes.io/managed-by
- Deployment/orion-worker (casos.yaml) template do pod: faltam app.kubernetes.io/name, app.kubernetes.io/instance, app.kubernetes.io/part-of, app.kubernetes.io/managed-by

### 1.5 Anotacao metacortex.io/owner - JUSTIFICAR
- Deployment/orion-worker (casos.yaml): sem anotacao metacortex.io/owner

### 1.6 Nome de container igual ao componente - JUSTIFICAR
- Deployment/orion-worker (casos.yaml): container 'app' com nome generico

### 2.1 requests e limits de CPU e memoria - NAO_VERIFICADO
- nao verificado: pulado com --sem-trivy

### 3.1 Tag :latest proibida - NAO_VERIFICADO
- nao verificado: pulado com --sem-trivy

### 3.2 securityContext da casa - NAO_VERIFICADO
- nao verificado: pulado com --sem-trivy

### 3.3 Segredo em texto puro - BARRA
- Secret/orion_db (casos.yaml): Secret com valor no manifesto; o valor nao se versiona, so a referencia
- Deployment/orion-worker (casos.yaml): container 'app' env API_TOKEN com valor literal; use valueFrom.secretKeyRef
- casos.yaml:1: credencial embutida em URL dentro de comentario

### 3.4 automountServiceAccountToken: false - BARRA
- Deployment/orion-worker (casos.yaml): automountServiceAccountToken nao e false

### 3.5 ServiceAccount dedicada - JUSTIFICAR
- Deployment/orion-worker (casos.yaml): usa a ServiceAccount default do namespace

### 3.6 hostNetwork, hostPID e privileged - NAO_VERIFICADO
- nao verificado: pulado com --sem-trivy

### 3.7 Imagem so de registry.metacortex.io - BARRA
- Deployment/orion-worker (casos.yaml): container 'app' usa 'nginx' fora de registry.metacortex.io/

## Conferencia que exige ler o projeto

- [ ] 2.2 Deployment/orion-worker (casos.yaml) 'app': readiness e liveness no mesmo endpoint /health. Confirmar no projeto que ele nao consulta o banco.
- [ ] 2.2 Deployment/orion-worker (casos.yaml) 'app': confirmar no codigo que readiness=/health e liveness=/health existem, na porta certa, e que a liveness nao depende do banco.
- [ ] 3.4 Deployment/orion-worker (casos.yaml): confirmar no projeto se a aplicacao fala com o apiserver; se nao fala, o token nao monta.
- [ ] 2.6 Deployment/orion-worker (casos.yaml): conferir no projeto se a aplicacao trata SIGTERM e se 30s bastam para drenar.

Codigo de saida: 1
