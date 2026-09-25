# Conferencia - Padrao de Manifests da Metacortex

Trivy: executado · BARRA: 0 · JUSTIFICAR: 0 · OK: 4 · NAO_VERIFICADO: 0 · NAO_SE_APLICA: 14

| Regra | Nivel | Conferido por | Veredito |
|---|---|---|---|
| 1.1 Nome de recurso em kebab-case | obrigatorio | script | OK |
| 1.2 Namespace <cliente>-<ambiente> | obrigatorio | script | OK |
| 1.3 Quatro rotulos app.kubernetes.io/* | obrigatorio | script | OK |
| 1.4 Seletor casa com rotulos do pod | obrigatorio | script | NAO_SE_APLICA |
| 1.5 Anotacao metacortex.io/owner | recomendado | script | NAO_SE_APLICA |
| 1.6 Nome de container igual ao componente | recomendado | script | NAO_SE_APLICA |
| 2.1 requests e limits de CPU e memoria | obrigatorio | trivy | NAO_SE_APLICA |
| 2.2 readinessProbe e livenessProbe | obrigatorio | script | NAO_SE_APLICA |
| 2.3 replicas >= 2 em prod | obrigatorio | script | NAO_SE_APLICA |
| 2.4 RollingUpdate maxUnavailable 0 / maxSurge 1 em prod | obrigatorio | script | NAO_SE_APLICA |
| 2.5 PodDisruptionBudget em prod | recomendado | script | NAO_SE_APLICA |
| 3.1 Tag :latest proibida | proibido | trivy | NAO_SE_APLICA |
| 3.2 securityContext da casa | obrigatorio | trivy | NAO_SE_APLICA |
| 3.3 Segredo em texto puro | proibido | script | OK |
| 3.4 automountServiceAccountToken: false | obrigatorio | script | NAO_SE_APLICA |
| 3.5 ServiceAccount dedicada | recomendado | script | NAO_SE_APLICA |
| 3.6 hostNetwork, hostPID e privileged | proibido | trivy | NAO_SE_APLICA |
| 3.7 Imagem so de registry.metacortex.io | obrigatorio | script | NAO_SE_APLICA |

Codigo de saida: 0
