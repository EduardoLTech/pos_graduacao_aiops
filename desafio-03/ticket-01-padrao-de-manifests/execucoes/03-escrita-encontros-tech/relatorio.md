# encontros-tech · helio-stg: manifests e decisões

- **Projeto lido:** `C:\estudo\github\desafio03\encontros-tech` (Flask 3 + gunicorn 21 + SQLAlchemy 2 + PostgreSQL via psycopg2; origem `github.com/KubeDev/encontros-tech`; não há Dockerfile, Procfile nem docker-compose no repositório)
- **Namespace:** `helio-stg` (staging = `stg`, regra 1.2)
- **Dono (`metacortex.io/owner`):** não informado, **não preenchido** (pendência 2)
- **Imagens:** não informadas. Os manifests usam a tag `pendente-loom`, que **não existe** e precisa ser trocada antes do apply (pendência 1)
- **Conferência:** `conferir_manifests.py` com Trivy 0.74.0 → **código 0**. Resultado: 14 OK, 0 barradas, 1 a justificar (1.5), 3 que não se aplicam (2.3, 2.4 e 2.5 valem só para prod)

## Arquivos

| Arquivo | Objetos |
|---|---|
| `manifests/encontros-tech.yaml` | ServiceAccount, ConfigMap, Deployment (1 réplica), Service ClusterIP :80 → 8000 |
| `manifests/encontros-tech-postgres.yaml` | ServiceAccount, Service headless :5432, StatefulSet PostgreSQL (1 réplica, PVC de 1Gi) |

## Decisões que não eram óbvias

**Porta e comando.** A porta padrão é 8000 (`src/core/settings.py:16`). `HOST` e `PORT` só são usados no `app.run` do `__main__` (`src/main.py:63`), que não roda sob gunicorn. Como o repositório não diz como a imagem sobe, o Deployment define o `command` explicitamente: `gunicorn --bind 0.0.0.0:8000 --workers 1 main:app`. O gunicorn está em `src/requirements.txt:2`, e o comentário em `src/core/settings.py:26` indica que ele é o servidor previsto. Os imports são planos (`from core.database ...`, `src/main.py:6`), então o comando supõe que o `WORKDIR` da imagem é o conteúdo de `src/` (pendência 1).

**Criação de schema no start, sem Job de migração.** `src/main.py:21` roda `Base.metadata.create_all` no import do módulo. Isso acontece em todo worker e em todo pod, e o projeto não tem Alembic nem outra ferramenta de migração. Não dá para tirar isso do start sem mudar o código, porque qualquer processo que importe `main` recria as tabelas. Em staging decidi assim:
- **1 réplica e 1 worker:** o `create_all` roda uma vez por pod.
- **Sem Job de migração:** um Job não impediria o `create_all` do Deployment, então só duplicaria o trabalho.
- **Rolling update padrão:** o pod novo sobe junto com o antigo, mas a tabela já existe, e o `create_all` só emite DDL para tabela ausente.

A exceção é o primeiro deploy com mais de uma réplica, em que dois `CREATE TABLE` podem correr ao mesmo tempo. Para prod, isso vira pendência de código (pendência 6).

**Probes.** A aplicação não expõe `/health` nem `/ready`. Usei rotas que já existem:
- **liveness → `/metrics`.** O `PrometheusMetrics(app)` (`src/main.py:35`) registra essa rota, que é o caminho padrão do prometheus_flask_exporter. Ela não consulta o banco.
- **readiness → `/api/events/?limit=1`.** O blueprint é registrado em `src/main.py:56` e a rota está em `src/routers/api_router.py:43-67`. Ela lê uma linha de `events` e devolve 500 (`api_router.py:65-67`) se o banco estiver fora ou se a tabela não existir. A barra final é proposital: sem ela, o Flask responde 308, e o kubelet contaria o redirect como sucesso.
- Descartei `/` como readiness porque ela lista todos os eventos. Além disso, no caminho de erro ela renderiza `error.html`, que não existe (ver "Fora do padrão").

**O que é segredo.** Estas são as variáveis que o código lê (`src/core/settings.py:10-27`) e o que o manifesto faz com cada uma:

