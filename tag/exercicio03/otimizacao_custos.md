# Relatório de Otimização de Custos Cloud

Este relatório apresenta uma análise detalhada dos custos e utilização dos recursos de nuvem com base nos dados fornecidos, propondo um plano estruturado para atingir a meta de **15% de redução de custo mensal** ($6.270,00 USD) sem comprometer os SLAs de produção.

---

## 📊 Panorama Geral e Metas

*   **Custo Mensal Atual:** $41.800,00 USD
*   **Meta de Redução (15%):** -$6.270,00 USD (Novo teto: $35.530,00 USD)
*   **Potencial de Economia Identificado:** **$10.670,00 USD (~25,5% da fatura)**

---

## 🎯 Decisões de Alinhamento (Confirmadas)

Após alinhamento com a liderança técnica, as seguintes premissas foram validadas e incorporadas ao plano de otimização:
1.  **Sem restrições de compliance para Logs:** Foi confirmado que não existem impedimentos legais ou regulatórios para a redução do tempo de retenção padrão do CloudWatch Logs para 14 ou 30 dias.
2.  **Estabilidade para Reservas (RIs):** A arquitetura e o dimensionamento das tecnologias de banco de dados (RDS PostgreSQL e ElastiCache Redis) em produção estão estáveis e maduros o suficiente para a compra de reservas de 1 ano.
3.  **Janela de Ociosidade aos Finais de Semana:** Está autorizado o desligamento completo de workloads de desenvolvimento/homologação (tanto nós de EKS quanto instâncias EC2 on-demand de Dev/Staging) aos finais de semana, maximizando a economia.

---

## 📈 Tabela Comparativa de Recomendações (Priorizada por Impacto)

| Prioridade | Serviço | Ação Recomendada | Economia Mensal Est. (USD) | % da Fatura Total | Esforço | Risco / Pré-requisito |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **1** | **EC2 on-demand** | Right-sizing e Auto Scaling (desligar Dev/Staging aos finais de semana e noites) | **$2.870,00** | 6,87% | Médio | **Baixo**: Requer mapeamento de janelas de uso. |
| **2** | **RDS PostgreSQL** | Compra de Reserved Instances (RI) de 1 ano + Desativar Multi-AZ em Dev/Staging | **$2.050,00** | 4,90% | Baixo | **Baixo**: Compromisso de 1 ano; sem risco técnico. |
| **3** | **EKS** | Autoscaling agressivo (Karpenter) + Nós Spot para Dev/Staging + Consolidar Clusters | **$1.675,00** | 4,01% | Médio-Alto | **Médio**: Risco de interrupção em Dev/Staging (tolerável). |
| **4** | **CloudWatch Logs** | Reduzir retenção para 14/30 dias + Ajustar verbosidade de logs (DEBUG -> WARN) | **$1.120,00** | 2,68% | Baixo | **Baixo**: Já alinhado com equipe de compliance. |
| **5** | **S3 Standard** | Implementar Lifecycle Policies (mover para Intelligent-Tiering ou Glacier Instant) | **$1.085,00** | 2,60% | Baixo | **Baixo**: Risco quase nulo se configurado corretamente. |
| **6** | **ElastiCache Redis** | Right-sizing do cluster prod + Compra de RI de 1 ano | **$630,00** | 1,51% | Baixo | **Baixo**: Pequeno downtime se redimensionar sem cluster mode. |
| **7** | **Data Transfer Out** | Consolidar recursos em mesma região + Usar CloudFront (CDN) para tráfego externo | **$380,00** | 0,91% | Médio-Alto | **Médio**: Envolve migração de recursos ou alteração de DNS. |
| **8** | **NAT Gateway** | Criar VPC Gateway Endpoints p/ S3 e DynamoDB + Remover NAT redundante em Dev | **$360,00** | 0,86% | Médio | **Baixo**: Requer ajustes em tabelas de roteamento VPC. |
| **9** | **CloudWatch Metrics**| Revisar e desativar métricas customizadas de alta cardinalidade | **$180,00** | 0,43% | Baixo | **Baixo**: Risco de perder alertas não utilizados. |
| **10** | **Lambda** | Migrar para arquitetura Graviton2 (ARM64) + Power Tuning | **$180,00** | 0,43% | Baixo | **Baixo**: Testar compatibilidade de binários/bibliotecas. |
| **11** | **EBS gp3** | Deletar volumes órfãos e snapshots antigos e sem uso | **$160,00** | 0,38% | Baixo | **Baixo**: Risco de apagar dado legado. Fazer backup antes. |
| **-** | **EC2 reservada** | Otimizar alocação atual (garantir uso de 100% das reservas contratadas) | **$0,00** | - | Baixo | **Baixo**: Ajustar tipos de instâncias em execução. |
| **Total** | | | **$10.670,00** | **25,53%** | | |

