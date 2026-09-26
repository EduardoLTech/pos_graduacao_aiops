---
adr_number: "005"
status: aceito
created: 2026-09-26
supersedes: ""
superseded_by: ""
---

# ADR 005: O host de validação é uma VM Ubuntu no GCP, provisionada por script `gcloud`

## Contexto
A entrega exige evidência de execução real contra um host Linux alcançável por SSH: host
sem desvio, host com desvios, host inalcançável e execução repetida. As regras do baseline
dependem de coisas que só um host de verdade tem: systemd com unidades e sockets, kernel próprio
(`kernel.versao_minima: 6.5`), interfaces de rede com bind em todos os endereços ou só no
endereço interno, swap e sincronização de tempo. O parque da Metacortex não é acessível; o host
de validação precisa ser criado.

O ambiente do operador é Windows 11 Home (sem Hyper-V), com WSL, Docker Desktop e VirtualBox
disponíveis, e com `gcloud` autenticado num projeto GCP.

## Alternativas Consideradas
- **VM no GCP, criada por script `gcloud`** — host real com systemd, kernel próprio e rede de
  nuvem; o script versionado recria o mesmo host e documenta cada escolha (imagem, rede,
  firewall, usuário). Contra: custo enquanto a VM existe; o estado "com desvios" deixa serviços
  proibidos e a porta 9100 em bind público numa máquina com IP externo.
- **VM no GCP, criada pelo console web** — mesmo host. Contra: descartada pelo usuário — os
  cliques não ficam versionados, e a evidência não diz como o host foi montado.
- **VM local no VirtualBox** — sem custo, VM real. Contra: rede NAT/host-only não reproduz a
  situação de uma VM do parque acessada pela rede.
- **WSL** — já instalada. Contra: kernel da Microsoft e rede do Windows tornam as regras de
  kernel e de portas artificiais.
- **Container com servidor SSH** — rápido. Contra: sem systemd, as regras de serviço perdem o
  sentido.

## Decisão
VM Ubuntu no GCP, criada, preparada e destruída por scripts `gcloud` versionados junto da
entrega, nunca pelo console. O que pesou foi reprodutibilidade da evidência: quem ler a entrega
precisa saber exatamente como o host foi montado, e o script é essa prova.

O script também fixa a postura de segurança do laboratório, porque o estado "com desvios" é
propositalmente inseguro:

- rede própria, sem as regras de firewall padrão da rede `default` (que abrem SSH para
  qualquer origem), com entrada permitida só na porta 22 e só a partir do IP do operador;
- VM sem conta de serviço, para que um comprometimento da VM não vire acesso ao projeto;
- chaves SSH do projeto bloqueadas na VM, para que nenhuma chave de fora entre no host entre
  duas execuções;
- usuário de coleta criado com `useradd`, fora do mecanismo de chaves por metadata do GCP, com
  chave dedicada e descartável, e `id` registrado na evidência *(premissa — confirme ou
  corrija: usuários criados por metadata entram, pela documentação conhecida, em grupo de sudo
  sem senha, o que contradiz a coleta com usuário comum)*;
- o host é colocado alternadamente em estado sem desvio e com desvios **fora** da ferramenta.

## Consequências
- **Positivas:** evidência contra um host real e reproduzível; o estado sem desvio × com
  desvios é preparado por script, então a ferramenta nunca precisa escrever no host; o
  laboratório inseguro de propósito não fica exposto à internet além da porta 22 do operador.
- **Negativas:** custo em nuvem enquanto a VM existir, e dependência de destruí-la ao final; no
  GCP o IP externo é traduzido (NAT 1:1) e não aparece na interface da VM — "bind público" só se
  reproduz com bind em todos os endereços (`0.0.0.0`, `::`), e um bind no IP interno pode ser
  alcançável de fora se o firewall permitir, que é justamente o limite declarado no PRD
  (Restrições); a imagem traz o agente do provedor (guest agent), e acesso administrativo entre
  duas execuções pode injetar chave e quebrar a prova de repetição, então só acontece nas
  etapas de preparação; a evidência publicada carrega IP, fingerprint e comentários de chave e
  precisa usar valores sintéticos e ser revisada antes de publicar.
- **Neutras / trade-offs aceitos:** o laboratório é infraestrutura de validação, não parte do
  comportamento da ferramenta (PRD, Fora do escopo); ele não tem PRD próprio.
