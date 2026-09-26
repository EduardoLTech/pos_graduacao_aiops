# fake-shop · orion-stg: manifests e decisões

- **Projeto lido:** `C:\estudo\github\desafio03\fake-shop` (Flask 3 + gunicorn 21 + Flask-Migrate/Alembic + PostgreSQL via psycopg 3; não há Dockerfile, compose nem CI no repositório)
- **Namespace:** `orion-stg` (staging = `stg`, regra 1.2)
- **Dono (`metacortex.io/owner`):** não informado, **não preenchido** (pendência 2)
- **Imagem da aplicação:** `registry.metacortex.io/orion/fake-shop:v1@sha256:07db4334f5f2bb330f0f342a81ad203bb21b770b8d7a27c90edb2261fea34e2f`. Veio de evidência, não de pedido: a tag e o digest são os mesmos da origem `fabricioveronez/fake-shop:v1` no Docker Hub (a tag mais recente, de 2026-08-12) e da imagem que o Loom publicou para `orion-prod` na execução 01. Falta alguém confirmar que é essa a versão que vai para staging (pendência 1)
- **Conferência:** `conferir_manifests.py` com Trivy 0.74.0 → **código 0**. Resultado: 14 OK, 0 barradas, 1 a justificar (1.5), 3 que não se aplicam (2.3, 2.4 e 2.5 valem só para prod)

## Arquivos

| Arquivo | Objetos |
|---|---|
| `manifests/fake-shop.yaml` | ServiceAccount, ConfigMap, Deployment (1 réplica), Service ClusterIP :80 → 5000 |
| `manifests/fake-shop-migracao.yaml` | ServiceAccount, Job `fake-shop-migracao-v1` |
| `manifests/fake-shop-postgres.yaml` | ServiceAccount, Service headless :5432, StatefulSet PostgreSQL 17 (1 réplica, PVC de 1Gi) |

## Decisões que não eram óbvias

**Configuração da imagem verificada.** Li a configuração da imagem de origem com `inspecionar_imagem.py`, sem Docker:
- `User: app`, criado com `useradd --uid 10001`. É o mesmo UID do padrão, então `runAsUser: 10001` lê e é dono de `/app`, que tem `chown -R app:app`.
- `WorkingDir: /app`, com `COPY src/ ./`. `index.py`, `migrations/` e `entrypoint.sh` estão ali.
- `PATH` começa por `/opt/venv/bin`, então `gunicorn` e `python` resolvem sem caminho absoluto.
- A imagem já define `FLASK_APP=index.py` e `PROMETHEUS_MULTIPROC_DIR=/tmp/metrics`, e cria `/tmp/metrics` no build.
- `Cmd: ["./entrypoint.sh"]`, porta exposta 5000.

**Porta e comando.** O processo escuta em 5000 (`src/entrypoint.sh:3`). O Deployment sobrescreve o `command` com `gunicorn --bind 0.0.0.0:5000 index:app`, sem o `flask db upgrade` de `src/entrypoint.sh:2`. Há dois motivos:
- a migração vai para um Job (próximo item);
- o `entrypoint.sh` deixa o `bash` como PID 1 e chama o gunicorn sem `exec`, então o SIGTERM não chegaria à aplicação.

**Migração em Job, mesmo com 1 réplica.** Em staging a regra 2.3 aceita 1 réplica, mas mantive a migração fora do pod:
- no rolling update, o pod novo migra enquanto o antigo ainda serve, e o schema muda debaixo dele;
- a migração inicial (`src/migrations/versions/a11283937150_modelo_inicial.py:70-144`) também insere os 9 produtos do catálogo, então duas execuções em paralelo podem falhar no meio;
- staging fica com a mesma forma que prod (execução 01), e a promoção não muda o desenho.

O Job `fake-shop-migracao-v1` usa a mesma imagem e o mesmo securityContext. O `upgrade` do Alembic não faz nada se o banco já estiver na última versão, então reaplicar não causa dano. `backoffLimit: 6` cobre o primeiro apply, em que o Job pode começar antes de o PostgreSQL aceitar conexão: o backoff exponencial passa de 5 minutos. O pod do Job tem `app.kubernetes.io/name: fake-shop-migracao` para não cair no seletor do Service.

**Probes.** A aplicação não expõe `/health` nem `/ready`. Usei rotas que já existem:
- **liveness → `/metrics`** (`src/index.py:18-19`). A rota é servida pelo prometheus_flask_exporter e não consulta o banco.
- **readiness → `/shop`** (`src/index.py:129-132`). A rota faz `Product.query.all()` e devolve 500 se o banco estiver fora ou se a tabela `products` ainda não existir. O pod só entra no Service depois que o Job migrou, e isso não depende da ordem do apply.
- **PostgreSQL:** readiness com `pg_isready` via TCP (o caminho que a aplicação usa) e liveness com `pg_isready` pelo socket local, que só testa se o servidor responde.