---

## 🔍 Detalhamento das Recomendações

### 1. EC2 On-Demand (Custo: $8.200,00 | Uso médio: 45%)
*   **Diagnóstico:** A utilização média de 45% indica que as instâncias estão severamente superdimensionadas (over-provisioned) ou ativas sem necessidade durante períodos ociosos.
*   **Ações Recomendadas:**
    1.  **Right-sizing:** Reduzir o tamanho das instâncias (ex: de `m5.xlarge` para `m5.large`) onde o pico de CPU/Memória não ultrapassa 50%.
    2.  **Auto Scaling & Schedule:** Implementar políticas de escalonamento automático e agendamento para desligar instâncias de desenvolvimento/homologação fora do horário comercial (ex: 20h às 08h e finais de semana). Isso reduz o tempo de execução dessas instâncias em mais de 60%.
    3.  **Spot Instances:** Migrar workloads de testes/batch que tolerem interrupções para instâncias Spot (desconto de até 90%).
*   **Economia Estimada:** **$2.870,00 (35% de redução na categoria)**
*   **Risco/Pré-requisitos:** Analisar os perfis de CPU/Memória por pelo menos 14 dias antes de realizar o right-sizing. Garantir que os scripts de startup das aplicações estejam preparados para reinicializações automáticas.

### 2. RDS PostgreSQL (Custo: $8.200,00 | Uso médio: 62%)
*   **Diagnóstico:** Custo elevado devido ao uso de Multi-AZ. A utilização de 62% sugere estabilidade, mas permite otimização comercial e de arquitetura.
*   **Ações Recomendadas:**
    1.  **Instâncias Reservadas (RI):** Adquirir reservas de 1 ano (No Upfront ou Partial Upfront) para as instâncias de banco de dados de produção. Isso gera um desconto imediato de ~30% a 35%.
    2.  **Desativação de Multi-AZ em Não-Produção:** Garantir que ambientes de Dev e Staging não utilizem Multi-AZ (Single-AZ economiza 50% do custo da instância).
*   **Economia Estimada:** **$2.050,00 (25% de redução na categoria)**
*   **Risco/Pré-requisitos:** A compra de RIs requer a certeza de que a tecnologia de banco de dados (PostgreSQL) e o tamanho da instância não mudarão no próximo ano.

### 3. EKS (Custo: $6.700,00 | Uso médio: 58%)
*   **Diagnóstico:** 3 clusters ativos com média de uso de 58% indicam espaço para consolidação e escalonamento mais eficiente.
*   **Ações Recomendadas:**
    1.  **Consolidação de Clusters:** Avaliar a fusão dos clusters de Dev e Staging em um único cluster utilizando Namespaces para isolamento lógico e Network Policies para segurança. Isso economiza a taxa fixa de gerenciamento do cluster ($0,10/hora por cluster) e reduz o overhead de nós de gerenciamento.
    2.  **Karpenter:** Substituir o Cluster Autoscaler clássico pelo Karpenter, que provisiona nós de tamanhos ideais dinamicamente e consolida workloads em menos nós.
    3.  **Nós Spot para Dev/Staging:** Configurar os Node Groups de Dev e Staging para rodar majoritariamente em instâncias Spot.
*   **Economia Estimada:** **$1.675,00 (25% de redução na categoria)**
*   **Risco/Pré-requisitos:** Implementar orquestração de tolerância a falhas (ex: node taints, tolerations e pod disruption budgets) para suportar a substituição de nós Spot sem indisponibilidade em Dev/Staging.

### 4. CloudWatch Logs (Custo: $2.800,00)
*   **Diagnóstico:** Custos elevados de observabilidade são comuns devido ao envio excessivo de logs e longos períodos de retenção.
*   **Ações Recomendadas:**
    1.  **Redução da Retenção:** Alterar a retenção padrão de 90 dias para 14 ou 30 dias. Para logs que necessitam de retenção de longo prazo por compliance, configurar uma política para exportá-los automaticamente para o S3 Glacier (muito mais barato que manter no CloudWatch).
    2.  **Filtro de Verbose e Níveis de Log:** Ajustar o nível de log padrão das aplicações de produção (ex: desativar logs de INFO genéricos ou DEBUG, focando apenas em WARNING/ERROR/CRITICAL).
*   **Economia Estimada:** **$1.120,00 (40% de redução na categoria)**
*   **Risco/Pré-requisitos:** Alinhar com a equipe de segurança e compliance os novos prazos de retenção antes de aplicar a alteração.