| Variável | Onde entra | Motivo |
|---|---|---|
| `DATABASE_URL` | `secretKeyRef` (`helio-encontros-tech-db`, chave `database-url`) | a URL carrega usuário e senha |
| `DEBUG`, `LOG_LEVEL`, `LOG_FORMAT`, `SERVICE_NAME` | ConfigMap | não são sensíveis |
| `APP_TITLE` | não passada | é lida em `settings.py:13` e não é usada em lugar nenhum |
| `HOST`, `PORT` | não passadas | só servem ao `app.run` |
| `SERVICE_VERSION` | não passada | depende da versão publicada (pendência 1). Sem ela, a métrica `app_info` sai com `1.0.0` |
| `PROMETHEUS_MULTIPROC_DIR` | não passada | ver "Escrita em disco" |

O `PROMETHEUS_PORT` de `.env.exemple:41` não é lido pelo código e ficou de fora. O manifesto não passa nenhuma variável que o código ignore.

**Escrita em disco com `readOnlyRootFilesystem`.**
- **App:** um único `emptyDir` em `/tmp`. Ele cobre o heartbeat dos workers do gunicorn (`worker_tmp_dir` padrão) e o `os.makedirs` de `src/main.py:32`, que roda mesmo sem a variável e cria `/tmp/prometheus_multiproc` (padrão de `settings.py:27`).
- **Métricas:** deixei `PROMETHEUS_MULTIPROC_DIR` fora do ambiente de propósito. Com 1 worker, o modo de processo único é o correto. O modo multiprocess exigiria o hook `child_exit` → `mark_process_dead`, que o projeto não tem, e um `emptyDir` sobrevive a reinícios do container, então os arquivos `.db` de execuções antigas se acumulariam.
- **Postgres:**
  - PVC em `/var/lib/postgresql/data`, com `PGDATA` num subdiretório (a raiz do volume pode ter `lost+found`).
  - `emptyDir` em `/var/run/postgresql` (socket e lock).
  - `emptyDir` em `/tmp`, usado pelo nss_wrapper do entrypoint oficial quando o UID 10001 não tem entrada em `/etc/passwd`.
  - `fsGroup: 10001` deixa o PVC gravável.

**Banco gerado junto.** O projeto exige PostgreSQL (`src/core/settings.py:10`, `src/requirements.txt:6`), e ninguém informou um banco existente. Por isso gerei um StatefulSet no mesmo padrão:
- rótulos, securityContext e ServiceAccount próprios;
- senha e usuário por Secret;
- `POSTGRES_DB=encontros_tech`, o nome do padrão do código;
- readiness com `pg_isready` via TCP e liveness com `pg_isready` pelo socket local.

Em staging a réplica única é aceita. Em prod ela feriria a 2.3.

**Sem acesso ao apiserver (3.4/3.5).** O `src/requirements.txt` não tem cliente de Kubernetes. Cada workload tem sua própria ServiceAccount, sem RBAC e com `automountServiceAccountToken: false`.

**SIGTERM (2.6).** Com o `command` explícito, o gunicorn é o PID 1 e trata SIGTERM com `graceful_timeout` de 30s. O código não registra handler próprio, e também não precisa. O PostgreSQL trata SIGTERM como smart shutdown. Mantive os 30s padrão nos dois.

**Recursos.** Os valores são iniciais, **sem medição**:
- **app:** requests `100m/128Mi`, limits `500m/256Mi`;
- **postgres:** requests `100m/256Mi`, limits `500m/512Mi`;
- **PVC:** `1Gi`, na StorageClass padrão do cluster.

**Informativo do Trivy.** Sobrou só o KSV-01010 (conteúdo sensível em ConfigMap). O ConfigMap tem apenas `DEBUG`, `LOG_LEVEL`, `LOG_FORMAT` e `SERVICE_NAME`, e nenhum desses valores é sensível. Por isso tratei como falso positivo, do mesmo tipo do caso conhecido de `DB_PORT`, e ele não responde pela 3.3. Não consegui ver a chave exata que disparou o KSV-01010: rodar o Trivy isolado não foi autorizado nesta sessão. Os informativos de seccomp e GID não aparecem.

## Pendências (dependem de gente)

1. **Imagens (bloqueia o apply).** O repositório não tem Dockerfile e ninguém informou o que o Loom publicou.
   - Troque `registry.metacortex.io/helio/encontros-tech:pendente-loom` pela tag@digest real.
   - Confirme na imagem: `WORKDIR` com o conteúdo de `src/` (`main.py`, `core/`, `models/`...), `gunicorn` no PATH e arquivos legíveis pelo UID 10001.
   - Troque `registry.metacortex.io/helio/postgres:pendente-loom` pelo postgres espelhado. A versão não aparece em nenhum lugar do projeto: o `.env.exemple:13` cita um docker-compose que não está no repositório.
   - Com a versão definida, preencha `SERVICE_VERSION` no ConfigMap.
