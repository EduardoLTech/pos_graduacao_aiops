---
adr_number: "004"
status: aceito
created: 2026-09-26
supersedes: ""
superseded_by: ""
---

# ADR 004: Chave de host desconhecida é aceita e registrada, salvo quando o operador informa o fingerprint esperado

## Contexto
A conexão é feita pela biblioteca embutida (ADR 002), que não herda o `known_hosts` do
operador: a ferramenta precisa decidir sozinha o que fazer com a chave que o servidor
apresenta. O parque não tem hoje registro central de chaves de host.

O risco de não verificar não é roubo de credencial: na autenticação por chave pública, a
assinatura do cliente fica presa à sessão, e um intermediário não consegue repassá-la ao host
real. O risco é a **integridade do veredito**: um intermediário (ou outro servidor no endereço)
pode devolver um retrato forjado com código `0`, e o Pipeline decide por esse código.

A tensão é segurança contra uso: com verificação obrigatória, a ferramenta não roda contra
nenhum host sem preparação; sem verificação nenhuma, o veredito não tem garantia de origem.

## Alternativas Consideradas
- **Recusar host desconhecido** — protege o veredito. Contra: exige distribuir as chaves de
  host antes de auditar, o que o parque não tem; a ferramenta nasceria inutilizável no caso
  mais comum.
- **Aceitar e registrar o fingerprint no relatório** — roda contra qualquer host; o relatório
  diz com quem a ferramenta falou. Contra: a mitigação depende de alguém comparar o fingerprint
  depois, e esse papel é do Roster, que ainda não existe — para o Pipeline de hoje, não protege
  nada.
- **Aceitar em silêncio** — roda contra qualquer host, sem rastro. Contra: esconde o
  intermediário e impede qualquer conferência posterior.
- **Aceitar um `known_hosts` completo informado pelo operador** — verificação no formato padrão
  do OpenSSH. Contra: um arquivo a manter, sem fonte de chaves de host no parque para
  alimentá-lo.
- **Fingerprint esperado opcional, por parâmetro** *(proposto na revisão de segurança do
  desenho)* — quem tem a chave de host em mãos (no laboratório, a nuvem a publica; no parque,
  quem provisionou) fixa a identidade; divergência encerra sem relatório. Contra: um parâmetro a
  mais, e só protege quem o usa.

## Decisão
Aceitar a chave de host desconhecida e registrar algoritmo e fingerprint no bloco `host` do
relatório, sem gravar nada no `known_hosts` do operador — **exceto** quando o operador informa o
fingerprint esperado: aí a chave apresentada precisa bater, senão a ferramenta encerra como host
inalcançável, sem autenticar e sem relatório (PRD P11). O que pesou foi o custo: recusar tornaria
a ferramenta inútil hoje, e o fingerprint opcional fecha o caso do Pipeline para quem tem a
chave, sem exigir de quem não tem. O `known_hosts` completo fica adiado até existir uma fonte de
chaves de host no parque.

## Consequências
- **Positivas:** funciona contra qualquer host sem preparação; quem informa o fingerprint tem
  veredito com origem garantida; cada relatório carrega algoritmo e fingerprint, comparáveis
  entre execuções e entre ferramentas.
- **Negativas:** sem o parâmetro, a origem do veredito é por confiança na primeira conexão, e um
  intermediário produz relatório que parece legítimo até alguém comparar o fingerprint; o
  Pipeline só fica protegido se for configurado com o fingerprint de cada host.
- **Neutras / trade-offs aceitos:** como nada é gravado no `known_hosts`, cada execução sem o
  parâmetro é "primeira conexão"; o algoritmo sai junto do hash porque a biblioteca pode
  negociar um tipo de chave de host diferente do que o OpenSSH escolheria.
