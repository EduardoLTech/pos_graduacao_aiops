A causa é um erro de digitação no seletor do Service: ele procura pods com `app: nyx-api`, mas os pods do kube-news têm o rótulo `app: nyxapi`, sem hífen. Os pods estão de pé, mas nenhum casa o seletor, então o Service fica sem endereço e quem chama de fora recebe 503. Não alterei nada no cluster; só li.

# Triagem — nyx-stg/nyx-api (kube-news)
**Sintoma declarado:** 503 para quem chama de fora; a aplicação parece estar de pé.
**Camada da causa:** tráfego.
**Causa:** o seletor do Service `nyx-api` não casa o rótulo dos pods do Deployment `nyx-api`.

**Evidência:**
- **Estado:** o EndpointSlice `nyx-api-7pqvd` está com `endpoints: null` e `ports: null`, ou seja, nenhum pod pronto está atrás do Service. Buscar pods com `app=nyx-api` não retorna nenhum.
- **Spec:**
  - Service `nyx-api`: `selector: app: nyx-api`
  - Deployment `nyx-api`: `template.metadata.labels: app: nyxapi`, e o pod `nyx-api-747898c48b-9pn65` também tem `app: nyxapi`

**A aplicação está de pé mesmo:** o Deployment tem `readyReplicas: 2`, os dois pods estão 1/1 Running com `Ready=True`, e a porta confere (`targetPort: 8080` = `containerPort: 8080`). O problema é só o rótulo.

**Funciona ao lado:** o `nyx-postgres`, no mesmo namespace e no mesmo nó, está pronto. O EndpointSlice dele (`nyx-postgres-28fph`) tem o endereço `10.244.0.34` e o seletor casa (`app: nyx-postgres`). Isso descarta problema no nó, na rede do namespace ou no banco.

**Correção sugerida (não aplicada):** trocar o seletor do Service `nyx-api` para `app: nyxapi`. É a mudança menor e não reinicia os pods. A outra opção é renomear o rótulo para `nyx-api` no Deployment, mas o `selector.matchLabels` de um Deployment não pode ser alterado depois de criado. Para isso, é preciso recriar o Deployment.

**Achados laterais:**
- Os pods reiniciaram 2 e 3 vezes logo depois de subir. O último erro foi `exitCode: 1` em cerca de 1s, às 23:18:24–25. Provavelmente o Postgres ainda não aceitava conexão. Hoje os pods estão estáveis e prontos, então isso não explica o 503.
- A senha do banco (`DB_PASSWORD` / `POSTGRES_PASSWORD`) está em texto puro no `env` dos dois Deployments. O certo é guardá-la num Secret.
- Nenhum container tem `resources` definido.

**Não verificado:**
- O caminho de fora até o Service (Ingress ou Gateway): não listei esses objetos. Depois de corrigir o seletor, se o 503 continuar, a próxima leitura é o Ingress do nyx-stg.
- Os logs das reinicializações.

**Caminho:** get services → get pods wide → get service nyx-api yaml → get endpointslices yaml → get pod 9pn65 yaml → get deployments yaml → get pods com `app=nyx-api`.
