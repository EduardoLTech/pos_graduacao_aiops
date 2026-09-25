# Endurecimento de NetworkPolicy (default-deny) — com verificação e refino

Item de segurança do playbook. Pega um manifesto de **NetworkPolicy permissivo** (o
clássico allow-all disfarçado de política) e o transforma numa versão endurecida —
**default-deny explícito**, ingress/egress mínimos, cada regra comentada — e então a
submete a um **ciclo de verificação e refino** antes de aprovar. Reusável para
qualquer namespace: troca-se o manifesto, as regras do padrão e o mapa de serviços.

## Por que três prompts (e não um)

Um manifesto que vai para produção é output de **alto impacto**: um egress aberto
por engano vaza telemetry, um ingress aberto expõe o produto core. Geração
autoregressiva não volta atrás para se auditar — quando o modelo escreve uma regra
frouxa no fim do YAML, já “esqueceu” de checar se ela contradiz o padrão. A resposta
é o **Chain-of-Verification** na variante **factor-revise**: gerar, **auditar num
contexto isolado** e revisar. O isolamento (o revisor não vê a justificativa de quem
gerou) é o que remove o viés de confirmação — o modelo tende a aprovar o que ele
mesmo escreveu se auditar no mesmo contexto.

| Prompt | Papel no ciclo | Contexto |
|--------|----------------|----------|
| [`prompt.md`](prompt.md) | **Geração** (RISE) → v1 endurecida | conversa A |
| [`prompt-verificacao.md`](prompt-verificacao.md) | **Verificação** (CoVe plan+execute) → achados | **conversa nova**, isolada |
| [`prompt-refino.md`](prompt-refino.md) | **Refino** (CoVe revise) → v2 + changalog | volta à conversa A |

Repita verificação → refino até a auditoria aprovar. Teto prático: **3 rodadas** —
além disso as mudanças viram cosméticas.

## Framework e técnica

- **Geração — RISE (Role-Input-Steps-Expectation):** a tarefa é procedural e parte
  de um input concreto (manifesto + spec + mapa) com um artefato de saída bem
  definido; o `Steps` fixa a ordem do raciocínio e o `Expectation` vira o critério
  de pronto. Não é BAB (não é narrar uma transformação de estado) nem CARE (o valor
  não está num exemplo colado, e sim na conformidade com a spec).
- **Ciclo — Chain-of-Verification (factor-revise):** apropriado quando a pergunta é
  binária — *está correto / conforme a spec?* — e o output vai para produção. O
  isolamento da etapa de verificação é o ponto central.
- **Nota sobre self-refine:** o self-refine responde *“está bom o suficiente?”*
  (qualidade gradual). Aqui a pergunta é de **conformidade** (*allow-all é errado,
  não “melhorável”*), então o motor é o CoVe; o laço v1→v2→v3 apenas herda do
  self-refine a disciplina de **critérios explícitos** e **teto de rodadas**.

## Parâmetros

Geração: `{{manifesto}}`, `{{regras_padrao}}`, `{{mapa_servicos}}`, `{{namespace}}`
(opcional), `{{provedor}}` (opcional). Verificação: `{{manifesto_candidato}}` +
`regras`/`mapa`. Refino: `{{manifesto_anterior}}`, `{{achados_verificacao}}` +
`regras`/`mapa`.

## Como rodar o ciclo

1. **Conversa A:** cole o corpo de `prompt.md`, preencha os parâmetros → **v1**.
2. **Conversa NOVA (isolada):** cole `prompt-verificacao.md` com a **v1** em
   `{{manifesto_candidato}}` → **achados** (PASS/FAIL + evidência). Não traga o
   histórico da conversa A.
3. **Volte à conversa A:** cole `prompt-refino.md` com a v1 e os achados → **v2** +
   changelog.
4. Repita 2–3 com a v2 até o veredito ser `APROVADO`.

### Exemplo de uso (Elo de Geração)

Trecho da seção `# Entrada` do `prompt.md` já preenchida (namespace do Sentinel):

```text
Namespace alvo: sentinel-prod
Provedor/CNI: Cilium

<manifesto_permissivo>
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: sentinel, namespace: sentinel-prod }
spec:
  podSelector: {}          # pega TODOS os pods do namespace
  ingress: [ {} ]          # allow-all de entrada
  egress:  [ {} ]          # allow-all de saída
</manifesto_permissivo>

<regras_padrao>
- default-deny explícito em ingress e egress
- só o api pode receber ingress do gateway (porta 8080)
- egress apenas para o Relay (5000) e DNS interno (53)
</regras_padrao>

<mapa_servicos>
sentinel-api: ns=sentinel-prod  label app=sentinel-api   porta 8080
gateway:      ns=edge           label app=gateway
relay:        ns=relay-prod     label app=relay          porta 5000
</mapa_servicos>
```

A saída principal é o **manifesto endurecido** — cada regra comentada com o fluxo que libera:

```yaml
spec:
  podSelector: { matchLabels: { app: sentinel-api } }
  policyTypes: [Ingress, Egress]
  ingress:
    - from: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: edge } },
              podSelector: { matchLabels: { app: gateway } } }]
      ports: [{ port: 8080 }]        # ingress: gateway → API do Sentinel
  egress:
    - to: [{ podSelector: { matchLabels: { app: relay } } }]
      ports: [{ port: 5000 }]        # egress: API → ingestão no Relay
    # (regra de DNS porta 53 incluída porque egress default-deny quebra resolução)
```

Essa **v1** vai colada em `{{manifesto_candidato}}` do prompt de verificação, numa conversa nova.

## Modelo

Criado com `claude-opus-4-8`; executar com `claude-sonnet-4-6`. A verificação isolada
se beneficia de um modelo diferente/independente quando possível.
