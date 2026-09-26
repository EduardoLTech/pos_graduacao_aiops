Já tenho a causa. A tag publicada não existe no registry, então o pod nunca consegue baixar a imagem.

# Triagem: orion-stg/orion-web (fake-shop)

**Sintoma declarado:** depois da publicação do Loom, o deploy foi aplicado mas o pod nunca trocou e a loja parou.
**Camada da causa:** imagem/registry.

**Causa:** o Deployment pede a imagem `fabricioveronez/fake-shop:v1.14.2`, e essa tag não existe no Docker Hub. O kubelet não consegue baixá-la, e os 3 pods ficam presos em `ImagePullBackOff` sem nunca iniciar o container.

**Evidência:**
- **Estado:** os pods `orion-web-7bbfd5df6b-{2mcn4,6jl89,b2ftn}` estão com `state.waiting.reason: ImagePullBackOff` e `Restart Count: 0`. O evento do kubelet diz: `failed to resolve reference "docker.io/fabricioveronez/fake-shop:v1.14.2": not found` (`code = NotFound`, 4 tentativas).
- **Spec:** o Deployment `orion-web` usa `image: fabricioveronez/fake-shop:v1.14.2`. As conditions mostram `Available=False` (`MinimumReplicasUnavailable`) e `unavailableReplicas: 3`.
- O `NotFound` descarta falta de credencial (isso daria `unauthorized`/`denied`) e falha de rede (daria timeout). O registry respondeu, só que a tag não está lá. Na prática, o release anunciou uma tag que nunca foi publicada, ou foi publicada com outro nome.

**Por que "o pod nunca trocou":** o Deployment está na revisão 1 (`generation: 1`) e tem um único ReplicaSet (`orion-web-7bbfd5df6b`, 0/3 prontos). Não existe ReplicaSet de uma versão anterior no cluster. O objeto foi criado do zero às 23:18 com a tag nova. Então não sobrou nenhuma versão antiga rodando para segurar o tráfego, e a loja ficou sem nenhum pod pronto.

**Funciona ao lado:** `orion-postgres` está 1/1 pronto, com endereço `10.244.0.35:5432` no EndpointSlice. Isso descarta o nó, a rede do namespace e o banco.

**Correção sugerida (não apliquei nada):** ter essa correção nas mãos de um humano, por um de dois caminhos:
- publicar `fabricioveronez/fake-shop:v1.14.2` no Docker Hub;
- ou apontar `spec.template.spec.containers[web].image` do Deployment `orion-web` para uma tag que exista, e acertar o release do Loom para a tag real.

Em qualquer caso, vale o pipeline de release conferir se a tag existe no registry antes de anunciar ou aplicar.

**Achados laterais:**
- Fora do padrão da casa: `DB_PASSWORD` está em texto puro no Deployment e na annotation `last-applied-configuration`; não há `resources`, probes nem `securityContext` (QoS `BestEffort`).
- Sem ReplicaSet antigo, não há como voltar para a versão anterior com `rollout undo`.

**Não verifiquei:**
- Quais tags do fake-shop existem de fato no Docker Hub. A triagem só lê o cluster, então não sei qual seria a tag certa.
- Na saída `wide`, o EndpointSlice de `orion-web` lista os 3 IPs, mas não mostra o campo `ready` de cada endereço. Com o container sem subir, eles devem estar `ready: false`, só que não li isso.

**Caminho seguido:** `kubectl_get` de deployments e pods → `kubectl_get` do Deployment `orion-web` (yaml) → `kubectl_get` de replicasets → `kubectl_describe` do pod `orion-web-7bbfd5df6b-2mcn4` → `kubectl_get` de endpointslices.