2. **Time dono (regra 1.5, recomendada).** Falta `metacortex.io/owner` no Deployment e no StatefulSet. O script marca isso como JUSTIFICAR. Preencha quando o time do helio for definido e adicione `metacortex.io/runbook` se houver runbook.
3. **Criar o Secret `helio-encontros-tech-db`** em `helio-stg`, fora do Git. A `database-url` precisa usar o mesmo usuário e a mesma senha que o StatefulSet recebe:
   ```sh
   SENHA="$(openssl rand -base64 24 | tr -d '/+=')"
   kubectl -n helio-stg create secret generic helio-encontros-tech-db \
     --from-literal=user=encontros_tech \
     --from-literal=password="$SENHA" \
     --from-literal=database-url="postgresql://encontros_tech:${SENHA}@encontros-tech-postgres:5432/encontros_tech"
   kubectl -n helio-stg label secret helio-encontros-tech-db \
     app.kubernetes.io/name=encontros-tech app.kubernetes.io/instance=helio-stg \
     app.kubernetes.io/part-of=helio app.kubernetes.io/managed-by=platform
   ```
   Sem esse Secret, os dois pods ficam em `CreateContainerConfigError`.
4. **Banco próprio ou da plataforma.** Gerei o PostgreSQL no namespace porque ninguém informou um banco existente. Se o helio tiver banco provisionado pela plataforma em staging, remova `encontros-tech-postgres.yaml` e aponte a `database-url` para ele. StorageClass, tamanho do volume e backup também precisam ser confirmados.
5. **Limits de memória.** Os valores são iniciais. Depois de observar o consumo em regime, ajuste o limit para 1,5x a 2x esse consumo (regra 2.1).
6. **Antes de prod (código).** `src/main.py:21` cria o schema no import. Com 2 ou mais réplicas (regra 2.3) ou mais de 1 worker, há corrida de DDL, e o projeto não tem como evoluir o schema. O time da aplicação precisa adotar Alembic e tirar o `create_all` do import. Aí a migração vai para um Job `encontros-tech-migracao-<versao>`. Em prod, o banco também precisa de replicação ou de exceção aprovada por Segurança.
7. **Endpoints de saúde de verdade.** Pedir ao time da aplicação `/health` (sem banco) e `/ready` (com banco). Hoje cada probe gera log INFO: o `after_request` loga toda requisição (`src/main.py:46-52`), e a readiness ainda gera um `log_business_event` a cada 10s (`src/routers/api_router.py:57-61`).
8. **Exposição externa.** Não gerei Ingress/Gateway, porque o pedido não trouxe host, TLS nem o padrão de entrada do helio. Hoje o Service é só ClusterIP.

## Fora do padrão, mas encontrado no código (para o time da aplicação)

- **`src/main.py:25`: `SECRET_KEY = 'your-secret-key-here'` fixo no código, com `# TODO`.** O `flash()` (`page_router.py:106,110,147...`) usa sessão assinada com essa chave, então qualquer pessoa consegue forjar o cookie de sessão. A chave deve ser lida do ambiente e vir de Secret, que o manifesto passa a injetar quando o código ler a variável.
- **`src/core/settings.py:10`: credencial padrão `encontros_tech:encontros_tech` na URL de fallback.** O manifesto sempre define `DATABASE_URL`, mas esse valor não deveria estar no código.
- **`src/routers/page_router.py:37`: `render_template("error.html")` aponta para um template que não existe.** Não há `error.html` em `src/templates/`. Quando o banco falha, `/` lança `TemplateNotFound` em vez de mostrar a página de erro.
- **`src/services/event_service.py:38`: o `edit_token` vai para o log em INFO.** O token dá direito de editar o evento sem autenticação (`/api/events/by-token/<token>`, PUT). Quem lê os logs pode editar qualquer evento. Os outros pontos do código já truncam o token em 8 caracteres.
- **`src/routers/page_router.py:102`: o token de edição volta na query string do redirect** (`/?created=...&token=...`). Ele fica em histórico, logs de proxy e `Referer`.
- **`src/services/event_service.py:27-28,126-127`: `technologies` não é persistido.** A API devolve o campo na criação, mas ele se perde na leitura.
- **`src/requirements.txt:14`: `pytest` entra nas dependências de runtime.** Separar em um arquivo de dependências de desenvolvimento, para não ir para a imagem.
