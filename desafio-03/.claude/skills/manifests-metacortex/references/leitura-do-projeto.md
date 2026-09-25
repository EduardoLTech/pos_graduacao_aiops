# Leitura do projeto: o que o YAML não diz

Porta, probe, banco e credencial saem do código, não de formulário. Cada resposta vai
com `arquivo:linha`. O que o projeto não responder fica como pendência nomeada.

## Conteúdo
- O que extrair
- Onde procurar por stack
- Imagem: usuário, workdir, comando
- Decisões recorrentes (sem endpoint de saúde, migração no start, escrita em disco, SIGTERM)

## O que extrair

| Pergunta | Serve para |
|---|---|
| Porta em que o processo escuta | `containerPort`, `targetPort`, probes |
| Comando de start (entrypoint, Procfile, script) | `command`, migração no start |
| Endpoints de saúde e **o que cada um consulta** | 2.2: liveness sem banco; readiness pode depender dele |
| Variáveis de ambiente que o código lê, com nome exato | `env`/ConfigMap. Variável que o manifesto passa e o código não lê é defeito, mesmo com o padrão cumprido |
| Quais variáveis são credencial | 3.3 |
| Migração ou alteração de schema no start | réplicas concorrentes migrando ao mesmo tempo |
| Caminhos em que escreve (tmp, cache, métricas multiprocess, upload) | 3.2: `emptyDir` com `readOnlyRootFilesystem` |
| Usa cliente de Kubernetes? | 3.4/3.5 |
| Trata SIGTERM? Quem é o PID 1? | 2.6 |
| Rotas administrativas ou de teste expostas sem autenticação | "fora do padrão, mas encontrado" |

## Onde procurar por stack

- **Manifesto de dependências** (`package.json`, `requirements.txt`, `pyproject.toml`,
  `go.mod`, `pom.xml`...): framework, driver de banco, ferramenta de migração, cliente de
  Kubernetes, exportador de métricas.
- **Ponto de entrada** (script de start, `entrypoint.sh`, `Procfile`, `CMD` da imagem): o
  que roda antes do servidor e quem vira PID 1.
- **Bind de porta, definição de rotas, leitura de variável de ambiente, registro de
  handler de sinal**: busque pelo idioma da stack encontrada, não por uma lista fixa.
- **ORM e migração**: sincronização ou alteração de schema no boot conta como migração
  no start.

## Imagem: usuário, workdir, comando

Se não houver Dockerfile no repositório, leia a configuração da imagem publicada
(`docker inspect`, ou a API do registry sem Docker) para saber `User`, `WorkingDir`,
`Cmd` e o que o build criou (diretórios, donos). É isso que diz se `runAsUser: 10001`
consegue ler os arquivos e se o `command` sobrescrito roda no diretório certo.

`registry.metacortex.io` só resolve dentro da rede do parque. Fora dela, inspecione a
imagem de **origem** que o Loom espelhou (normalmente no Docker Hub, com o mesmo digest),
sem Docker, pela API do registry:

```sh
repo=<org>/<imagem>; ref=<tag-ou-digest>
tok=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:$repo:pull" | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
# manifest (índice multi-arch -> escolha o digest amd64) -> config.digest -> blob com User/WorkingDir/Cmd/history
curl -s -H "Authorization: Bearer $tok" -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json" "https://registry-1.docker.io/v2/$repo/manifests/$ref"
```

Só marque a imagem como "não verificada" se nem a origem for alcançável.

## Decisões recorrentes

**Aplicação sem endpoint de saúde.** Não invente rota. Escolha entre rotas que existem:
- liveness em rota que responde sem tocar no banco (rota de métricas, página estática);
- readiness em rota barata que depende do que o tráfego precisa (banco, schema). Uma
  vantagem: o pod só entra no Service depois que a migração terminou.
- Registre como pendência para o time da aplicação expor `/health` e `/ready` de
  verdade. `tcpSocket` só é saída quando não existe rota HTTP que sirva.

**Migração no start.** Com mais de uma réplica, cada pod migraria ao mesmo tempo. Tire a
migração do container da aplicação (`command` só com o servidor) e leve-a para um `Job`
com o nome versionado (`<componente>-migracao-<versao>`), mesma imagem, mesmo
securityContext. A readiness dependente do schema segura o tráfego até o Job terminar,
sem depender da ordem do apply.

**Escrita em disco com `readOnlyRootFilesystem`.** Um `emptyDir` por caminho gravável. Se
montar um diretório pai (ex.: `/tmp`), monte também os subdiretórios que a imagem
criava ali e que a aplicação usa, porque o mount esconde o que havia no caminho.

**SIGTERM.** Processo como PID 1 sem handler ignora SIGTERM, e o pod leva o
`terminationGracePeriodSeconds` inteiro para morrer; shell como PID 1 que chama o
servidor sem `exec` não repassa o sinal. Servidores de aplicação costumam tratar
SIGTERM: confirme no do projeto. Aponte a correção no código; não compense com grace
period maior.

**Recursos sem medição.** Declare requests/limits iniciais conservadores e diga que são
iniciais. A regra da casa (1,5x a 2x o consumo em regime) só se aplica com métrica
observada.
