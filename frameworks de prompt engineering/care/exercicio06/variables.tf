# ============================================================
# variables.tf – Módulo S3 | Padrão HVT
# ============================================================

# ----------------------------------------------------------
# Tags obrigatórias
# ----------------------------------------------------------

variable "owner" {
  description = "Responsável pelo recurso (ex.: squad-platform). Usado na tag obrigatória Owner."
  type        = string

  validation {
    condition     = length(var.owner) > 0
    error_message = "A variável 'owner' não pode ser vazia."
  }
}

variable "cost_center" {
  description = "Centro de custo associado ao recurso (ex.: CC-1234). Usado na tag obrigatória CostCenter."
  type        = string

  validation {
    condition     = can(regex("^CC-[0-9]+$", var.cost_center))
    error_message = "O 'cost_center' deve seguir o formato CC-<número> (ex.: CC-1234)."
  }
}

variable "environment" {
  description = "Nome do ambiente onde o recurso será provisionado. Valores aceitos: dev, staging, production."
  type        = string

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "O 'environment' deve ser um dos valores: dev, staging, production."
  }
}

# ----------------------------------------------------------
# Identificação do bucket
# ----------------------------------------------------------

variable "bucket_name" {
  description = "Nome lógico do bucket, sem prefixo e sem ambiente. O módulo compõe o nome final como hvt-<bucket_name>-<environment>. Use kebab-case (ex.: raw-data, app-artifacts)."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,50}[a-z0-9]$", var.bucket_name))
    error_message = "O 'bucket_name' deve conter apenas letras minúsculas, números e hífens, com entre 3 e 52 caracteres."
  }
}

# ----------------------------------------------------------
# Criptografia
# ----------------------------------------------------------

variable "sse_algorithm" {
  description = "Algoritmo de criptografia do lado do servidor (SSE). Valores aceitos: AES256 (SSE-S3) ou aws:kms (SSE-KMS)."
  type        = string
  default     = "AES256"

  validation {
    condition     = contains(["AES256", "aws:kms"], var.sse_algorithm)
    error_message = "O 'sse_algorithm' deve ser 'AES256' ou 'aws:kms'."
  }
}

variable "kms_master_key_id" {
  description = "ARN ou ID da chave KMS utilizada quando sse_algorithm = 'aws:kms'. Ignorado para AES256."
  type        = string
  default     = null
}

# ----------------------------------------------------------
# Logging
# ----------------------------------------------------------

variable "logging_target_bucket" {
  description = "Nome do bucket S3 de destino para os logs de acesso do servidor. Deve ser um bucket dedicado de logging já existente."
  type        = string
}

variable "logging_target_prefix" {
  description = "Prefixo (path) dentro do bucket de logging onde os logs serão armazenados. Padrão: logs/<bucket_name>/."
  type        = string
  default     = ""
}

# ----------------------------------------------------------
# Versionamento
# ----------------------------------------------------------

variable "versioning_enabled" {
  description = "Habilita o versionamento de objetos no bucket. Padrão: true (obrigatório pela política interna)."
  type        = bool
  default     = true
}

# ----------------------------------------------------------
# Lifecycle
# ----------------------------------------------------------

variable "noncurrent_version_expiration_days" {
  description = "Número de dias até que versões não-correntes de objetos sejam expiradas automaticamente. Use 0 para desativar."
  type        = number
  default     = 90

  validation {
    condition     = var.noncurrent_version_expiration_days >= 0
    error_message = "O valor de 'noncurrent_version_expiration_days' deve ser >= 0."
  }
}

# ----------------------------------------------------------
# Tags adicionais
# ----------------------------------------------------------

variable "additional_tags" {
  description = "Mapa de tags adicionais a serem mescladas com as tags obrigatórias (Owner, CostCenter, Environment). As tags obrigatórias têm precedência."
  type        = map(string)
  default     = {}
}
