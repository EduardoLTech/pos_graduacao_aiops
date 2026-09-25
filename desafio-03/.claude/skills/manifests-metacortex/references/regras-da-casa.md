# Regras da casa: o que cada uma exige e quem confere

Fonte: *Padrão de Manifests da Metacortex*, wiki de Plataforma, mantida por Segurança &
Compliance (revisão 2026-07-29). Níveis: **obrigatório** barra sem discussão;
**recomendado** exige justificativa escrita no PR; **proibido** não tem exceção para
workload de cliente. Exceção a obrigatório só com aprovação escrita de Segurança no
PR, com prazo de validade.

## Conteúdo
- Bloco 1: identidade e nomenclatura
- Bloco 2: resiliência
- Bloco 3: segurança
- Checagens do Trivy fora do padrão
- O que não entrou na skill

## Bloco 1: identidade e nomenclatura

| Regra | Nível | Quem confere | Critério |
|---|---|---|---|
| 1.1 Nome em kebab-case | obrigatório | script | minúsculo, hífen, sem camelCase, underscore ou ponto (`NyxAPI` → `nyx-api`) |
| 1.2 Namespace `<cliente>-<ambiente>` | obrigatório | script | ambientes `dev`, `stg`, `prod`; um cliente por namespace. Fora do formato, o Construct não cria o namespace |
| 1.3 Quatro rótulos | obrigatório | script | em todo objeto **e** no template do pod: `app.kubernetes.io/name` (componente), `instance` (= namespace), `part-of` (= cliente), `managed-by` (`platform`, `argocd` ou `helm`). `app:` sozinho não atende |
| 1.4 Seletor casa com o pod | obrigatório | script | `matchLabels` do workload e `selector` do Service idênticos aos rótulos do template, caractere por caractere. É o erro mais comum e mais silencioso: o Service sobe sem endpoint |
| 1.5 Anotação de dono | recomendado | script | `metacortex.io/owner` com o time; `metacortex.io/runbook` quando existir. O valor vem de gente, não se inventa |
| 1.6 Nome de container | recomendado | script (nome genérico) + você | nome do componente (`api`, `worker`, `web`), nunca `app`, `main` ou `container` |

## Bloco 2: resiliência

| Regra | Nível | Quem confere | Critério |
|---|---|---|---|
| 2.1 requests e limits | obrigatório | Trivy (KSV-0011/15/16/18) + você | CPU e memória em todo container. **Você:** limit de memória entre 1,5x e 2x o consumo observado em regime. Sem medição, declare o valor como inicial e registre a pendência |
| 2.2 readiness e liveness | obrigatório | script (presença) + você (alvo) | as duas em qualquer ambiente, apontando para endpoint que a aplicação **de fato expõe**. Readiness responde "posso receber tráfego?"; liveness responde "estou vivo?". A liveness não pode depender do banco: banco lento reinicia o container, e o reinício não conserta o banco |
| 2.3 replicas >= 2 em prod | obrigatório | script | ausência de `replicas` é 1. dev/stg aceitam 1 |
| 2.4 Estratégia em prod | obrigatório | script | `RollingUpdate`, `maxUnavailable: 0`, `maxSurge: 1` |
| 2.5 PDB em prod | recomendado | script | workload de prod com mais de uma réplica tem PDB com `minAvailable: 1` no mínimo, selecionando o pod |
| 2.6 terminationGracePeriodSeconds | recomendado | você | o padrão de 30s serve se a aplicação trata SIGTERM e drena nesse tempo. Processo que é PID 1 sem handler ignora SIGTERM e morre só no SIGKILL, ao fim do prazo |

## Bloco 3: segurança

| Regra | Nível | Quem confere | Critério |
|---|---|---|---|
| 3.1 `:latest` | proibido | Trivy (KSV-0013) | tag imutável ou digest; sem tag também conta como latest |
| 3.2 securityContext | obrigatório | Trivy (KSV-0001/03/12/14/20) + você | `runAsNonRoot`, `runAsUser: 10001`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: [ALL]`. **Você:** todo caminho em que a aplicação escreve precisa de `emptyDir` montado (montar um diretório pai esconde os subdiretórios que a imagem criou nele) |
| 3.3 Segredo em texto puro | proibido | script + você | nada sensível em `env.value`, ConfigMap ou comentário; sempre `secretKeyRef`. Secret com `data`/`stringData` no manifesto também é segredo versionado no Git. **Você:** decidir o que é sensível, porque o script usa heurística de nome e de URL com senha |
| 3.4 `automountServiceAccountToken: false` | obrigatório (desde 2026-07-29) | script + você | obrigatório quando a aplicação não fala com o apiserver. **Você:** confirmar no código (cliente de Kubernetes nas dependências?) |
| 3.5 ServiceAccount dedicada | recomendado | script | uma por workload, nunca a `default`; sem RBAC se não fala com a API |
| 3.6 hostNetwork, hostPID, privileged | proibido | Trivy (KSV-0009/10/17) | sem exceção para workload de cliente |
| 3.7 Registry interno | obrigatório | script | toda `image:` começa com `registry.metacortex.io/`. Imagem pública entra pelo Loom, que espelha e republica |

A regra 3.7 fica com o script porque a KSV-0125 do Trivy, mesmo configurada com a lista
da casa (`assets/trivy-config-data/`), **não dispara** para imagem sem registry explícito
(`nginx` = Docker Hub implícito). Com a lista padrão, ela ainda acusa
`registry.metacortex.io` como não confiável.

## Checagens do Trivy fora do padrão

O script lista, como informativo, o que o Trivy acha e a página não pede: seccomp
(KSV-0030/0104), GID <= 10000 (KSV-0021), KSV-0106, KSV-0118. Não barram na revisão
da casa, mas a varredura de Segurança roda o mesmo Trivy no pipeline. O
`assets/modelo-workload.yaml` já sai limpo delas (`seccompProfile: RuntimeDefault`,
`runAsGroup`/`fsGroup: 10001`).

A KSV-01010 (conteúdo sensível em ConfigMap) marcou `DB_PORT` como sensível: é falso
positivo e não responde pela 3.3.

## O que não entrou na skill

- **Bloco 4 (vocabulário: Pod, ReplicaSet, Deployment, Service, port/targetPort,
  Endpoints, ConfigMap/Secret, Probes).** Foi escrito para gente que chega na
  plataforma, não é regra, e o modelo já sabe isso. Carregar esse bloco a cada disparo
  só custaria token.
- **Histórico de revisões da página.** Só vale o estado atual (por exemplo, a 3.4 já é
  obrigatória).
