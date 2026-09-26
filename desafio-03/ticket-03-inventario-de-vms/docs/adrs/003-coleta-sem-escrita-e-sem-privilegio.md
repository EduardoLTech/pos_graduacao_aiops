---
adr_number: "003"
status: aceito
created: 2026-09-26
supersedes: ""
superseded_by: ""
---

# ADR 003: A coleta usa só leituras já disponíveis no host, com o usuário comum, e o que não se lê vira `nao_verificado` por regra

## Contexto
O enunciado deixa aberto como cada dado é coletado e fecha duas coisas: a ferramenta **só lê**
(nada instalado, escrito ou corrigido do outro lado) e a coleta entra com **usuário comum**,
sem privilégio. Parte do baseline (configuração efetiva do SSH, chaves autorizadas de outras
contas, processo dono de portas de outros usuários) não é legível assim. O enunciado exige que
isso apareça como `nao_verificado` — nem como conforme, nem abortando a execução — e que a
decisão sobre "o que acontece quando um dado não pode ser coletado" seja registrada.

Também pesa a repetição: duas execuções seguidas precisam devolver o mesmo veredito para cada
regra (PRD P12).

## Alternativas Consideradas
- **Só leituras que o sistema base do host já oferece, com o usuário da conexão** — nada é
  copiado para o host; cada regra é avaliada à parte, e a falta de permissão ou a falha de uma
  leitura afeta só aquela regra. Contra: o que exige privilégio fica sistematicamente
  `nao_verificado` (na prática, chaves de outras contas e login de root efetivo).
- **Copiar um script de coleta para o host e executá-lo** — uma ida e volta só, coleta mais
  uniforme. Contra: escreve no host auditado (arquivo temporário), o que o invariante "só lê"
  proíbe.
- **Tentar elevação de privilégio quando disponível (`sudo` não interativo)** — verificaria mais
  regras onde o usuário tem sudo. Contra: o mesmo host passa a ter vereditos diferentes conforme
  quem roda; um usuário com sudo põe a ferramenta em condição de escrever no host; e o enunciado
  define a coleta com usuário comum.
- **Abortar a execução quando um dado não pode ser lido** — mais simples. Contra: o enunciado
  diz que abortar seria inútil; um host com uma regra ilegível ficaria sem nenhum retrato.

## Decisão
A coleta executa apenas leituras que o sistema base do host já oferece, com o usuário da
conexão, sem copiar nada e sem nunca tentar elevação de privilégio. Cada regra é avaliada
isoladamente, e há três desfechos quando falta evidência:

- **sem privilégio** para ler → `nao_verificado`, motivo "exige privilégio que o usuário da
  coleta não tem";
- **a leitura falhou** (comando ausente, erro, tempo ou tamanho excedido) → `nao_verificado`,
  motivo "falha de coleta" com o que falhou (PRD P9);
- **a conexão caiu** durante a coleta → a execução inteira termina como host inalcançável,
  sem relatório, porque um retrato pela metade não distingue regra ilegível de regra não
  tentada (PRD P8).

Evidência parcial sem desvio encontrado é `nao_verificado`; um desvio encontrado na parte
legível já é `desvio` (PRD I4, P25). O que pesou mais foi o "só lê": copiar um script ou elevar
privilégio abrem a porta para escrita no host, e isso não se negocia.

## Consequências
- **Positivas:** o invariante "só lê" vale por construção, não por disciplina; o veredito
  depende do host, não de quem roda; uma regra ilegível nunca derruba as outras.
- **Negativas:** regras críticas (chaves SSH) e altas (login de root) tendem a sair
  `nao_verificado` com usuário comum — o parque continua sem resposta para elas até existir um
  usuário de coleta com leitura privilegiada, que é decisão de outro ADR; várias idas e voltas
  SSH em vez de uma; a coleta depende de ferramentas do sistema base do Ubuntu estarem
  presentes.
- **Neutras / trade-offs aceitos:** o próprio login deixa registro no host (log de
  autenticação, registro de sessão); isso é efeito do acesso por SSH, que o enunciado impõe, e
  não escrita da ferramenta (PRD I1). As leituras rodam com idioma e formato fixos para que a
  saída não dependa da configuração regional do host. Os comandos executados no host são fixos
  e nunca incorporam texto vindo do próprio host (PRD I7).
