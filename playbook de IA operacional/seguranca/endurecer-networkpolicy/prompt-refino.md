---
nome: Refino de NetworkPolicy (aplicar achados da auditoria)
dominio: seguranca
objetivo: Receber a NetworkPolicy da rodada anterior e os achados da auditoria de
  segurança e produzir a próxima versão que endereça CADA achado, com um changelog
  ligando achado → correção. É o elo de REVISÃO do ciclo Chain-of-Verification
  (factor-revise) — fecha a volta v1 → verificação → v2 (→ v3…).
quando_usar: Depois que a verificação reprovou (ou apontou melhorias em) uma versão
  do manifesto. Roda de volta no contexto de geração, agora munido da auditoria
  independente. Repita o ciclo até a verificação aprovar (teto prático: 3 rodadas).
inputs:
  manifesto_anterior: A versão auditada (v1, v2…).
  achados_verificacao: A saída do prompt de verificação (perguntas + PASS/FAIL +
    correção exigida).
  regras_padrao: As regras do padrão (para não regredir ao corrigir).
  mapa_servicos: O mapa de identificação dos serviços (labels/portas corretos).
modelo_recomendado: claude-sonnet-4-6 (execução); criado com claude-opus-4-8
versao: 1.0.0
framework: Chain-of-Verification (revise) + laço estilo self-refine (teto 3 rodadas)
tags: [seguranca, kubernetes, networkpolicy, cove, refino, changelog]
---

# Papel

Você é quem escreveu a NetworkPolicy e acaba de receber a auditoria de um revisor
de segurança independente. Você trata **cada FAIL como bloqueante** e endereça todos
antes de reemitir — sem discutir, sem deixar “para depois”, e sem **regredir** nada
que já estava correto.

# Entrada

<manifesto_anterior>
{{manifesto_anterior}}
</manifesto_anterior>

<achados_verificacao>
{{achados_verificacao}}
</achados_verificacao>

<regras_padrao>
{{regras_padrao}}
</regras_padrao>

<mapa_servicos>
{{mapa_servicos}}
</mapa_servicos>

# Tarefa

Produza a **próxima versão** do manifesto que resolve **todos** os achados da
auditoria, mantendo o que já passou. Para cada achado, mostre explicitamente como a
nova versão o endereça.

# Passos

1. **Ler os achados** — liste cada FAIL/observação com o que a auditoria exigiu.
2. **Corrigir sem regredir** — aplique a correção usando **labels/portas do mapa**;
   confira que a correção de um achado não reabre outro (ex.: mexer no egress e
   deixar o DNS de fora).
3. **Reemitir** — o manifesto completo e aplicável, ainda com um comentário por regra.
4. **Rastrear** — changelog ligando cada achado à mudança concreta.

# Formato da saída

1. **Versão N do manifesto** — bloco ```yaml``` completo e aplicável (não um diff).
2. **Changelog achado → correção** — tabela: `achado da auditoria | mudança aplicada | trecho novo`.
3. **Achados não endereçados** — vazio no caso ideal; se algo depende de dado que
   falta, marque `⚠ pendente: <o que falta>` em vez de silenciar.

# Regras

- **Todo achado tem de aparecer no changelog** — nenhum FAIL some sem tratamento.
- **Sem regressão**: não remova nem afrouxe uma regra que já estava correta.
- **Labels/portas do mapa**, sempre; nada inventado.
- Mantenha **default-deny explícito** e **comentário por regra** na nova versão.
- Se a auditoria já veio `APROVADO`, não invente mudança cosmética — declare
  `sem alterações necessárias` e pare o laço.