**O que é segredo.** O código lê `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` e `DB_PORT` (`src/index.py:22-26`).

| Variável | Onde entra | Motivo |
|---|---|---|
| `DB_USER`, `DB_PASSWORD` | `secretKeyRef` (`orion-fake-shop-db`, chaves `user` e `password`) | credencial. O StatefulSet lê as mesmas chaves para `POSTGRES_USER` e `POSTGRES_PASSWORD` |
| `DB_HOST` | ConfigMap (`fake-shop-postgres`) | é o Service do banco gerado junto, não é sensível |
| `DB_NAME`, `DB_PORT` | ConfigMap (`ecommerce`, `5432`) | padrões do código (`src/index.py:25-26`) |
| `PROMETHEUS_MULTIPROC_DIR` | ConfigMap (`/tmp/metrics`) | a imagem já define o mesmo valor. Repeti para amarrar o valor ao `emptyDir` do manifesto: se a imagem mudar, o mount continua valendo |
| `FLASK_APP` | só no Job (`index.py`) | o `flask db upgrade` precisa dela, o gunicorn não. A imagem também define |

O manifesto não passa nenhuma variável que o código não lê.

**Escrita em disco com `readOnlyRootFilesystem`.**
- **App e Job:** `emptyDir` em `/tmp` (heartbeat dos workers do gunicorn, `worker_tmp_dir` padrão) e outro `emptyDir` em `/tmp/metrics`, onde o `GunicornPrometheusMetrics` (`src/index.py:18`) grava as métricas de cada worker. Os dois são separados porque montar só `/tmp` esconderia o `/tmp/metrics` que a imagem cria. O Job precisa dos mesmos volumes: o `flask db upgrade` importa `index.py`, que inicializa o exporter.
- O Python não consegue gravar `__pycache__` em `/app`. Ele ignora o erro e segue.
- **PostgreSQL:**
  - PVC em `/var/lib/postgresql/data`, com `PGDATA` num subdiretório (a raiz do volume pode ter `lost+found`);
  - `emptyDir` em `/var/run/postgresql` (socket e lock);
  - `emptyDir` em `/tmp`, usado pelo nss_wrapper do entrypoint oficial, porque o UID 10001 não tem entrada no `/etc/passwd` da imagem (o usuário `postgres` é o 999);
  - `fsGroup: 10001` deixa o PVC gravável.

**Banco gerado junto.** O projeto exige PostgreSQL (`src/index.py:28`, `src/requirements.txt:18`), e ninguém informou um banco existente. Por isso gerei um StatefulSet no mesmo padrão: rótulos, securityContext, ServiceAccount própria, credencial por Secret e `POSTGRES_DB=ecommerce`. A versão não aparece no projeto. Escolhi o PostgreSQL 17, suportado pelo psycopg 3.2 e pelo SQLAlchemy 2.0, fixado pelo digest da tag `17` no Docker Hub (17.11 hoje). Em staging a réplica única é aceita. Em prod ela feriria a 2.3.

**Sem acesso ao apiserver (3.4/3.5).** `src/requirements.txt` não tem cliente de Kubernetes. Cada workload tem ServiceAccount própria, sem RBAC e com `automountServiceAccountToken: false`.

**SIGTERM (2.6).**
- **App:** com o `command` sobrescrito, o gunicorn é o PID 1 e trata SIGTERM com desligamento gracioso (`graceful_timeout` de 30s). O código não registra handler próprio e não precisa. Mantive os 30s padrão.
- **PostgreSQL:** a imagem declara `STOPSIGNAL SIGINT` (fast shutdown), mas o kubelet ignora esse campo e manda SIGTERM, que no PostgreSQL é smart shutdown: ele espera as conexões fecharem. O gunicorn mantém conexões abertas pelo pool do SQLAlchemy, então o pod levaria os 30s inteiros e morreria no SIGKILL. Por isso há um `preStop` com `pg_ctl stop -m fast -t 25`, que desconecta os clientes e para limpo dentro do prazo.

**Recursos.** Os valores são iniciais, **sem medição**:
- **app e Job:** requests `100m/128Mi`, limits `500m/256Mi` (1 worker sync do gunicorn, configuração padrão);
- **postgres:** requests `100m/256Mi`, limits `500m/512Mi`;
- **PVC:** `1Gi`, na StorageClass padrão do cluster.

**Informativo do Trivy.** Sobrou só o KSV-01010 (conteúdo sensível em ConfigMap), sobre a chave `DB_PORT`. É o falso positivo conhecido e não responde pela 3.3. Os informativos de seccomp e GID não aparecem.

## Pendências (dependem de gente)

