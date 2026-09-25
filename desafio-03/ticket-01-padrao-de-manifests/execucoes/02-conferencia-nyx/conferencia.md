# Conferência — nyx-barrado.yaml (nyx-prod)

Veredito: **BARRA**

Conferido com `conferir_manifests.py` + Trivy 0.74.0 (código de saída 1: 11 regras
barram, 2 pedem justificativa) e lendo o projeto kube-news
(`C:\estudo\github\desafio03\kube-news`). A versão corrigida está em
`nyx-corrigido.yaml`; o script sai com código 0 sobre ela (0 barra, 1 justificativa:
a 1.5, que depende de um dado que não tenho).

O defeito mais grave não é de regra: **a aplicação não lê `DATABASE_URL`**. Mesmo com
o padrão todo cumprido, o pod subiria tentando falar com `localhost:5432` com a senha
padrão do código. Detalhe em "Fora do padrão, mas encontrado".

## Barra na revisão

| Regra | Achado | Correção |
|---|---|---|
| 1.1 kebab-case | Deployment chamado `NyxAPI` | `nyx-api` em todos os objetos |
| 1.3 Quatro rótulos | Deployment, template do pod e Service só têm `app:` (o Service nem isso) | `app.kubernetes.io/name: nyx-api`, `instance: nyx-prod`, `part-of: nyx`, `managed-by: platform` em todo objeto e no template |
| 1.4 Seletor casa com o pod | Service seleciona `app: nyx-api`, o pod tem `app: nyxapi`: **Service sem endpoint**, zero tráfego | `selector` do Service = `matchLabels` do Deployment (`name` + `instance`), caractere por caractere; `targetPort: http` pelo nome da porta |
| 2.1 requests e limits | nenhum (KSV-0011/15/16/18) | requests `100m`/`128Mi`, limits `500m`/`256Mi`, **iniciais** (ver pendências) |
| 2.2 readiness e liveness | nenhuma probe | readiness `GET /ready`, liveness `GET /health`, porta `http` (8080). Justificativa na seção de leitura do projeto |
| 2.3 replicas >= 2 em prod | `replicas: 1` | `replicas: 2` |
| 2.4 Estratégia em prod | `strategy` ausente (25%/25%) | `RollingUpdate`, `maxUnavailable: 0`, `maxSurge: 1` |
| 3.1 `:latest` (proibido) | `registry.metacortex.io/nyx/api:latest` | tag imutável ou digest publicado pelo Loom. **Não sei qual é**: o corrigido usa `:PENDENTE-TAG-LOOM`, que não existe no registry de propósito (falha em `ImagePullBackOff` em vez de subir imagem errada) |
| 3.2 securityContext | nada (KSV-0001/03/12/14/20) | pod: `runAsNonRoot`, `runAsUser/runAsGroup/fsGroup: 10001`, `seccompProfile: RuntimeDefault`; container: `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: [ALL]`, `emptyDir` em `/tmp` |
| 3.3 Segredo em texto puro (proibido) | `DATABASE_URL` com usuário **e senha do banco** em `env.value`, versionado no Git | credencial via `secretKeyRef` do Secret `nyx-db` (criado fora do Git, comando abaixo). **A senha vazou no histórico do Git: precisa ser rotacionada**, não basta tirar do arquivo |
| 3.4 `automountServiceAccountToken` | não é `false` | `false` na ServiceAccount e no pod: a aplicação não fala com o apiserver (ver abaixo) |

## Exige justificativa no PR (regras recomendadas)

| Regra | Situação no barrado | No corrigido |
|---|---|---|
| 1.5 `metacortex.io/owner` | ausente | **continua ausente**: o time dono não está em nenhum lugar do projeto nem do pedido, e o valor não se inventa. Pendência P1 |
| 3.5 ServiceAccount dedicada | usava a `default` | ServiceAccount `nyx-api`, sem Role/RoleBinding |
| 2.5 PDB em prod | não se aplicava (1 réplica) | PDB `nyx-api` com `minAvailable: 1` |
| 2.6 terminationGracePeriodSeconds | ausente (30s) | 30s explícito; **a aplicação não trata SIGTERM**, ver abaixo e pendência P6 |

