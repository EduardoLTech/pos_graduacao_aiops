# Análise de causa-raiz de degradação (cross-artefato)

Item de catálogo do **Playbook de IA Operacional da Aegis** — domínio **SRE**.

Recebe um pacote de artefatos de um sistema em degradação (**configuração +
métricas + logs** da mesma janela) e leva a IA a **raciocinar até a causa-raiz** —
não ao sintoma —, cruzando as três fontes, com a cadeia causal evidenciada elo a
elo, mitigação imediata e correção definitiva. Nasceu do Checkpoint 03 (degradação
do Cerebro), mas é **genérico**: troque o pacote de entrada e ele serve a qualquer
degradação (Relay, Forge, Sentinel, um banco, uma fila…).

## Parâmetros

| Parâmetro | Obrigatório | O que é |
|---|---|---|
| `{{config}}` | sim | Config/parâmetros de infra (limites, heap, jobs, caches, shards…). |
| `{{metricas}}` | sim | Série temporal da janela do incidente, com significados/limiares. |
| `{{logs}}` | sim | Log da **mesma janela** das métricas, do(s) nó(s) afetado(s). |
| `{{sistema}}` | não | Qual serviço e o que ele faz, em uma linha. |
| `{{janela}}` | não | Janela do incidente + sintoma relatado pelo plantão. |
| `{{contexto_extra}}` | não | Deploys, mudanças recentes, SLA, dependências. |

Parâmetros opcionais sem valor: escreva `nenhum`.

## Framework e técnicas

- **RISE (Role-Input-Steps-Expectation)** como base: tarefa **procedural e
  diagnóstica**, com input concreto (config/métricas/logs), sequência de passos e
  critério de validação — o cenário ideal do RISE.
- **+ Chain-of-Thought explícito**: os `# Passos` definem os tópicos de raciocínio
  (linha do tempo → cadeia causal → evidência) em vez de deixar o modelo raciocinar
  por conta própria — mais assertivo e com menos alucinação.
- **+ Step-Back** (passo 0): carrega os princípios do subsistema *antes* de
  mergulhar nos dados, para o modelo não ancorar no sintoma mais visível.

## Como usar

1. Cole o **corpo do prompt** (do primeiro `#` em diante) em uma conversa nova com
   `claude-sonnet-4-6` (modelo de execução).
2. Substitua cada `{{param}}` pelo valor real; os delimitadores `<config>…</config>`,
   `<metricas>…</metricas>`, `<logs>…</logs>` **ficam**.
3. **Sanitize antes de colar** (ver abaixo) — o prompt assume entrada já tratada.

## Tratamento de dados antes do modelo externo

Trate os artefatos como **produção** antes de enviá-los a um provedor externo:

- **Anonimizar tenants** (ex.: `acme-corp`, `stark-industries` → `tenant-A`).
- **Remover topologia interna**: hostnames de nó, IPs, URLs de registry/repo,
  nomes de índice que possam carregar dados de cliente.
- **Confirmar que os logs não trazem payload/PII** (corpo de requisição, tokens).
- Preferir provedor com termos de **não-treinamento / retenção zero** (enterprise).

## Avaliação (ganchos)

- **Rubrica**: chegou à causa-raiz (não ao sintoma)? cada elo tem sinal das 3 fontes?
  mitigação ataca a origem? avaliou hipótese alternativa? declarou confiança/lacunas?
- **Golden-answer** no promptfoo, comparando contra a RCA de referência.
- **Chain-of-Verification** como passo extra para outputs que vão guiar uma ação em
  produção (gerar perguntas de verificação e respondê-las em contexto isolado).

## Versão

`1.0.0` — criado com `claude-opus-4-8`, executado com `claude-sonnet-4-6`.
