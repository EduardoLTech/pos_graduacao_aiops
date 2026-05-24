# Context Window Content

## User Prompt 1

#Context
Na empresa todos os modulos do Terraform para AWS precisam seguir um padrao de construcao. é utilizado o terraform-aws-modules como referencia. Os ambientes são separados em dev, staging e production. Convencao de naming: kebab-case para recursos, snake_case para variaveis.

#Action
Crie um modulo Terraform reutilizavel para criacao de bucket S3 com as seguintes definicioes:
Tags obrigatórias em todo recurso: Owner, CostCenter, Environment.
Prefixo hvt- nos nomes de recursos.
Todo bucket S3 com: encryption habilitada (SSE-S3 mínimo), versioning ativo, block public access total, logging configurado.
Variáveis de entrada em variables.tf com description e type obrigatórios.

#Result
O modulo deve conter: main.tf, variables.tf com descrições e validações, outputs.tf com ARN e nome do bucket, e um README_S3.md com exemplo de uso. Os arquivos ficarão em exercicio06.

#Exemple
Para sua referencia, siga o exemplo de construcao do modulo VPC:
variable "environment" {
  description = "Nome do ambiente (dev, staging, production)"
  type        = string
}

locals {
  common_tags = {
    Owner       = var.owner
    CostCenter  = var.cost_center
    Environment = var.environment
  }
}

resource "aws_vpc" "this" {
  cidr_block = var.cidr_block
  tags = merge(local.common_tags, {
    Name = "hvt-vpc-${var.environment}"
  })
}

## Model Response 1

Módulo criado com sucesso com os seguintes arquivos em `exercicio06/`:

**variables.tf** — 11 variáveis com `type`, `description` e bloco `validation`:
- Tags obrigatórias: `owner`, `cost_center`, `environment` (com validação de formato CC-\<número\> e valores aceitos de environment)
- Identificação: `bucket_name` (validação de kebab-case)
- Criptografia: `sse_algorithm` (`AES256` padrão, `aws:kms` opcional) e `kms_master_key_id`
- Logging: `logging_target_bucket` (obrigatório), `logging_target_prefix`
- Lifecycle: `noncurrent_version_expiration_days` (padrão 90)
- Extras: `additional_tags`

**main.tf** — 6 recursos AWS como sub-recursos separados (padrão AWS provider v5):
- `aws_s3_bucket` — bucket principal com naming `hvt-<bucket_name>-<environment>`
- `aws_s3_bucket_public_access_block` — todos os 4 blocos = `true`
- `aws_s3_bucket_versioning` — habilitado por padrão
- `aws_s3_bucket_server_side_encryption_configuration` — SSE-S3 por padrão, SSE-KMS opcional
- `aws_s3_bucket_logging` — logs enviados ao bucket de destino informado
- `aws_s3_bucket_lifecycle_configuration` — expiração de versões não-correntes e multipart incompleto

**outputs.tf** — 7 outputs: `bucket_name`, `bucket_arn`, `bucket_domain_name`, `bucket_regional_domain_name`, `bucket_region`, `versioning_status`, `encryption_algorithm`

**README_S3.md** — documentação completa com tabela de variáveis/outputs, 3 exemplos de uso (dev, produção com KMS, consumo de outputs) e checklist de conformidade com políticas internas.

Decisões técnicas relevantes:
- Tags com precedência garantida via `merge(var.additional_tags, local.common_tags)` — tags obrigatórias sempre sobrescrevem chaves duplicadas
- `bucket_key_enabled = true` habilitado automaticamente com SSE-KMS (reduz chamadas KMS em até 99%)
- Lifecycle criado com `count` — só provisionado se `noncurrent_version_expiration_days > 0`


