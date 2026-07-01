# Decisão de engenharia com trade-offs (múltiplos caminhos)

Item de catálogo — domínio **arquitetura**. Prompt parametrizável para **decisões de
engenharia caras e sem resposta óbvia**: recebe o cenário (estado atual + restrições),
compara vários caminhos defensáveis, pesa os trade-offs contra critérios explícitos e as
restrições inegociáveis, e recomenda um caminho ou uma combinação faseada — com o
raciocínio à mostra.

## Quando usar

Sempre que a resposta honesta for **"depende"**: backpressure sob sobrecarga, estratégia
de escala (vertical × horizontal × serverless), migração, escolha de arquitetura,
qualquer trade-off custo × SLA × risco. Não use para diagnóstico de causa-raiz (aí a
resposta é única — use o item de análise de causa-raiz) nem para tarefas de saída direta.

## Parâmetros

| Parâmetro | Obrigatório | O que é |
|---|---|---|
| `estado_sistema` | sim | Estado atual (números, capacidade, picos, retenção, dependências). |
| `restricoes` | sim | Regras a respeitar — SLAs, orçamento, inegociáveis. Marque o que é rígido. |
| `opcoes_candidatas` | não | Caminhos já em cima da mesa. Se vazio, o modelo propõe. |
| `criterios` | não | Critérios de avaliação. Default: SLA · custo · risco de perda · complexidade · tempo até valer. |
| `sistema` | não | Qual sistema e o que faz, em uma linha. |

## Método (por que este desenho)

- **Base RISE.** A tarefa é procedural com input concreto (o cenário) e um critério de
  pronto claro — o RISE (Role-Input-Steps-Expectation) encaixa: o cenário é o **Input**,
  a sequência enumerar → desenvolver → filtrar → confrontar → recomendar é o **Steps**, e
  a Expectation fecha o contrato.
- **Tree-of-Thought como técnica central.** A decisão tem **mais de um caminho certo**;
  o Tree-of-Thought é a técnica indicada para ramificar o raciocínio, avaliar viabilidade
  e trade-offs de cada ramo e convergir — é o caso "depende" (comparação de estratégias,
  custo, complexidade), enquanto o Chain-of-Thought serviria a uma resposta única.
- **Step-Back no passo 0.** Enunciar as alavancas genéricas do problema e a restrição
  inegociável antes de olhar as opções evita ancorar na primeira ideia e mantém o filtro
  rígido no centro.

Custo do Tree-of-Thought: resposta mais longa e mais tokens (várias análises em
paralelo). Aceitável — em decisão cara, o raciocínio exposto é o produto.

## Como executar

1. Cole o **corpo** do prompt (do primeiro `#` em diante — sem o front-matter) no chat
   ou Workbench, com o modelo de execução declarado (`claude-sonnet-4-6`).
2. Substitua cada `{{param}}` pelo valor real; opcionais sem valor → `nenhum`. Os
   delimitadores `<estado_sistema>…</estado_sistema>` ficam.
3. Uma conversa limpa por cenário.

## Saída

Veredito de uma linha → caminhos considerados (≥3) → tabela de trade-offs → checagem das
restrições → recomendação (🔴 agora × 🟢 estrutural) → por que não as alternativas →
riscos e o que validar.
