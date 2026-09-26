# Como ler o estado que o cluster devolve

Tabela de consulta: o agente abre quando encontra um `reason` ou um `exitCode` que não
reconhece. As linhas marcadas com ✔ foram vistas nos chamados do laboratório. As outras
vêm da documentação do Kubernetes e não foram reproduzidas.

## Sumário
- Container terminado (`lastState.terminated`)
- Container esperando (`state.waiting`)
- Pod e Deployment
- Service e endereços

## Container terminado: `containerStatuses[].lastState.terminated`

| reason / exitCode | Leitura | Cruze com |
|---|---|---|
| ✔ `OOMKilled` / 137 | passou do limite de memória do container | `resources.limits.memory` no spec; a duração (startedAt→finishedAt) diz se morre na subida ou sob carga |
| `Error` / 137, sem OOMKilled | recebeu SIGKILL: liveness falhou ou o prazo de encerramento acabou | eventos `Unhealthy` da liveness; `terminationGracePeriodSeconds` |
| `Error` / 143 | recebeu SIGTERM e saiu | quem mandou: rollout, liveness, drenagem do nó |
| ✔ `Error` / 1 ou outro ≠ 0 | a aplicação saiu com erro (no laboratório: `ECONNREFUSED` no banco, na subida) | `logs --previous` (aqui o log costuma ter a causa) e variáveis de ambiente do spec |
| `Completed` / 0 num Deployment | o processo terminou sozinho: command errado ou processo em segundo plano | `command`/`args` do spec |
| `ContainerCannotRun` / 128 | o binário do command não existe na imagem | `command` e a imagem |

`logs --previous` vazio não descarta nada: o processo pode ter morrido antes de escrever.

## Container esperando: `containerStatuses[].state.waiting`

| reason | Leitura | O que a mensagem diz |
|---|---|---|
| ✔ `ErrImagePull` / `ImagePullBackOff` | o kubelet não conseguiu baixar a imagem | ✔ `not found`: tag ou imagem inexistente. ✔ `no match for platform`: a imagem não tem a arquitetura do nó. `unauthorized` / `pull access denied`: credencial ou repositório privado (`imagePullSecrets`). `i/o timeout` / `no such host`: rede até o registry |
| ✔ `CrashLoopBackOff` | reinicia e está em espera entre tentativas | a causa está no `lastState.terminated`, não aqui |
| `CreateContainerConfigError` | referência quebrada no spec: ConfigMap ou Secret inexistente, ou chave que falta | a mensagem nomeia o objeto e a chave; confira se ele existe no namespace |
| `ContainerCreating` por muito tempo | volume que não monta ou rede do pod | eventos `FailedMount` / `FailedCreatePodSandBox` |

## Pod e Deployment

| Sinal | Leitura |
|---|---|
| `status.phase: Pending` sem `nodeName` | não foi agendado: eventos `FailedScheduling` dizem o motivo (recurso, taint, afinidade, PVC). Leia o nó (`allocatable`, `conditions`) |
| ✔ Deployment `Progressing=False`, `ProgressDeadlineExceeded` | o ReplicaSet novo não ficou pronto no prazo: vá para os pods do RS novo |
| ✔ Deployment sem `readyReplicas` | zero pronto; o campo some, não vem 0 |
| RS novo 0/N e RS antigo N/N | a versão nova falhou e a antiga ainda serve: é o "o pod nunca trocou" |
| pronto oscilando, sem reinício | readiness falhando: eventos `Unhealthy` com o caminho e o código |

## Service e endereços

| Sinal | Leitura |
|---|---|
| ✔ Endpoints sem `subsets` / EndpointSlice com `endpoints: null` | nenhum pod pronto casa o seletor: compare `spec.selector` do Service com os rótulos dos pods (`--show-labels`) |
| endereços presentes, mas em `notReadyAddresses` ou `conditions.ready: false` | os pods casam, mas não estão prontos: readiness |
| endereços prontos e mesmo assim sem resposta | `targetPort` contra `containerPort` (nome ou número) e a porta em que a aplicação realmente escuta |
| Service com endereço e porta certos, e o 503 continua para quem vem de fora | a camada de entrada: Ingress ou Gateway (backend, host, path, classe) e NetworkPolicy que bloqueie o namespace de origem. Não reproduzido no laboratório, que não tem Ingress |

O objeto Endpoints está a caminho da aposentadoria. Prefira EndpointSlice e use o
Endpoints só para confirmar.