## Conferido lendo o projeto

| Item | Resposta | Evidência |
|---|---|---|
| Porta | 8080, casa com `containerPort` do barrado | `src/server.js:81` |
| Comando de start | `node server.js` | `src/package.json:8` |
| Variáveis lidas | `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_SSL_REQUIRE`. **Nenhuma `DATABASE_URL`** | `src/models/post.js:8-13` |
| O que é segredo | `DB_PASSWORD` (e `DB_USERNAME`, que fica no mesmo Secret para a credencial rodar como uma unidade). Host, porta, banco e SSL vão para o ConfigMap | `src/models/post.js:9-10` |
| Liveness (2.2) | `GET /health` responde JSON sem consultar o banco. Devolve 500 depois de `PUT /unhealth`, por causa do `healthMid` que roda antes das rotas: é exatamente o sinal de "processo morto" | `src/system-life.js:22-28`, `src/system-life.js:43-51`, `src/server.js:22-23` |
| Readiness (2.2) | `GET /ready` existe, mas **só olha um temporizador** (`/unreadyfor/:seconds`), não o banco. É a melhor rota que existe: `/` faz `findAll` na tabela inteira e não serve de probe. Pendência P5 para o time expor readiness que verifique o banco | `src/system-life.js:5-20`, `src/server.js:74-78` |
| Cliente de Kubernetes (3.4/3.5) | não: dependências são express, body-parser, ejs, express-prom-bundle, pg, pg-hstore, prom-client, sequelize | `src/package.json:12-21` |
| Escrita em disco (3.2) | nenhuma no código (sem `fs`, upload ou cache em disco; métricas do prom-client ficam em memória). `emptyDir` em `/tmp` por precaução. A imagem não está no repositório (sem Dockerfile): se o CMD for `npm start`, o npm tenta gravar log em `$HOME/.npm` — pendência P3 | busca por `fs.`/`writeFile`/`upload` em `src/*.js` sem resultado |
| SIGTERM (2.6) | **não trata**: não existe `process.on('SIGTERM')`. Com `node` como PID 1, o SIGTERM é ignorado e o pod só morre no SIGKILL, 30s depois, em todo rollout e drain. A correção é no código (fechar o `server` do `app.listen` no SIGTERM), não um grace period maior | `src/server.js:80-81`, busca por `process.on` sem resultado |
| Migração no start | `sequelize.sync({ alter: true })` roda em todo start, sem `await` nem `catch`. Com 2 réplicas (e o `maxSurge`), dois pods alteram o schema ao mesmo tempo. O projeto não tem comando de migração separado, então não dá para levar isso para um Job sem mudar código. Pendência P4 | `src/models/post.js:58-60`, `src/server.js:80` |
| Usuário da imagem | desconhecido: sem Dockerfile no repositório e a imagem publicada não foi inspecionada. `runAsUser: 10001` precisa conseguir ler o `WORKDIR` | pendência P3 |

## Fora do padrão, mas encontrado

1. **`DATABASE_URL` não é lida (defeito que o padrão não pega).** O código monta a
   conexão com `DB_*` (`src/models/post.js:8-13`) e cai em defaults quando elas faltam:
   `localhost`, usuário `kubedevnews` e **senha fixa no código** (`src/models/post.js:10`).
   Com o manifesto barrado, a aplicação nunca falaria com `pg.nyx-prod.svc`. O corrigido
   passa as seis variáveis com o nome que o código lê. Recomendação ao time: tirar os
   defaults de credencial e falhar no start se `DB_PASSWORD` faltar.
