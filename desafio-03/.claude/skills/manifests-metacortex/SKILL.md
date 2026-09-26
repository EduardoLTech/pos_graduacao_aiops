---
name: manifests-metacortex
description: >-
  Padrão de Manifests da Metacortex para Kubernetes: escreve manifesto novo já
  dentro do padrão (Deployment, Service, ConfigMap, Job, PDB, ServiceAccount) a
  partir do projeto da aplicação, e confere manifesto existente regra por regra
  com Trivy + script da casa, apontando o que barra na revisão de Segurança.
  Use sempre que alguém pedir para criar, gerar, revisar, conferir, validar ou
  corrigir manifesto/YAML de Kubernetes de workload do parque — "esse manifesto
  está no padrão?", "revisa esse deployment antes de eu subir", "o Seraph barrou
  meu manifesto", "gera os manifests do fake-shop", "empacota o kube-news pra
  k8s" — mesmo sem citar a Metacortex, e para clientes nyx, orion e helio.
  Não use para triagem de cluster em execução (pod que não sobe, service sem
  tráfego no cluster), para aplicar manifesto no cluster, nem para dúvida
  conceitual de Kubernetes.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash(python3 *conferir_manifests.py*), Bash(python *conferir_manifests.py*), Bash(python3 *inspecionar_imagem.py*), Bash(python *inspecionar_imagem.py*)
---

# Manifests da Metacortex

A página do padrão é longa demais para conferir no meio de uma tarefa, e manifesto
torto volta da revisão do Seraph. Esta skill divide o padrão em três partes, e cada
uma tem um dono:

- **Trivy** confere o que o catálogo dele já conhece: 2.1 requests/limits, 3.1
  `:latest`, 3.2 securityContext, 3.6 hostNetwork/hostPID/privileged.
- **`scripts/conferir_manifests.py`** confere o que é da casa e o Trivy não sabe:
  Bloco 1 inteiro, 2.2 a 2.5, 3.3, 3.4, 3.5 e 3.7. Ele também chama o Trivy e
  devolve um relatório por regra.
- **Você** resolve o que só se decide lendo o projeto: para onde as probes
  apontam, tamanho dos limits, onde a aplicação escreve em disco, se ela fala com
  o apiserver, se ela trata SIGTERM, o que é segredo. O script lista essas
  pendências em "Conferência que exige ler o projeto". Cada uma precisa de resposta
  com evidência do código, não de suposição.

A tabela completa das regras, com o critério de cada uma, está em
`references/regras-da-casa.md`. Leia antes de escrever ou de explicar um achado.

## Ferramentas

Leia a skill, o projeto e os manifestos com Read, Glob e Grep, nunca com `cat`, `ls`
ou `git` no Bash. O Bash desta skill só roda os dois scripts dela, **um comando por
chamada**: sem `cd`, `&&`, `;`, `|` nem `echo $?` depois. Qualquer coisa encadeada
cai fora da permissão e é negada. Os scripts resolvem o diretório sozinhos. No caminho
normal, a última linha já diz o código de saída. Um erro de uso (caminho inexistente,
YAML inválido, arquivo fora de UTF-8) sai no stderr com código 2, e a mensagem diz o
que corrigir.

Chame os scripts com `python3` (no Windows, `python`), pelo caminho absoluto da skill:
`<dir-da-skill>/scripts/<script>.py`. Use a ferramenta Bash também no Windows: a
permissão da skill cobre Bash, e a mesma chamada pela ferramenta PowerShell é negada.

## Preflight

`python3 <dir-da-skill>/scripts/conferir_manifests.py --verificar-ambiente` confere
Python, PyYAML e Trivy num comando só. Código 3 significa Trivy ausente: siga
`references/instalar-trivy.md`. Sem Trivy o script roda, mas as regras 2.1, 3.1,
3.2 e 3.6 saem `NAO_VERIFICADO` e o código de saída é 3: nunca reporte isso como
conforme.

## Modo conferir (o uso frequente)

1. Rode o script sobre o arquivo ou diretório:
   `python3 <dir-da-skill>/scripts/conferir_manifests.py <caminho>`
   Códigos de saída: 0 sem barramento, 1 barra, 2 erro de uso/YAML, 3 incompleto.
2. Localize o projeto da aplicação (repositório local ou clone que o usuário
   indicar) e responda cada item de "Conferência que exige ler o projeto" com
   `arquivo:linha`. Siga `references/leitura-do-projeto.md`. Sem o projeto, diga
   quais itens ficaram abertos: não os marque como conferidos.
3. Procure também o que nenhuma regra nomeia, mas que só o código revela. O
   exemplo clássico é a variável de ambiente que o manifesto passa e a aplicação
   não lê.
4. Entregue o relatório no formato abaixo e, se o usuário pedir, a versão
   corrigida do manifesto, conferida de novo pelo script até sair código 0.

Formato do relatório de conferência:

```
# Conferência — <arquivo> (<namespace>)
Veredito: BARRA | PASSA COM JUSTIFICATIVA | PASSA
## Barra na revisão        (regra · achado · correção)
## Exige justificativa no PR (regras recomendadas)
## Conferido lendo o projeto (item · resposta · evidência arquivo:linha)
## Fora do padrão, mas encontrado (achado do código ou informativo do Trivy)
```

## Modo escrever

1. Leia o projeto antes de escrever uma linha de YAML
   (`references/leitura-do-projeto.md`): porta, comando de start, endpoints de
   saúde, variáveis de ambiente que o código lê, o que é segredo, migração no
   start, caminhos de escrita, usuário da imagem.
2. Pergunte só o que o projeto não responde: cliente e ambiente, se não vierem no
   pedido; o time dono (`metacortex.io/owner`); a tag/digest publicada pelo Loom.
   Não invente valor para esses campos.
3. Parta de `assets/modelo-workload.yaml` e ajuste ao projeto. Um arquivo por
   componente é o bastante. Segredo entra só por referência (`secretKeyRef`); o
   comando para criar o Secret vai no relatório, não no repositório.
4. Rode o script no diretório gerado e corrija até sair código 0. Os informativos
   do Trivy que o modelo já resolve (seccomp, GID) devem sumir. Se algum sobrar,
   explique o motivo. O relatório já traz a mensagem do Trivy por arquivo (qual
   chave, qual campo); não rode `trivy config` avulso para ver o detalhe.
5. Entregue os YAML e um resumo curto das decisões que não eram óbvias (probe
   escolhida e por quê, migração, volumes, valores de recurso iniciais), com as
   pendências que dependem de gente: consumo observado para os limits, Secret a
   criar, exceções que precisariam de aprovação de Segurança.

## Limites

- Não aplique nada no cluster (`kubectl apply`, `helm`, `argocd`). A skill escreve
  e confere arquivo; subir é outro fluxo.
- Não baixe o nível de uma regra para fazer o manifesto passar. Regra obrigatória
  só tem exceção com aprovação escrita de Segurança no PR, e regra proibida não
  tem exceção para workload de cliente. Se o projeto torna uma regra impossível,
  diga isso e deixe a decisão para o humano.
- Banco que o projeto exige: gere-o junto (StatefulSet com PVC, no mesmo padrão:
  rótulos, securityContext, senha por Secret), a menos que o usuário diga que o banco
  já existe e informe o endereço. Não suponha banco externo que ninguém mencionou. Em
  prod, um banco de réplica única fere a 2.3, e o script vai barrar. Não contorne isso:
  entregue o manifesto, diga que ele depende de exceção aprovada por Segurança (ou de
  um banco com replicação) e deixe a decisão para o humano.
