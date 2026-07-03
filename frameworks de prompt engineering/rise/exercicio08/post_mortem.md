# Incident Post-Mortem: Instabilidade Chronos API (v2.48.0)
**Classificação**: SEV1 (Severidade Alta - Impacto Crítico no Negócio)  
**Data**: 24 de Abril de 2026  
**Autor**: SRE Principal / Líder de Resposta a Incidentes  

---

## 1. Sumário Executivo

Em 24 de abril de 2026, durante o pico de tráfego diário (~14:00 UTC), a aplicação **chronos-api** apresentou severa degradação de performance, com a latência de p99 atingindo **8100ms** (comparado à linha de base de 420ms) e a taxa de erros alcançando **11.7%**. A fila de transações assíncronas (**chronos-transactions** no Reactor) acumulou mais de **50.000 mensagens**, com um consumer lag crescente de **18 minutos**.

O gatilho do incidente foi o deploy da versão **v2.48.0** realizado no dia anterior (23/04/2026 às 18:42:11 UTC). A análise técnica revelou que a refatoração do pool de conexões do Ledger e o novo endpoint de batch saturaram as conexões do banco de dados PostgreSQL (RDS), esgotando os pools individuais dos pods e levando a timeouts em cascata.

Após avaliar os riscos entre scaling vertical emergencial do banco de dados e rollback da aplicação, optou-se pelo **rollback imediato para a versão v2.47.0**. A mitigação foi bem-sucedida, restabelecendo a latência do sistema para níveis normais e permitindo a drenagem segura das filas.

---

## 2. Linha do Tempo (Timeline)

| Timestamp (UTC) | Evento / Métrica | Detalhes / Observações |
| :--- | :--- | :--- |
| **2026-04-23 18:42:11** | **Deploy v2.48.0** | Sincronização automática via Argo CD finalizada com sucesso. |
| **2026-04-24 13:30** | Início do Pico / Estabilidade | Latência p99: 420ms \| Tráfego: 1200 rps \| Erros: 0.2%. |
| **2026-04-24 13:45** | Aumento de Tráfego | Latência p99: 510ms \| Tráfego: 1450 rps \| Erros: 0.3%. |
| **2026-04-24 14:00** | Primeiros Sintomas | Latência p99: 780ms \| Tráfego: 1780 rps \| Erros: 0.8%. *HPA inicia escalonamento dos pods.* |
| **2026-04-24 14:10** | Degradação Severa | Latência p99: 2400ms \| Tráfego: 2100 rps \| Erros: 4.5%. *HPA atinge o teto de 12 pods.* |
| **2026-04-24 14:15** | Alertas de SEV1 | Latência p99: 5200ms \| Tráfego: 2400 rps \| Erros: 8.2%. *Circuit Breaker do ledger-client começa a abrir.* |
| **2026-04-24 14:20** | Pico do Incidente | Latência p99: 8100ms \| Tráfego: 2650 rps \| Erros: 11.7%. *Lag da fila atinge 18 minutos e 50k msgs.* |
| **2026-04-24 14:25** | Resposta a Incidentes | Início da análise de logs, métricas e tomada de decisão de engenharia. |
| **2026-04-24 14:35** | Mitigação Aplicada | Execução do rollback via Argo CD para a versão v2.47.0. |
| **2026-04-24 14:45** | Estabilização | Latência p99 recua para <500ms. Consumo de mensagens na fila chronos-transactions normalizado. |

---

## 3. Análise Técnica Detalhada

### 3.1. O Efeito Gargalo e a Saturação das Conexões
A análise detalhada do estado do cluster e do RDS revelou um gargalo matemático rígido entre o pool de conexões configurado por pod e a capacidade máxima do banco de dados (RDS):

1. **Capacidade do RDS**: O banco de dados do Ledger possui um limite físico/configurado de **250 conexões ativas máximo**.
2. **Dimensionamento do Cluster (chronos-api)**:
   - Durante o incidente, o HPA escalou os pods ao seu limite máximo: **12 pods**.
   - Cada pod executa uma configuração do pool de conexões do `ledger-client` com `max=20` (visto no log: `connection pool exhausted (max=20, active=20...)`).
3. **Cálculo da Pressão Máxima de Conexões**:
   $$\text{Conexões Máximas Teóricas} = 12 \text{ pods} \times 20 \text{ conexões/pod} = 240 \text{ conexões}$$
4. **Estado de Ocupação**: As métricas de monitoramento reportaram **240/250 conexões ativas no RDS**.