2. **Endpoints de caos expostos sem autenticação.** `PUT /unhealth` derruba a
   liveness de vez (o pod reinicia) e `PUT /unreadyfor/:seconds` tira o pod do Service
   (`src/system-life.js:30-41`). Quem alcança o Service consegue tirar as duas réplicas
   de circulação com duas requisições. Em prod devem sair ou ficar atrás de flag/rede
   administrativa. Não se resolve no manifesto; no mínimo, uma NetworkPolicy
   restringindo a origem do tráfego (fora do escopo desta conferência).
3. **Erro de banco derruba o processo.** As rotas `async` (`src/server.js:34-78`) e o
   `sync` sem `catch` (`src/models/post.js:59`) não tratam rejeição; no Node atual,
   promessa rejeitada sem tratamento encerra o processo. Banco fora = CrashLoop, não 500.
4. **`POST /api/post` sem autenticação** grava em massa e loga o corpo inteiro
   (`src/server.js:55-65`).
5. **Cardinalidade de métrica.** `http_requests_total` usa `req.path` como label
   (`src/middleware.js:11`): cada `/post/<id>` cria uma série nova no Prometheus.
6. **Banco `pg.nyx-prod.svc`.** Não sei se é o PostgreSQL que a plataforma provisiona ou
   um banco de réplica única dentro do namespace. Se for o segundo, fere a 2.3 em prod.
   Pendência P7.
7. **Trivy informativo.** O barrado acusava KSV-0004/0021/0030/0104/0106/0118; o
   corrigido resolve todos. Sobra a KSV-01010 (conteúdo sensível em ConfigMap), o falso
   positivo conhecido de `DB_PORT`: nada sensível foi para o ConfigMap.

## Secret a criar (fora do Git)

Depois de rotacionar a senha (P2):

```bash
kubectl -n nyx-prod create secret generic nyx-db \
  --from-literal=DB_USERNAME=nyx \
  --from-literal=DB_PASSWORD='<senha-nova>'
```

## Pendências (dependem de gente)

| # | Pendência | Bloqueia deploy? | Com quem |
|---|---|---|---|
| P1 | Time dono para `metacortex.io/owner` (e `metacortex.io/runbook`, se existir). Até lá, justificar a 1.5 no PR | não | dono do workload nyx |
| P2 | **Rotacionar a senha do banco** que foi commitada no `nyx-barrado.yaml` e criar o Secret `nyx-db` | **sim** | DBA / time nyx + Segurança |
| P3 | Tag imutável ou digest publicado pelo Loom para `registry.metacortex.io/nyx/api`; e, da imagem, `User`, `WorkingDir` e `Cmd` (confirmar que `10001` lê o workdir e que o processo não grava fora de `/tmp`, p. ex. log do npm) | **sim** (imagem) | Loom / time nyx |
| P4 | `sequelize.sync({ alter: true })` no start com 2 réplicas: mudar o código para a migração rodar uma vez (comando separado + Job `nyx-api-migracao-<versao>`) ou aceitar o risco por escrito | não, mas é risco em todo rollout | time da aplicação |
| P5 | Readiness que verifique o banco (hoje `/ready` só olha um temporizador) | não | time da aplicação |
| P6 | Handler de SIGTERM no `server.js` (fechar o servidor e drenar) | não | time da aplicação |
| P7 | Confirmar que `pg.nyx-prod.svc` é o banco provisionado pela plataforma; confirmar se ele exige SSL (o corrigido mantém `DB_SSL_REQUIRE: "false"`, que é o comportamento da URL original) | não | Plataforma |
| P8 | Requests/limits são iniciais: ajustar o limit de memória para 1,5x–2x o consumo observado depois de medir em regime | não | time nyx / SRE |
| P9 | `managed-by: platform` foi a escolha padrão do modelo; trocar para `argocd` ou `helm` se for esse o fluxo de entrega do nyx | não | Plataforma |
| P10 | Endpoints de caos (`/unhealth`, `/unreadyfor`) e `POST /api/post` abertos em prod | não pelo padrão; recomendado antes de prod | time da aplicação + Segurança |
