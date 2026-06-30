# Triagem de saúde de pods (Kubernetes)

Item nº 1 do Playbook de IA Operacional da Aegis · domínio **SRE**.

## Descrição

Recebe um **snapshot** de cluster Kubernetes (saída de `kubectl get pods`,
`kubectl describe pod` e `kubectl logs`) e devolve uma **triagem** dos pods: para cada
pod problemático, a **causa provável** (cruzando status × eventos × logs), o **sinal**
que a comprova e a **próxima ação** do plantão. Reconhece o caso de cluster saudável
sem inventar problema.

## Objetivo

Dar ao plantão SRE uma triagem rápida e **confiável** da saúde dos pods, substituindo o
pedido ad-hoc ("cria um script que olha os pods e fala quais estão com problema") por um
item versionado, testável e reusável.

## Público-alvo

Plantonistas / SRE (time do Sam Wilson) operando o cluster onde o Sentinel roda.

## Como usar

1. Colete o snapshot com acesso ao cluster (get pods + describe dos suspeitos + logs).
2. Cole o conteúdo no parâmetro `{{snapshot}}` do `prompt.md`.
3. (Opcional) Preencha `{{namespace}}` e `{{contexto_extra}}`.
4. Execute em chat/playground/API. **Sem agente e sem tools** — o dado vai colado.

## Parâmetros de entrada

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `snapshot` | sim | Saída colada de `kubectl get pods` + `describe` + `logs`. |
| `namespace` | não | Namespace alvo, para contextualizar a saída. |
| `contexto_extra` | não | Janela do incidente, SLA, observações do plantão. |

## Pré-requisitos

- Snapshot já coletado por quem tem acesso ao cluster (o prompt não busca nada).
- Modelo de execução recomendado: `claude-sonnet-4-6` (criado com `claude-opus-4-8`).

## Framework e técnica

**R-I-S-E** (Role · Input · Steps · Expectation) como base — tarefa procedural e
diagnóstica — combinado com o elemento **Example** do **C-A-R-E**, para fixar formato e
profundidade da saída. Construído via **meta-prompting / CRAFT** (humano no controle):
o modelo gerou o rascunho, a curadoria final é humana.

Mapa dos componentes RISE no prompt: **Role** → `# Papel`; **Input** → `# Entrada`
(`{{snapshot}}`); **Steps** → `# Passos`; **Expectation** → `# Critério de pronto`
(definição de "pronto"/validação, pela definição do RISE). O `# Exemplo de um bloco`
é o **Example** do CARE.

## Casos de uso validados

| Cenário | Entrada | Resultado esperado |
|---|---|---|
| Pod reiniciando (OOM) | `CrashLoopBackOff` + `OOMKilled`/Exit 137 + log `out of memory` | Causa = limite de memória baixo p/ carga; ação = subir `limits.memory`. |
| Pods que não sobem | `ImagePullBackOff` (`manifest unknown`) + `Pending` (`Insufficient cpu`) | Tag inexistente → rollback; CPU insuficiente → reduzir request / escalar. |
| Tudo saudável | Todos `Running`/Ready; restart antigo estável | Veredito de saúde, **sem** inventar problema. |

## Limitações

- A qualidade da triagem depende da completude do snapshot; sem evidência o item
  classifica como **indeterminado** e indica o que coletar (não chuta).
- Não executa ações nem acessa o cluster — apenas diagnostica o que foi colado.

## Avaliação (próximos passos)

Pronto para amarrar no fluxo de avaliação: framework das 3 perguntas, **rubrica**
(causa correta? sinal citado? ação segura? reconheceu o saudável?) e teste
**golden-answer** no promptfoo.

## Changelog

| Versão | Data | Mudança |
|---|---|---|
| 1.0.0 | 2026-06-28 | Criação do item (Checkpoint 01). |
| 1.1.0 | 2026-06-30 | Adicionada seção `# Critério de pronto` (componente Expectation do RISE), antes diluído entre Formato e Regras. |