1. **Confirmar as imagens no Loom.**
   - `registry.metacortex.io/orion/fake-shop:v1@sha256:07db…` saiu da execução 01 (orion-prod) e da origem no Docker Hub, não de um pedido para staging. Se staging deve rodar outra versão, troque a tag@digest nos dois arquivos e renomeie o Job para `fake-shop-migracao-<versao>`.
   - `registry.metacortex.io/orion/postgres:17@sha256:d74eeac9…` supõe que o Loom espelhe o postgres oficial com o mesmo digest. Não consegui acessar `registry.metacortex.io` daqui para confirmar. Se o espelho não existir, é preciso pedir ao Loom.
2. **Time dono (regra 1.5, recomendada).** Falta `metacortex.io/owner` no Deployment, no Job e no StatefulSet, e o script marca isso como JUSTIFICAR. Na execução 01, o dono de `orion-prod` foi `sre`, mas não presumi que seja o mesmo em staging. Preencha quando for confirmado e adicione `metacortex.io/runbook` se houver um.
3. **Criar o Secret `orion-fake-shop-db`** em `orion-stg`, fora do Git. A aplicação, o Job e o PostgreSQL leem as mesmas chaves:
   ```sh
   kubectl -n orion-stg create secret generic orion-fake-shop-db \
     --from-literal=user=ecommerce \
     --from-literal=password="$(openssl rand -base64 24 | tr -d '/+=')"
   kubectl -n orion-stg label secret orion-fake-shop-db \
     app.kubernetes.io/name=fake-shop app.kubernetes.io/instance=orion-stg \
     app.kubernetes.io/part-of=orion app.kubernetes.io/managed-by=platform
   ```
   Sem esse Secret, os três pods ficam em `CreateContainerConfigError`. O Secret precisa existir antes do primeiro start do PostgreSQL, porque o usuário e a senha só são aplicados quando o `PGDATA` está vazio.
4. **Banco próprio ou da plataforma.** Gerei o PostgreSQL no namespace porque ninguém informou um banco existente. Se o orion tiver banco provisionado pela plataforma em staging, remova `fake-shop-postgres.yaml`, troque `DB_HOST` no ConfigMap e ajuste o Secret. StorageClass, tamanho do volume e backup também precisam ser confirmados.
5. **Limits de memória.** Os valores são iniciais. Depois de observar o consumo em regime, ajuste o limit para 1,5x a 2x esse consumo (regra 2.1).
6. **Endpoints de saúde de verdade.** Pedir ao time da aplicação `/health` (sem banco) e `/ready` (com banco). A readiness em `/shop` carrega o catálogo inteiro e renderiza o template a cada 10s. Hoje são 9 produtos, mas o custo cresce com o catálogo.
7. **Exposição externa.** Não gerei Ingress/Gateway, porque o pedido não trouxe host, TLS nem o padrão de entrada do orion. Hoje o Service é só ClusterIP.
8. **Métricas multiprocess.** O projeto não tem config do gunicorn com o hook `child_exit` → `mark_process_dead`. Com 1 worker o impacto é pequeno. Com mais workers, as métricas de workers mortos se acumulam no `emptyDir`, que sobrevive a reinícios do container.

## Fora do padrão, mas encontrado no código (para o time da aplicação)

- **`src/index.py:16`: `app.secret_key = 'supersecretkey'` fixo no código.** Com essa chave, qualquer pessoa consegue forjar cookie de sessão. Ela deve vir de um Secret, e o manifesto passa a injetá-la quando o código ler a variável.
- **`src/index.py:24`: senha padrão `Pg1234`** usada quando `DB_PASSWORD` não está definida. O manifesto sempre define a variável, mas esse valor não deveria existir no código.
- **`src/index.py:90`: o checkout fecha o primeiro pedido aberto do banco** (`Order.query.filter_by(is_open=True).first()`), não o pedido do cookie do cliente. Com mais de um cliente, um checkout finaliza o carrinho de outra pessoa e grava nele o endereço e o cartão de quem pagou.
- **`src/index.py:106-110` e a migração: número do cartão e CVV gravados em texto puro no banco.** Isso fere o PCI-DSS, que proíbe guardar o CVV. Mesmo em staging, use só dados de teste.
- **`src/index.py:227-249`: `/update_quantity` e `/remove_item` aceitam qualquer `item_id`** sem verificar se o item pertence ao carrinho do cookie. É um IDOR entre clientes.
- **`src/index.py:39`: o número do pedido é `random.randint` de 6 dígitos com `UNIQUE`** (migração, linha 45). Colisão gera erro 500 no checkout, e a chance cresce com o volume de pedidos.
- **`src/index.py:259`: `debug=True`** só vale no `__main__` e não afeta o gunicorn. Fica registrado.
- **`src/requirements.txt:8`: `GitPython==3.1.0`** não é usado pelo código e tem CVEs conhecidos. Remover.
