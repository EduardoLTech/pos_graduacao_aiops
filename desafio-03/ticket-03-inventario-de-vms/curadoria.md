# Curadoria — Ticket 03

O que mudou entre o que foi escrito antes do código e o que a implementação, a execução contra
host real e uma revisão independente mostraram. Cada linha aponta onde a correção foi feita.

## Onde o documento precisou ser corrigido

| # | Documento | O que estava escrito | O que a implementação mostrou | Destino |
|---|---|---|---|---|
| 1 | design D5, ADR 002 | Chave carregada por `PKey.from_path`; passphrase reconhecida por `PasswordRequiredException` | Com chave protegida, `PKey.from_path` (paramiko 5.0.0) levanta `TypeError` genérico. A verificação feita antes do ADR usou o carregador por classe, que é outra API. Trocado pelo carregador de cada classe; PKCS#8 fica sem suporte | Design corrigido; o ADR 002 continua certo na decisão, mas a frase de verificação descreve a outra API |
| 2 | PRD P5 | Códigos 0–4 | Nenhum código cobre defeito da própria ferramenta; usar 2 ou 3 afirmaria algo falso sobre o uso ou o host. Criado o código 5 | PRD P5 e spec `conexao-ssh` |
| 3 | design D1 | `baseline.yaml` na raiz do projeto | Na raiz, o padrão só funciona executando a partir do diretório do projeto; movido para dentro do pacote | Design |
| 4 | PRD P22 × exemplo do enunciado | Toda porta em bind público fora de `[22]` é desvio de `publicas_permitidas` | A 9100 em `0.0.0.0` virava dois desvios críticos. O exemplo do enunciado conta `critico: 2` para swap + 9100, isto é, a 9100 uma vez só | Decisão do usuário: seguir o enunciado. PRD P22, spec e teste |
| 5 | PRD P14 | `tamanho` na "maior unidade K/M/G/T que dê ao menos 1" | Na VM, 1 GiB de swap aparece no `/proc/swaps` como 1048572 KiB (o cabeçalho é descontado): pela regra literal, `1024M`. As amostras escritas à mão usavam 4 GiB e arredondavam para `4G`, por isso o teste não pegou | Código arredonda antes de comparar; teste com o valor medido; PRD P14 |
| 6 | PRD I1, design D2 | NTP lido por `timedatectl show` | Na VM, o `timedatectl` ativa o `systemd-timedated` pelo D-Bus, que sobe, cria diretórios em `/tmp` e `/var/tmp` e os apaga ao sair: a leitura ligava um serviço no host. Medido com `find -newer` e journal contra uma rodada de controle | Decisão do usuário: `adjtimex` só leitura via `python3 -c` constante, com o mesmo critério do `timedated`. Design D2, spec `inventario-do-host`, teste que proíbe `timedatectl` |
| 7 | design D4, PRD P25 | Fontes de chave: contas com shell de login, mais `root` | Revisão independente: contas com shell `nologin`, `false` ou vazio também autenticam por chave (e abrem túnel). Puladas, uma chave indevida ali passava sem aviso — com coleta como root, falso `conforme` numa regra crítica | Script percorre todas as contas. Design D4, PRD P25, spec; na evidência, a conta `svc-legado` com shell `nologin` sai como desvio |
| 8 | PRD P14/P24 | `processo` `null` quando o dono não é legível | Com usuário comum, `processo` saía `null` em **todas** as portas da evidência: o dado que o enunciado pede nunca aparecia. O `ss -e` dá, sem privilégio, o uid do dono e a unidade systemd | Portas ganham `conta` e `unidade`. PRD P14/P24, design D2, spec |
| 9 | PRD P20, Restrições | `encontrado` com a frase de apresentação (`true (4G)`) | No JSON, `"esperado": false` ao lado de `"encontrado": "false"` quebra quem compara os dois. No exemplo do enunciado, a frase só aparece no Markdown | `encontrado` com tipo no JSON, frase só no Markdown. PRD Restrições, spec `relatorio` |
| 10 | PRD §6 | "Portas UDP — UDP não tem escuta" | Justificativa errada: um socket UDP em todos os endereços também está exposto, e o `rpcbind` do próprio laboratório abre a 111 em UDP | UDP continua fora, agora como limite declarado com o risco escrito (PRD §6) |

## O que o agente entendeu diferente do que foi escrito

O agente escreveu o PRD, as specs e o código a partir do enunciado. Onde a leitura dele
divergiu do texto:

- **"Processo dono" como opcional.** O enunciado lista o processo dono da porta como parte do
  inventário, sem ressalva. O agente leu a restrição de usuário comum como licença para deixar o
  campo sempre vazio, e registrou isso como decisão (P24) em vez de procurar o que era legível
  sem privilégio. Só a revisão mostrou que o dado vinha `null` em 100% das portas. (#8)
- **A frase do Markdown no JSON.** O exemplo do enunciado mostra `true (4G)` só na tabela do
  Markdown; no JSON o `encontrado` é valor. O agente juntou os dois formatos num campo só e
  escreveu no PRD que `encontrado` era a frase. (#9)
- **"Chaves autorizadas" como chaves de quem faz login.** O enunciado pede as chaves autorizadas
  do host. O agente restringiu às contas com shell de login, supondo que as demais não
  autenticam — suposição falsa para SSH. (#7)
- **"Só lê" como "nenhum comando que escreve".** O agente escolheu comandos de leitura e não
  considerou que uma leitura pode ativar um serviço no host. Foi a medição, não o desenho, que
  achou. (#6)
- **Regras lidas isoladamente.** O agente escreveu P22 regra a regra, sem conferir o total contra
  o exemplo; o exemplo contava a 9100 uma vez. (#4)
- **O exemplo como fonte menos confiável que a regra.** Onde exemplo e regra do enunciado
  divergiam (o `resumo` do exemplo soma 9 para 11 regras), o agente seguiu a regra — escolha
  mantida e registrada no PRD, Restrições.

## Limites da ferramenta encontrados na implementação

- **Tempo esgotado na autenticação aparece como "autenticação recusada".** O paramiko levanta a
  mesma exceção para os dois casos; separar exigiria ler o texto da mensagem, o que o ADR 002
  recusou.
- **Com usuário comum, o código 0 nunca sai** e o desvio de login de root nunca aparece: as
  regras de chaves e de login de root exigem leitura privilegiada. O pipeline precisa tratar `4`
  como "sem desvio visível, com ressalva" (README).
- **Coleta como root não foi validada contra host real.** Os caminhos de `sshd -T` legível só
  são provados em teste. Com root, `sshd -T` sem `-C` não considera blocos `Match`.

## Atrito com o ciclo de spec

- O validador do OpenSpec (1.2.0) só aceita requisito que tenha `SHALL` ou `MUST` literal: as
  specs em português usam `MUST`/`MUST NOT` como palavra normativa.
- O parser do OpenSpec lê `##` dentro de bloco de código como cabeçalho de seção: o esqueleto
  do Markdown não pôde ser copiado literalmente para a spec e virou lista, apontando para o PRD.
