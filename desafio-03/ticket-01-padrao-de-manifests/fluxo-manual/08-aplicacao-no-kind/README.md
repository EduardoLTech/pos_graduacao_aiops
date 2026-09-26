# Manifests da execução 04 aplicados num cluster kind (2026-09-25)

Até aqui, o script e o Trivy conferiam o YAML, mas nada tinha subido num cluster.
Esta pasta aplica os manifests que a skill gerou na execução 04 (fake-shop em
`orion-stg`: aplicação, Job de migração e PostgreSQL), sem editar nenhum deles.

Ambiente: kind v0.27.0, Kubernetes v1.32.2, nó único, StorageClass `standard` do kind.

## Desvios de laboratório

Estão todos em `fake-shop-stg/kustomization.yaml`. Nenhum mexe no manifesto:
- **Imagem:** `registry.metacortex.io` só existe dentro do parque. O kustomize troca o nome
  pela imagem de origem, com a mesma tag e o mesmo digest
  (`fabricioveronez/fake-shop:v1@sha256:07db4334…`, `postgres:17@sha256:d74eeac9…`).
- **Namespace:** criado junto. No parque, quem cria é a plataforma.
- **Secret `orion-fake-shop-db`:** gerado com senha de laboratório. O relatório da
  execução 04 manda criar à mão.

```sh
cd fake-shop-stg
kubectl kustomize --load-restrictor LoadRestrictionsNone . > renderizado.yaml
kubectl apply -f renderizado.yaml
```

## O que o cluster mostrou

| Verificação | Resultado |
|---|---|
| Os objetos são aceitos pelo apiserver | 11 criados, nenhum recusado |
| PostgreSQL com UID 10001, `readOnlyRootFilesystem` e PVC | subiu; PVC `Bound` (1Gi) |
| Job de migração | 2 pods com erro enquanto o banco não resolvia no DNS (`Name or service not known`) e sucesso no 3º. O `backoffLimit: 6` foi dimensionado para isso, e segurou |
| Readiness em `/shop` | falhou com 500 (`relation "products" does not exist`) até a migração terminar; depois o pod ficou pronto. Segura tráfego até o schema existir, como foi desenhado |
| Aplicação com UID 10001, raiz só leitura e dois `emptyDir` | subiu sem erro de escrita; `/shop` 200 e `/metrics` respondendo, pelo Service |
| Liveness em `/metrics` com o banco fora (StatefulSet em 0 por 162 s) | o pod saiu de pronto e **não reiniciou**. A liveness não depende do banco |
| Volta do banco | pronto de novo sem reinício; `/shop` 200 com o schema preservado no PVC |

Um ponto a observar: na subida, a liveness falhou uma vez por timeout (3 s) enquanto o
`/shop` da readiness esperava o banco. O gunicorn roda com um único worker síncrono, então
uma requisição presa ao banco atrasa o `/metrics`. Foi uma falha só, abaixo do
`failureThreshold` de 3. Com o banco fora do ar, a conexão falha rápido e o problema não
volta. **O caso não testado** é o banco que aceita a conexão e não responde: aí o worker
pode ficar preso tempo suficiente para a liveness reiniciar o pod.

`estado-final.txt` e `eventos.txt` são a saída de `kubectl get` do namespace, gravada
antes de apagá-lo. O `orion-stg` foi removido em seguida para não se misturar com o
ambiente do Chamado 2 do Ticket 02, que usa o mesmo namespace.

## O que não foi aplicado

- **Execução 03 (encontros-tech):** a imagem é `:pendente-loom`, e não há imagem publicada
  do projeto.
- **Execução 05 (nyx corrigido):** depende de um banco em `nyx-prod`, que o manifesto
  referencia e não cria.
