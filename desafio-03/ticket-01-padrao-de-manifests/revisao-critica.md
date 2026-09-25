# Revisão crítica do Ticket 01

Revisão feita em 2026-09-24 pelo subagente `critical-code-analyst` (Claude Code, Opus 5.5),
a pedido do autor, depois da primeira entrega. O revisor só leu e rodou testes: não
escreveu na entrega. Os casos de teste dele ficaram fora do repositório.

Abaixo, os achados e o que foi feito com cada um. Estado: **críticos e altos corrigidos**;
médios e baixos registrados e **não** corrigidos.

## Veredito do revisor

> Tem problema material, mas é corrigível. A ordem do fluxo é real: o Trivy rodou antes do
> script, e o script antes do SKILL.md. As decisões de projeto nos manifests se sustentam.
> Três coisas pesam contra: o script dá "OK" e código 0 para regras do Trivy sem ter
> conferido nada; as duas execuções medem reprodução do que já estava na skill, não
> generalização; e a regra "banco da plataforma em prod" foi inventada e contradiz o
> Ticket 04. Eu não entregaria como está.

## Altos: corrigidos

| # | Achado (provado pelo revisor) | Correção | Evidência da correção |
|---|---|---|---|
| A1 | As regras 2.1, 3.1, 3.2 e 3.6 saíam OK sem nenhum workload. Um `values.yaml` sem objeto saía com código 0. Um `kind: List` com `nginx:latest` e senha literal passava nessas regras, porque nem o script nem o Trivy expandem `items` | O script expande `List.items`. Arquivo sem objeto de Kubernetes sai com código 2. As regras do Trivy só viram OK se havia container que ele leu: sem workload saem `NAO_SE_APLICA`, com workload dentro de List saem `NAO_VERIFICADO` | `fluxo-manual/05-correcoes-pos-revisao/`: `values.yaml` → código 2; `list.yaml` → 3.3 e 3.7 BARRA, regras do Trivy NAO_VERIFICADO; ConfigMap sozinho → NAO_SE_APLICA. Regressão: barrado 1, fake-shop 0, nyx-corrigido 0, `--sem-trivy` 3 |
| A2 | As execuções provavam reprodução, não o método. `leitura-do-projeto.md` trazia as respostas dos dois projetos, e o prompt da escrita entregou dono e digest | A referência ficou genérica: saíram `sequelize.sync`, `/unhealth`, `/metrics`, `/tmp/metrics`, gunicorn e `PROMETHEUS_MULTIPROC_DIR`, e ficaram os padrões de decisão. Nova execução no **encontros-tech**, projeto que não entrou no fluxo, **sem dono nem imagem** no prompt e com a sessão restrita às permissões da skill | `execucoes/03-escrita-encontros-tech/`: código 0 no script. Decisões próprias do projeto (readiness `/api/events/?limit=1` com a barra final, `create_all` no import, `error.html` inexistente). Dono e imagem ficaram como pendência, não inventados |
| A3 | "Banco da plataforma em prod" era uma política inventada e contradizia o Ticket 04, que pede o par aplicação + banco | A regra saiu do `SKILL.md`. Agora a skill gera o banco junto (StatefulSet no padrão), a menos que o usuário informe um banco existente. Em prod, a réplica única é tratada como exceção à 2.3, que Segurança precisa aprovar, sem contornar a regra | `SKILL.md`, seção Limites. A execução 03 gerou o `encontros-tech-postgres.yaml` |

As execuções 01 e 02 ficaram como estavam: são o registro do que a skill produziu na
versão anterior. O README aponta onde elas dependiam da regra removida.

## Médios: registrados, não corrigidos

- **M1 Permissões.** As execuções 01 e 02 rodaram com mais permissões que o
  `allowed-tools`. A execução 03 rodou no envelope da skill e teve **8 negações**, entre
  elas uma chamada do próprio script feita com `cd ... &&`, o `curl` para inspecionar a
  imagem de origem e o `trivy config` avulso. A referência manda usar `curl`, que o
  `allowed-tools` não concede.
- **M2 KSV-0125.** Com o `trivy-config-data` vazio, a KSV-0125 barra a 3.7 pelo
  mapeamento, o que contradiz "KSV-0125 é só evidência".
- **M3 Codificação.** Arquivo em UTF-16 ou Latin-1 dá traceback com código 1, o mesmo de
  "barra".
- **M4 Heurística de segredo.** Não pega senha em `args`, `DB_PWD` nem senha em comentário
  sem URL. Barra `TOKEN_TTL` por engano. A 2.5 aceita PDB com `minAvailable: 0`.
- **M5 Narrativa da origem.** A "escrita à mão" do fake-shop foi um único Write do agente,
  depois do script. O `/skill-creator` em "modo brainstorm" não teve turno humano. Parte
  da evidência de `fluxo-manual/` foi gerada depois das execuções. A saída dos casos de
  borda da KSV-0125 foi apagada.

## Baixos: registrados, não corrigidos

- **Falsos positivos:** `kustomization.yaml` e `selector.matchExpressions`; automount
  desligado só na ServiceAccount também barra.
- **Leniências:** `runAsUser: 20000`, `maxSurge: 50%`, a tag placeholder
  (`:PENDENTE-TAG-LOOM`, `:pendente-loom`) sai com código 0, e a 2.4 não se aplica a
  StatefulSet.
- **Leitura estrita do padrão:** 1.3 exigida no template do pod, `instance == namespace` e
  `part-of == cliente`. Rótulos do `jobTemplate` do CronJob não são conferidos.
- **Generalização exagerada:** a frase "KSV-0125 não dispara sem registry explícito" não
  se sustenta. Só o `nginx` sem organização escapou; `fabricioveronez/kube-news` disparou.
- **Secret do nyx:** o comando da conferência não aplica os quatro rótulos.
- **Description:** nunca passou por teste negativo nem de colisão com a skill de triagem do
  Ticket 02.