**Conclusão**: O cluster consumiu 96% das conexões disponíveis do RDS do Ledger. A aplicação entrou em um estado de starvation (fome) de conexões. Qualquer nova tentativa de obter conexões resultava em requisições presas aguardando a liberação do pool (`waiting=147`), estourando o timeout configurado de **2 segundos** (`query timeout after 2000ms`).

### 3.2. A Origem da Alta Latência (8100ms vs. Timeout de 2s)
Uma dúvida comum em incidentes dessa natureza é: *Se o timeout do Ledger foi reduzido de 5s para 2s na v2.48.0, por que a latência de p99 reportada pelo Beacon foi de 8100ms?*

O motivo reside na diferença entre **Query Execution Timeout** e **Connection Acquisition Timeout**:
- A query no banco de dados é limitada a 2s (`query timeout after 2000ms`).
- No entanto, antes da query ser executada, a thread/processo da aplicação precisa adquirir uma conexão livre do pool.
- Devido à saturação (`waiting=147`), as requisições passaram a maior parte do seu ciclo de vida bloqueadas na fila do pool de conexões. Esse tempo de espera em fila interna da aplicação somou-se ao tempo de execução, resultando em latências ponta-a-ponta elevadas (p99 de 8.1s) até que ocorresse o timeout do contexto HTTP principal ou do gateway upstream.

### 3.3. Análise de Causa Raiz (Gatilhos do Deploy v2.48.0)
Quatro alterações introduzidas no deploy da versão v2.48.0 causaram o incidente de forma combinada:
1. **Endpoint `POST /v2/transactions/batch`**: Operações em lote tendem a reter conexões por muito mais tempo (iniciando transações longas, processando múltiplos inserts/updates), aumentando drasticamente a concorrência e a taxa de ocupação das conexões do pool.
2. **Refatoração do cliente do Ledger (nova biblioteca interna)**: A migração do pool de conexões para uma nova biblioteca interna é um forte indicador de um **vazamento de conexão (connection leak)** (ex: conexões não retornando ao pool após falhas ou transações não confirmadas/abortadas corretamente).
3. **Upgrade do driver: psycopg 3.1.18 -> 3.2.0**: Mudanças nas bibliotecas de banco de dados podem introduzir diferenças sutis na forma como conexões implícitas são gerenciadas, prepare statements são gerados ou transações são abertas por padrão.
4. **Redução do timeout de 5s para 2s**: Embora projetado para "falhar rápido", sem um tratamento adequado e um circuit breaker bem dimensionado, causou a falha abrupta de requisições que poderiam ter completado se tivessem mais 1 ou 2 segundos, amplificando a taxa de erro (`err_rate_pct` de 11.7%) e abrindo o Circuit Breaker precocemente (`ledger-client OPEN`).

---

## 4. Avaliação de Opções: Rollback vs. Scaling Emergencial

No ápice do incidente, duas abordagens de mitigação foram propostas. Abaixo está a matriz de decisão que justificou a escolha:

| Critério de Decisão | Opção A: Scaling Emergencial (RDS + Conexões) | Opção B: Rollback para v2.47.0 (Escolha SRE) |
| :--- | :--- | :--- |
| **Ações Necessárias** | 1. Alterar tamanho da instância do RDS (Scale Up).<br>2. Aumentar limite de conexões no PostgreSQL (`max_connections`).<br>3. Modificar o ConfigMap para aumentar o `max` pool por pod.<br>4. Escalar horizontalmente os pods da API. | 1. Executar rollback da imagem no Argo CD (v2.48.0 -> v2.47.0).<br>2. Monitorar a queda de conexões e estabilização de latência. |
| **Tempo para Resolução** | **Alto (15 a 30 minutos)**. Alteração de classe de instância do RDS exige tempo de provisionamento e reinicialização. | **Baixo (2 a 3 minutos)**. O Argo CD sincroniza a versão anterior quase instantaneamente e o Kubernetes executa um rolling update reverso. |
| **Riscos Associados** | **Altíssimo**. Modificações no RDS em pico de tráfego podem gerar downtime total por falha na transição. Aumentar conexões sem tratar o possível vazamento na biblioteca interna apenas adiaria o esgotamento do banco. | **Mínimo**. Retorno a uma versão estável comprovada em produção nas últimas semanas. O único impacto é a perda temporária do novo endpoint `/v2/transactions/batch`. |
| **Custo de Infraestrutura** | Aumento imediato no custo operacional do RDS na AWS sem comprovação de necessidade real sob código otimizado. | Zero custo adicional. |
| **Eficácia** | Baixa a curto prazo. Trata o sintoma (falta de conexões), mas não resolve a causa raiz (vazamento ou ineficiência do batch). | **Alta**. Remove o código instável, a nova biblioteca de pool e o endpoint batch ineficiente. |

