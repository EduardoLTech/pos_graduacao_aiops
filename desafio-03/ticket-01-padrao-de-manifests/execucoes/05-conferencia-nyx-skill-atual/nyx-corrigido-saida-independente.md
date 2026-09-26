# Conferencia - Padrao de Manifests da Metacortex

Trivy: executado · BARRA: 0 · JUSTIFICAR: 1 · OK: 17 · NAO_VERIFICADO: 0 · NAO_SE_APLICA: 0

| Regra | Nivel | Conferido por | Veredito |
|---|---|---|---|
| 1.1 Nome de recurso em kebab-case | obrigatorio | script | OK |
| 1.2 Namespace <cliente>-<ambiente> | obrigatorio | script | OK |
| 1.3 Quatro rotulos app.kubernetes.io/* | obrigatorio | script | OK |
| 1.4 Seletor casa com rotulos do pod | obrigatorio | script | OK |
| 1.5 Anotacao metacortex.io/owner | recomendado | script | JUSTIFICAR |
| 1.6 Nome de container igual ao componente | recomendado | script | OK |
| 2.1 requests e limits de CPU e memoria | obrigatorio | trivy | OK |
| 2.2 readinessProbe e livenessProbe | obrigatorio | script | OK |
| 2.3 replicas >= 2 em prod | obrigatorio | script | OK |
| 2.4 RollingUpdate maxUnavailable 0 / maxSurge 1 em prod | obrigatorio | script | OK |
| 2.5 PodDisruptionBudget em prod | recomendado | script | OK |
| 3.1 Tag :latest proibida | proibido | trivy | OK |
| 3.2 securityContext da casa | obrigatorio | trivy | OK |
| 3.3 Segredo em texto puro | proibido | script | OK |
| 3.4 automountServiceAccountToken: false | obrigatorio | script | OK |
| 3.5 ServiceAccount dedicada | recomendado | script | OK |
| 3.6 hostNetwork, hostPID e privileged | proibido | trivy | OK |
| 3.7 Imagem so de registry.metacortex.io | obrigatorio | script | OK |

## Achados

### 1.5 Anotacao metacortex.io/owner - JUSTIFICAR
- Deployment/nyx-api (nyx-corrigido.yaml): sem anotacao metacortex.io/owner

## Conferencia que exige ler o projeto

- [ ] 2.2 Deployment/nyx-api (nyx-corrigido.yaml) 'api': confirmar no codigo que readiness=/ready e liveness=/health existem, na porta certa, e que a liveness nao depende do banco.
- [ ] 2.1 Deployment/nyx-api (nyx-corrigido.yaml) 'api': limits de memoria devem ficar entre 1,5x e 2x o consumo observado; o YAML nao diz o consumo.
- [ ] 3.2 Deployment/nyx-api (nyx-corrigido.yaml): readOnlyRootFilesystem ligado; conferir no projeto todo caminho em que a aplicacao escreve e se ha emptyDir montado nele.
- [ ] 2.6 Deployment/nyx-api (nyx-corrigido.yaml): conferir no projeto se a aplicacao trata SIGTERM e se 30s bastam para drenar.

## Trivy fora do padrao da casa (informativo, nao barra por esta pagina)

- KSV-01010 (MEDIUM): ConfigMap with sensitive content
  - nyx-corrigido.yaml: ConfigMap 'nyx-api' in 'nyx-prod' namespace stores sensitive contents in key(s) or value(s) '{"DB_PORT"}'

Codigo de saida: 0
