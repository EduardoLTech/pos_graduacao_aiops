# fake-shop · orion-prod: manifests e decisões

- **Projeto lido:** `C:\estudo\github\desafio03\fake-shop` (Flask 3 + gunicorn 21 + PostgreSQL via psycopg 3; não há Dockerfile no repositório)
- **Namespace:** `orion-prod` · **dono:** `sre` (`metacortex.io/owner`)
- **Imagem:** `registry.metacortex.io/orion/fake-shop:v1@sha256:07db4334f5f2bb330f0f342a81ad203bb21b770b8d7a27c90edb2261fea34e2f` (publicada pelo Loom)
- **Conferência:** `conferir_manifests.py` com Trivy 0.74.0 → **código 0**, 18 regras OK, nenhuma barrada ou a justificar

## Arquivos

| Arquivo | Objetos |
|---|---|
| `manifests/fake-shop.yaml` | ServiceAccount, ConfigMap, Deployment (2 réplicas), Service ClusterIP :80 → 5000, PDB `minAvailable: 1` |
| `manifests/fake-shop-migracao.yaml` | ServiceAccount, Job `fake-shop-migracao-v1` |

## Decisões que não eram óbvias

**Porta e comando.** O processo escuta em 5000 (`src/entrypoint.sh:3`, `gunicorn --bind 0.0.0.0:5000 index:app`). O Deployment sobrescreve o `command` só com o gunicorn, sem o `flask db upgrade` da linha 2.

**Migração em Job.** O `entrypoint.sh:2` roda `flask db upgrade` a cada start. Com 2 réplicas, as duas migrariam ao mesmo tempo. A migração inicial (`migrations/versions/a11283937150_modelo_inicial.py:24-143`) também insere os 9 produtos do catálogo, então rodar duas vezes em paralelo pode duplicar dados ou falhar no meio. Por isso a migração foi para o Job `fake-shop-migracao-v1`, com a mesma imagem, o mesmo securityContext e `FLASK_APP=index.py` (README.md:14). O `upgrade` do Alembic não faz nada se o banco já estiver na última versão, então rodar o Job de novo não causa dano. O Job é imutável: a cada release, crie um Job novo com a versão no nome.

**Rótulo do Job diferente do rótulo da aplicação.** O pod do Job usa `app.kubernetes.io/name: fake-shop-migracao`. Se usasse `fake-shop`, ele cairia no seletor do Service. Como o Job não tem readiness, o pod seria considerado pronto e passaria a receber tráfego. Também contaria no PDB.

**Probes: a aplicação não expõe `/health` nem `/ready`.** Usei rotas que já existem:
- **liveness → `/metrics`** (`index.py:19`). A rota é servida pelo prometheus_flask_exporter e não consulta o banco. Se o banco ficar lento, o container não é reiniciado.
- **readiness → `/shop`** (`index.py:129-132`). A rota faz `Product.query.all()` e devolve 500 se o banco estiver fora do ar ou se a tabela `products` ainda não existir. Assim o pod só entra no Service depois que o Job terminou a migração, e isso não depende da ordem do apply.

**O que é segredo.** O código lê `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` e `DB_PORT` (`index.py:22-26`). `DB_PASSWORD` e `DB_USER` vêm por `secretKeyRef`. `DB_HOST` também vem do Secret, e não do ConfigMap: em prod o banco é o da plataforma (uma réplica de PostgreSQL no namespace não cumpriria a 2.3), eu não sei o host e não inventei um. A plataforma entrega o host junto com a credencial. O ConfigMap tem só `DB_NAME`, `DB_PORT` e `PROMETHEUS_MULTIPROC_DIR`. O manifesto não passa nenhuma variável que o código não lê. `FLASK_APP` só vai para o Job, porque o gunicorn não precisa dela.

**Escrita em disco com `readOnlyRootFilesystem`.**
- `/tmp/metrics` é o `PROMETHEUS_MULTIPROC_DIR` (README.md:16). O `GunicornPrometheusMetrics` (`index.py:18`) grava ali os arquivos de métrica de cada worker.
- `/tmp` guarda os arquivos de heartbeat dos workers do gunicorn (`worker_tmp_dir` padrão).
- Os dois são `emptyDir` separados, porque montar só `/tmp` esconderia um `/tmp/metrics` criado na imagem.
- O Job monta os mesmos volumes: `flask db upgrade` importa `index.py`, que inicializa o exporter multiprocess e exige o diretório.
- O Python não consegue gravar `__pycache__` no disco somente leitura. Ele ignora o erro e segue, sem impacto funcional.

**Sem acesso ao apiserver (3.4/3.5).** `requirements.txt` não tem cliente de Kubernetes. Por isso cada workload tem sua própria ServiceAccount, sem RBAC e com `automountServiceAccountToken: false`.

