# README_S3.md – Módulo Terraform: HVT S3 Bucket

## Visão Geral

Módulo reutilizável para provisionamento de buckets S3 na AWS seguindo os **padrões internos HVT**.
Toda bucket criada por este módulo obrigatoriamente inclui:

| Controle | Detalhe |
|---|---|
| **Naming** | Prefixo `hvt-` + nome lógico + ambiente (kebab-case) |
| **Block Public Access** | Todos os 4 blocos habilitados |
| **Criptografia SSE** | SSE-S3 (`AES256`) por padrão; SSE-KMS opcional |
| **Versionamento** | Habilitado por padrão |
| **Logging** | Logs de acesso enviados a bucket dedicado |
| **Lifecycle** | Expiração automática de versões não-correntes |
| **Tags obrigatórias** | `Owner`, `CostCenter`, `Environment` |

---

## Estrutura do módulo

```
exercicio06/
├── main.tf        # Recursos AWS
├── variables.tf   # Variáveis de entrada com validações
├── outputs.tf     # Saídas do módulo
└── README_S3.md   # Este arquivo
```

---

## Pré-requisitos

- Terraform **>= 1.5.0**
- Provider **hashicorp/aws >= 5.0**
- Um bucket S3 dedicado para receber os **logs de acesso** deve existir previamente.

---

## Variáveis

| Variável | Tipo | Obrigatória | Padrão | Descrição |
|---|---|---|---|---|
| `owner` | `string` | ✅ | — | Responsável pelo recurso (ex.: `squad-platform`) |
| `cost_center` | `string` | ✅ | — | Centro de custo no formato `CC-<número>` |
| `environment` | `string` | ✅ | — | Ambiente: `dev`, `staging` ou `production` |
| `bucket_name` | `string` | ✅ | — | Nome lógico do bucket (kebab-case, sem prefixo/ambiente) |
| `logging_target_bucket` | `string` | ✅ | — | Nome do bucket de logs de acesso pré-existente |
| `sse_algorithm` | `string` | ❌ | `AES256` | Algoritmo SSE: `AES256` ou `aws:kms` |
| `kms_master_key_id` | `string` | ❌ | `null` | ARN/ID da chave KMS (necessário apenas para `aws:kms`) |
| `logging_target_prefix` | `string` | ❌ | `logs/<bucket>/` | Prefixo de destino nos logs |
| `versioning_enabled` | `bool` | ❌ | `true` | Habilita/suspende o versionamento |
| `noncurrent_version_expiration_days` | `number` | ❌ | `90` | Dias até expirar versões não-correntes (`0` = desativado) |
| `additional_tags` | `map(string)` | ❌ | `{}` | Tags adicionais (mescladas às obrigatórias) |

---

## Outputs

| Output | Descrição |
|---|---|
| `bucket_name` | Nome completo do bucket criado |
| `bucket_arn` | ARN do bucket (para políticas IAM) |
| `bucket_domain_name` | Endpoint S3 global |
| `bucket_regional_domain_name` | Endpoint S3 regional (preferencial) |
| `bucket_region` | Região AWS do bucket |
| `versioning_status` | Status do versionamento |
| `encryption_algorithm` | Algoritmo SSE configurado |

---

## Exemplos de uso

### 1 – Ambiente de desenvolvimento (SSE-S3, configuração mínima)

```hcl
module "s3_raw_data_dev" {
  source = "../../modules/s3"   # ajuste ao caminho real do módulo

  # Identificação
  bucket_name = "raw-data"
  environment = "dev"

  # Tags obrigatórias
  owner       = "squad-data"
  cost_center = "CC-4201"

  # Logging (bucket deve existir previamente)
  logging_target_bucket = "hvt-logs-central-dev"
}
```

**Nome gerado:** `hvt-raw-data-dev`

---

### 2 – Ambiente de produção com SSE-KMS e tags adicionais

```hcl
module "s3_app_artifacts_prod" {
  source = "../../modules/s3"

  # Identificação
  bucket_name = "app-artifacts"
  environment = "production"

  # Tags obrigatórias
  owner       = "squad-platform"
  cost_center = "CC-1001"

  # SSE-KMS com chave gerenciada pelo cliente
  sse_algorithm     = "aws:kms"
  kms_master_key_id = "arn:aws:kms:us-east-1:123456789012:key/abcd1234-ab12-cd34-ef56-abcdef123456"

  # Logging
  logging_target_bucket = "hvt-logs-central-production"
  logging_target_prefix = "logs/app-artifacts/prod/"

  # Lifecycle mais conservador em produção
  noncurrent_version_expiration_days = 365

  # Tags extras
  additional_tags = {
    Project     = "phoenix"
    Criticality = "high"
  }
}
```

**Nome gerado:** `hvt-app-artifacts-production`

---

### 3 – Consumindo os outputs em outro módulo

```hcl
# Referência ao bucket criado pelo módulo
resource "aws_iam_policy" "app_s3_access" {
  name = "hvt-app-s3-access-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${module.s3_app_artifacts_prod.bucket_arn}/*"
      }
    ]
  })
}

output "artifacts_bucket_name" {
  value = module.s3_app_artifacts_prod.bucket_name
}
```

---

## Convenções adotadas

| Regra | Detalhe |
|---|---|
| **Naming de recursos** | kebab-case com prefixo `hvt-` |
| **Naming de variáveis** | snake_case |
| **Tags obrigatórias** | `Owner`, `CostCenter`, `Environment` |
| **Recurso lógico** | Sempre nomeado `this` (padrão `terraform-aws-modules`) |
| **Segurança** | Nenhuma ACL ou política pública permitida |

---

## Conformidade com políticas internas

- ✅ `block_public_acls = true`
- ✅ `block_public_policy = true`
- ✅ `ignore_public_acls = true`
- ✅ `restrict_public_buckets = true`
- ✅ Criptografia SSE habilitada (mínimo SSE-S3)
- ✅ Versionamento ativo por padrão
- ✅ Logging de acesso configurado
- ✅ Tags obrigatórias aplicadas via `merge()` com precedência garantida