**Decisão do SRE Sênior**: **Rollback imediato para a versão v2.47.0**. 

---

## 5. Plano de Mitigação Imediata (Executado)
A mitigação seguiu os passos detalhados no Runbook operacional:
1. **Desativação temporária do Auto-Sync no Argo CD** para evitar que o GitOps sobrescreva a ação manual.
2. **Rollback manual da imagem** da `chronos-api` para a versão estável anterior `v2.47.0`.
3. **Validação do escoamento do tráfego**: Queda imediata de conexões do Ledger para valores estáveis de baseline (~120 conexões) e latência retornando a ~450ms.
4. **Drenagem do Lag**: Com o tempo de resposta da API reestabelecido, os workers do Reactor processaram com segurança a fila acumulada, normalizando o consumer lag em 15 minutos pós-rollback.

---

## 6. Ações Corretivas e Soluções Definitivas (Pós-Fix)

Para evitar reincidência e garantir que a v2.48.0 (ou uma correção v2.48.1) possa ser implantada com segurança, as seguintes ações estruturais devem ser implementadas:

### 1. Auditoria da Nova Biblioteca de Pool e Driver Psycopg
*   **Problema**: Suspeita de connection leak (vazamento de conexões).
*   **Ação**: Realizar testes locais de perfilamento de memória e conexões para garantir que todos os blocos `try-finally` ou gerenciadores de contexto (`with`) estejam liberando as conexões de volta para o pool, especialmente nos caminhos de exceção (como quando ocorre timeout de 2s).
*   **Prazo**: 3 dias (Desenvolvimento / SRE).

### 2. Otimização do Endpoint `/v2/transactions/batch`
*   **Problema**: Processamento síncrono ou pesado de transações em lote consumindo o pool por períodos prolongados.
*   **Ação**: 
    - Migrar o processamento de batch de síncrono para assíncrono (devolver HTTP `202 Accepted` e enfileirar as transações via Reactor para execução em background pelos workers).
    - Implementar paginação e limites rígidos no payload de batch (ex: máximo de 50 transações por request).
*   **Prazo**: 5 dias (Desenvolvimento).

### 3. Implementação de Arquitetura de Pooling com PgBouncer
*   **Problema**: Conexão direta dos pods ao RDS limita o escalonamento horizontal devido ao teto de 250 conexões.
*   **Ação**: Deploy de uma camada de **PgBouncer** (seja como sidecar ou deployment centralizado) configurada em modo de pool de transação (`pool_mode = transaction`). Isso permitirá que centenas de pods da aplicação se conectem ao PgBouncer, enquanto este multiplexa as conexões reais com o RDS de forma eficiente, limitando as conexões do banco de forma segura.
*   **Prazo**: 7 dias (SRE).

### 4. Ajustes nos Timeouts e Circuit Breakers
*   **Problema**: Timeouts curtos demais sem fallback robusto gerando erros em cascata.
*   **Ação**: Ajustar o Circuit Breaker para retornar uma resposta amigável de erro (degradação graciosa ou leitura de cache) quando o pool estiver exaurido, em vez de deixar a requisição travar em fila. Configurar um timeout de aquisição do pool menor do que o timeout de query (ex: timeout de pegar conexão = 250ms; timeout da query = 2s).

---

## 7. Critérios de Validação Pós-Fix

O deploy da correção da v2.48.0 só será homologado se atender aos seguintes critérios em ambiente de Staging/Performance:

1. **Teste de Carga Estressado**:
   - Simular carga de 3000 req/s (15% acima do pico de produção histórico) por 1 hora.
   - O HPA deve escalar até o máximo de pods configurado.
   - O número de conexões ativas no banco de dados deve permanecer estável (sem crescimento linear indefinido, caracterizando leak).
2. **Taxa de Liberação de Conexões**:
   - Validar que a média de conexões ativas por pod não ultrapasse 70% da capacidade do pool sob carga constante de baseline.
3. **Validação do Endpoint de Batch**:
   - Enviar batches de tamanho máximo (limite estipulado) e monitorar o tempo de retenção da conexão pelo pod. A latência média do batch deve ser inferior a 1s e não deve afetar a latência das transações unitárias (isolamento de pool ou assincronismo).
4. **Verificação de Resiliência (Caos)**:
   - Injetar latência artificial de 3s no banco de dados. Validar se o Circuit Breaker abre corretamente em menos de 10s e se, ao cessar a latência, o pool se recupera e limpa todas as conexões presas sem necessidade de restart de pod.