### 5. S3 Standard (Custo: $3.100,00)
*   **Diagnóstico:** Uso de armazenamento padrão (Standard) para todos os dados, inclusive os históricos que raramente são acessados.
*   **Ações Recomendadas:**
    1.  **Lifecycle Policies (Políticas de Ciclo de Vida):** Criar regras para mover objetos não modificados após 30 dias para S3 Standard-IA (Infrequent Access) ou Glacier Instant Retrieval.
    2.  **S3 Intelligent-Tiering:** Para buckets onde o padrão de acesso é imprevisível, habilitar o Intelligent-Tiering para que a própria AWS gerencie a movimentação de camadas de forma automática e sem custos de recuperação.
*   **Economia Estimada:** **$1.085,00 (35% de redução na categoria)**
*   **Risco/Pré-requisitos:** Atentar para a taxa de recuperação do S3 IA. Se os arquivos forem lidos com frequência, a cobrança de recuperação pode anular a economia de armazenamento.

### 6. ElastiCache Redis (Custo: $2.100,00 | Uso médio: 40%)
*   **Diagnóstico:** Cluster de produção operando com apenas 40% de utilização.
*   **Ações Recomendadas:**
    1.  **Right-sizing:** Reduzir o tipo de instância dos nós para um tamanho menor (ex: cache.r6g.large para cache.r6g.medium).
    2.  **Reserved Nodes:** Comprar reserva de 1 ano para o cluster de produção ativo.
*   **Economia Estimada:** **$630,00 (30% de redução na categoria)**
*   **Risco/Pré-requisitos:** Monitorar o pico de uso de memória e CPU do Redis. O Redis armazena dados em memória RAM, portanto o right-sizing deve focar principalmente na capacidade de memória disponível.

### 7. NAT Gateway & Data Transfer Out (Custo Combinado: $3.100,00)
*   **Diagnóstico:** Custos elevados de rede geralmente são decorrentes de tráfego inter-regional e tráfego direcionado para serviços AWS (como S3 e CloudWatch) passando por NAT Gateways pagos.
*   **Ações Recomendadas:**
    1.  **VPC Gateway Endpoints:** Criar Gateway Endpoints gratuitos para S3 e DynamoDB na VPC. Isso fará com que todo o tráfego do EKS/EC2 para o S3 trafegue de forma interna e gratuita, contornando o custo por GB processado pelo NAT Gateway.
    2.  **Consolidação Regional:** Evitar tráfego de saída entre diferentes regiões (Data Transfer Out inter-region). Onde possível, consolide as aplicações e bancos de dados na mesma região AWS.
*   **Economia Estimada:** **$740,00 (NAT Gateway: $360.00 | Data Transfer: $380.00)**
*   **Risco/Pré-requisitos:** Ajustes em tabelas de roteamento de rede durante janelas de manutenção para evitar breves instabilidades de conectividade.

---

## 📅 Plano de Ação Recomendado (Fases)

Para atingir e superar a meta de **15%** com o menor esforço e risco possíveis, sugere-se a divisão em 3 fases:

### 🚀 Fase 1: Rápida Implementação (Ganho Rápido / Baixo Risco)
*   **Ações:**
    *   Implementar VPC Gateway Endpoints para S3.
    *   Aplicar Lifecycle Policies no S3 Standard.
    *   Reduzir a retenção dos logs do CloudWatch para 30 dias.
    *   Limpar volumes EBS órfãos.
*   **Esforço:** Baixo (1-3 dias)
*   **Economia Estimada:** **~$2.725,00/mês (~6,5% de redução)**

### ⚙️ Fase 2: Ajustes Comerciais e de Infraestrutura (Impacto Médio)
*   **Ações:**
    *   Adquirir Reserved Instances para RDS PostgreSQL (Prod) e ElastiCache Redis.
    *   Desativar Multi-AZ nos RDS de Dev/Staging.
    *   Aplicar Right-sizing nas instâncias EC2 On-Demand e habilitar o Auto Scaling Scheduler para desligar Dev/Staging à noite e aos fins de semana.
*   **Esforço:** Médio (1-2 semanas de análise + execução)
*   **Economia Estimada Adicional:** **~$4.400,00/mês (~10,5% de redução)**
*   *Nota: Ao concluir a Fase 2, a meta de 15% já terá sido superada (totalizando ~17%).*

### 🛠️ Fase 3: Otimização Avançada (Alto Impacto / Médio Risco)
*   **Ações:**
    *   Implementar Karpenter no EKS com instâncias Spot para Dev/Staging.
    *   Migrar Lambdas para Graviton2 (ARM64).
    *   Analisar e mitigar o Data Transfer Out inter-regional.
*   **Esforço:** Médio-Alto (2-4 semanas de engenharia)
*   **Economia Estimada Adicional:** **~$3.545,00/mês (~8,5% de redução)**
