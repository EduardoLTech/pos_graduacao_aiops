# Conferência — nyx-barrado.yaml (nyx-prod)

Veredito: **BARRA** (11 regras barram; 2 recomendadas sem justificativa)

Conferido com `conferir_manifests.py` + Trivy 0.74.0 (código de saída 1) e leitura do
projeto kube-news em `C:\estudo\github\desafio03\kube-news` (sem Dockerfile no repositório;
a imagem de origem foi inspecionada com `inspecionar_imagem.py`).

A versão corrigida está em `nyx-corrigido.yaml` e sai com **código 0** no mesmo script
(0 barra, 1 JUSTIFICAR: owner). O que ela não resolve está em "Pendências", no fim.

## Barra na revisão

| Regra | Achado | Correção |
|---|---|---|
| 1.1 kebab-case | Deployment `NyxAPI` | renomeado para `nyx-api`, igual ao Service |
| 1.3 Quatro rótulos | Deployment, template do pod e Service só têm `app:` (o Service nem isso) | `app.kubernetes.io/name: nyx-api`, `instance: nyx-prod`, `part-of: nyx`, `managed-by: platform` em todo objeto e no template |
| 1.4 Seletor casa com o pod | Service seleciona `app: nyx-api`, o pod tem `app: nyxapi`: **Service sem endpoint**, nenhum tráfego chega | seletor do Service = `matchLabels` do Deployment (`name` + `instance`), `targetPort: http` nomeado |
| 2.1 requests/limits | nenhum (KSV-0011/15/16/18) | requests 100m/128Mi, limits 500m/256Mi, **valores iniciais sem medição** |
| 2.2 probes | nenhuma | readiness `GET /ready`, liveness `GET /health`, porta `http` (8080) — ver leitura do projeto |
| 2.3 replicas ≥ 2 em prod | `replicas: 1` | `replicas: 2` |
| 2.4 estratégia em prod | ausente (25%/25%) | `RollingUpdate`, `maxUnavailable: 0`, `maxSurge: 1` |
| 3.1 `:latest` | `registry.metacortex.io/nyx/api:latest` (KSV-0013) | `:v1.0.0@sha256:f86b40ce…` — **tag/digest a confirmar com o Loom** |
| 3.2 securityContext | nenhum (KSV-0001/03/12/14/20) | pod: `runAsNonRoot`, `runAsUser/runAsGroup/fsGroup: 10001`, `seccompProfile: RuntimeDefault`; container: `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `drop: [ALL]`; `emptyDir` em `/tmp` |
| 3.3 segredo em texto puro | `DATABASE_URL` com a senha `s3nh4-do-banco` literal no `env.value` | usuário e senha por `secretKeyRef` do Secret `nyx-api-db`; o resto em ConfigMap. **A senha já está no histórico do Git: tem de ser rotacionada** |
| 3.4 automountServiceAccountToken | ausente (token montado) | `false` na ServiceAccount e no pod; a aplicação não fala com o apiserver (ver abaixo) |

## Exige justificativa no PR (regras recomendadas)

| Regra | Achado | Situação no corrigido |
|---|---|---|
| 1.5 `metacortex.io/owner` | ausente | **continua ausente**: o time dono não foi informado e o valor não se inventa. Pendência |
| 3.5 ServiceAccount dedicada | usa a `default` | ServiceAccount `nyx-api`, sem RBAC |
| 2.5 PDB em prod | não se aplicava (1 réplica) | com 2 réplicas, PDB `minAvailable: 1` |

## Conferido lendo o projeto

| Item | Resposta | Evidência |
|---|---|---|
| Porta | 8080 | `src/server.js:81` (`app.listen(8080)`); imagem `ExposedPorts: 8080/tcp` |
| Variáveis que o código lê | `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_SSL_REQUIRE`. **`DATABASE_URL` não é lida** | `src/models/post.js:8-13` |
| O que é credencial | `DB_PASSWORD` (e `DB_USERNAME`, mantido junto no Secret) | `src/models/post.js:9-10` |
| 2.2 endpoints de saúde | `/health` responde JSON fixo sem consultar o banco → liveness. `/ready` só compara um timer e **também não consulta o banco** → é a única rota de readiness que existe, mas não segura tráfego com o banco fora | `src/system-life.js:11-28` |
| 2.2 ressalva da liveness | o middleware `healthMid` roda antes das rotas: depois de `PUT /unhealth`, **todas** as rotas (inclusive `/health`) dão 500 e a liveness reinicia o pod. É o comportamento desenhado para demo | `src/server.js:22`, `src/system-life.js:30-51` |
| 3.4 fala com o apiserver? | Não: nenhuma dependência de cliente Kubernetes | `src/package.json:12-21`; `package-lock.json` sem `kubernetes` |
| 3.2 escrita em disco | Nenhuma escrita encontrada (sem `fs.*`, upload ou cache em disco; métricas do prom-client em memória). `emptyDir` em `/tmp` mantido como rede de segurança; na imagem `/tmp` é o do Alpine, sem conteúdo a esconder | busca por `fs.|writeFile` em `src/*.js` sem resultado |
| Usuário da imagem | imagem roda como `node` (UID 1000), `WorkingDir /app`; o manifesto força 10001. O `COPY src/ ./` não usa `--chown`, então os arquivos são de root e só precisam ser legíveis — esperado, **mas não verificado por camada** (smoke test) | `inspecionar_imagem.py fabricioveronez/kube-news:v1.0.0` |
| 2.6 SIGTERM / PID 1 | `docker-entrypoint.sh` do node faz `exec` → **`node server.js` é PID 1 e não há handler de SIGTERM** no código: o sinal é ignorado e o pod só morre no SIGKILL, ao fim dos 30s. Mantido o padrão de 30s; a correção é no código, não no grace period | `Cmd ["node","server.js"]`; busca por `process.on|SIGTERM` em `src/` sem resultado |
| Migração no start | `seque.sync({ alter: true })` roda a cada boot, **sem `await`** (promessa solta). Com 2 réplicas e `maxSurge: 1`, até 3 pods fazem `ALTER TABLE` concorrente | `src/server.js:80`, `src/models/post.js:58-60` |
| Imagem de origem | `nyx/api` foi tratada como espelho de `fabricioveronez/kube-news` (o projeto indicado). `v1.0.0` tem amd64+arm64; `v1` (mais recente, 2026-09-21) **só tem arm64** | `inspecionar_imagem.py … --tags` |

## Fora do padrão, mas encontrado

1. **`DATABASE_URL` não é lida pela aplicação.** Mesmo com o padrão cumprido, o manifesto
   original subiria apontando para `localhost:5432` com usuário/senha padrão do código:
   a aplicação nunca falaria com `pg.nyx-prod.svc`. O corrigido passa `DB_HOST`, `DB_PORT`,
   `DB_DATABASE` (ConfigMap) e `DB_USERNAME`/`DB_PASSWORD` (Secret), extraídos da URL
   original (`nyx@pg.nyx-prod.svc:5432/nyx`).
2. **Senha padrão no código**: `DB_PASSWORD || "Pg#123"` (`src/models/post.js:10`, também no
   README). Sem o Secret, a aplicação sobe com uma senha conhecida em vez de falhar.
3. **Rotas de caos sem autenticação em prod**: `PUT /unhealth` derruba o pod (todas as
   rotas passam a 500) e `PUT /unreadyfor/:seconds` tira o pod do Service
   (`src/system-life.js:30-41`). Qualquer um que alcance o Service consegue.
4. **Escrita sem autenticação**: `POST /post` e `POST /api/post` (inserção em massa, sem
   validação de tamanho em `/api/post`) (`src/server.js:34-65`).
5. **`sync({ alter: true })` sem `await`**: falha de conexão com o banco vira
   `UnhandledPromiseRejection`; no Node 22 isso derruba o processo (reinício em loop se o
   banco estiver fora), e a readiness não reflete o banco.
6. **Trivy KSV-01010** no corrigido marca `DB_PORT` no ConfigMap como sensível: falso
   positivo conhecido, não responde pela 3.3.
7. `/metrics` fica exposto pelo mesmo Service da aplicação (`express-prom-bundle`,
   `src/server.js:9-21`). Não fere o padrão; informativo.

## Pendências (não decidíveis sem gente)

| # | Pendência | Quem | Efeito no corrigido |
|---|---|---|---|
| 1 | **Rotacionar a senha `s3nh4-do-banco`**: está em texto puro no Git. Tirar do YAML não a desfaz | Nyx / DBA | — |
| 2 | Criar o Secret fora do repositório: `kubectl -n nyx-prod create secret generic nyx-api-db --from-literal=username=nyx --from-literal=password='<nova-senha>'` | quem opera nyx-prod | sem ele o pod fica em `CreateContainerConfigError` |
| 3 | Time dono para `metacortex.io/owner` (e `metacortex.io/runbook`, se existir) | Nyx | 1.5 segue JUSTIFICAR até lá |
| 4 | Tag/digest publicados pelo Loom em `registry.metacortex.io/nyx/api`. Usei `v1.0.0@sha256:f86b40ce…` (digest da origem); se o Loom não preservou o digest, o pull falha e é preciso trocar | Plataforma / Loom | pull pode falhar |
| 5 | `managed-by: platform` (valor do modelo da casa); trocar para `argocd` se o deploy for pelo Argo | Plataforma | nenhum para a regra |
| 6 | Requests/limits são iniciais; ajustar o limit de memória para 1,5x–2x o consumo observado em regime | Nyx, após medição | — |
| 7 | `DB_SSL_REQUIRE: "false"` repete a URL original (sem `sslmode`); confirmar se `pg.nyx-prod` exige TLS | DBA | conexão recusada se exigir |
| 8 | Confirmar que `pg.nyx-prod.svc` existe e é gerido fora deste manifesto (a URL original indica isso; o banco não foi gerado aqui) | Nyx | — |
| 9 | **Código:** tirar `sync({ alter: true })` do boot (flag de ambiente ou script de migração) para permitir um Job `nyx-api-migracao-<versao>`. Hoje o manifesto não consegue desligar a migração, e 2 réplicas migram em paralelo | time da aplicação | risco de `ALTER` concorrente no rollout |
| 10 | **Código:** `/ready` consultar o banco (`sequelize.authenticate()`), para a readiness segurar tráfego com o banco fora | time da aplicação | readiness hoje só reflete o timer |
| 11 | **Código:** tratar SIGTERM (`server.close()` + fechar o pool) ou rodar com init (`tini`/`dumb-init`) | time da aplicação | cada pod leva 30s para morrer no rollout |
| 12 | **Código/Segurança:** desligar ou proteger `/unhealth` e `/unreadyfor` em prod; autenticar `POST /api/post`; remover a senha padrão `Pg#123` | time da aplicação + Segurança | exposição em prod |
| 13 | Smoke test com `runAsUser: 10001` e `readOnlyRootFilesystem` (leitura de `/app` e `node_modules` por UID ≠ dono não foi verificada por camada) | quem sobe em stg | — |