**SIGTERM (2.6).** Com o `command` sobrescrito, o gunicorn é o PID 1 e trata SIGTERM com um desligamento gracioso de 30s (`graceful_timeout`). Deixei o `terminationGracePeriodSeconds` no padrão de 30s. O `entrypoint.sh` original tem `bash` como PID 1 e chama o gunicorn sem `exec`, então o SIGTERM não chegaria à aplicação. Esse é mais um motivo para não usar o entrypoint.

**Recursos.** Com a configuração padrão, o gunicorn roda 1 worker sync por pod. Os valores iniciais são requests `100m/128Mi` e limits `500m/256Mi`, **sem medição**. O Job usa os mesmos valores.

**Informativo do Trivy.** Sobrou só o KSV-01010 (conteúdo sensível em ConfigMap). É o falso positivo conhecido sobre `DB_PORT` e não responde pela 3.3. Os informativos de seccomp e GID não aparecem.

## Pendências (dependem de gente)

1. **Criar o Secret `orion-fake-shop-db`** em `orion-prod`, fora do Git, com os dados do banco que a plataforma provisionar para o orion:
   ```sh
   kubectl -n orion-prod create secret generic orion-fake-shop-db \
     --from-literal=host='<host do PostgreSQL da plataforma>' \
     --from-literal=user='<usuário>' \
     --from-literal=password='<senha>'
   kubectl -n orion-prod label secret orion-fake-shop-db \
     app.kubernetes.io/name=fake-shop app.kubernetes.io/instance=orion-prod \
     app.kubernetes.io/part-of=orion app.kubernetes.io/managed-by=platform
   ```
   Sem esse Secret, nem o Job nem os pods sobem (`CreateContainerConfigError`).
2. **Provisionar o banco PostgreSQL de prod** pela plataforma e confirmar `DB_NAME` e `DB_PORT`. No ConfigMap estão `ecommerce` e `5432`, que são os valores padrão do código.
3. **Configuração da imagem não verificada.** Não consegui acessar `registry.metacortex.io` daqui (a resolução de nome falhou) e o repositório não tem Dockerfile. Falta confirmar três coisas no Loom ou com `docker inspect`:
   - O `WorkingDir` contém `index.py` e `migrations/`. Os dois `command` dependem disso.
   - `python` está no PATH.
   - O UID 10001 consegue ler os arquivos da aplicação.
   - Se a imagem já cria `/tmp/metrics`, não há problema: o `emptyDir` cobre esse caminho.
4. **Limits de memória.** Os valores são iniciais. Depois de observar o consumo em regime, ajuste o limit para 1,5x a 2x esse consumo (regra 2.1).
5. **Seed de produtos em prod.** A migração inicial insere um catálogo de demonstração. O time dono precisa confirmar se isso é aceitável no banco de produção do orion.
6. **Endpoints de saúde de verdade.** Pedir ao time da aplicação `/health` (sem banco) e `/ready` (com banco). A readiness em `/shop` carrega o catálogo inteiro a cada 10s por pod: hoje são 9 produtos, mas o custo cresce com o catálogo.
7. **Exposição externa.** Não entrou Ingress/Gateway: o pedido não trouxe host, TLS nem o padrão de entrada do orion. Hoje o Service é só ClusterIP.
8. **Runbook.** Não há `metacortex.io/runbook`. Adicionar quando a sre tiver um (regra 1.5).
9. **Métricas multiprocess.** O projeto não tem config do gunicorn com o hook `child_exit` → `mark_process_dead`. Com 1 worker o impacto é pequeno. Com mais workers, as métricas de workers mortos se acumulam.

## Fora do padrão, mas encontrado no código (para o time da aplicação)

- **`index.py:16` — `app.secret_key = 'supersecretkey'` fixo no código.** Com essa chave, qualquer pessoa consegue forjar cookie de sessão. Ela deve vir de um Secret e ser a mesma nas duas réplicas.
- **`index.py:24` — senha padrão `Pg1234`** usada quando `DB_PASSWORD` não está definida. O manifesto sempre define a variável, mas esse valor não deveria existir no código.
- **`index.py:90` — o checkout fecha o primeiro pedido aberto do banco (`Order.query.filter_by(is_open=True).first()`), não o pedido do cookie do cliente.** Com mais de um cliente, um checkout finaliza o carrinho de outra pessoa e grava nele o endereço e o cartão de quem pagou. Esse defeito é grave em prod.
- **`index.py:106-110` e a migração — número do cartão e CVV gravados em texto puro no banco.** Isso fere o PCI-DSS, que proíbe guardar o CVV. Precisa de decisão de Segurança antes de o orion receber pagamento real.
- **`index.py:227-249` — `/update_quantity` e `/remove_item` aceitam qualquer `item_id`** sem verificar se o item pertence ao carrinho do cookie. É um IDOR entre clientes.
- **`index.py:259` — `debug=True`** só vale no `__main__` e não afeta o gunicorn. Fica registrado.
- **`requirements.txt:8` — `GitPython==3.1.0`** não é usado pelo código e tem CVEs conhecidos. Remover.
