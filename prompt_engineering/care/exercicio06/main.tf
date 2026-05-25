# ============================================================
# main.tf – Módulo S3 | Padrão HVT
# ============================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# ----------------------------------------------------------
# Locals
# ----------------------------------------------------------

locals {
  bucket_full_name = "hvt-${var.bucket_name}-${var.environment}"

  logging_prefix = length(var.logging_target_prefix) > 0 ? var.logging_target_prefix : "logs/${local.bucket_full_name}/"

  common_tags = {
    Owner       = var.owner
    CostCenter  = var.cost_center
    Environment = var.environment
  }

  all_tags = merge(var.additional_tags, local.common_tags)
}

# ----------------------------------------------------------
# Bucket principal
# ----------------------------------------------------------

resource "aws_s3_bucket" "this" {
  bucket = local.bucket_full_name

  tags = merge(local.all_tags, {
    Name = local.bucket_full_name
  })
}

# ----------------------------------------------------------
# Block Public Access (total)
# ----------------------------------------------------------

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ----------------------------------------------------------
# Versionamento
# ----------------------------------------------------------

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id

  versioning_configuration {
    status = var.versioning_enabled ? "Enabled" : "Suspended"
  }
}

# ----------------------------------------------------------
# Criptografia SSE
# ----------------------------------------------------------

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.sse_algorithm
      kms_master_key_id = var.sse_algorithm == "aws:kms" ? var.kms_master_key_id : null
    }

    # Garante que objetos enviados sem header de criptografia sejam recusados
    bucket_key_enabled = var.sse_algorithm == "aws:kms"
  }
}

# ----------------------------------------------------------
# Logging de acesso ao servidor
# ----------------------------------------------------------

resource "aws_s3_bucket_logging" "this" {
  bucket = aws_s3_bucket.this.id

  target_bucket = var.logging_target_bucket
  target_prefix = local.logging_prefix
}

# ----------------------------------------------------------
# Lifecycle – expiração de versões não-correntes
# ----------------------------------------------------------

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  count = var.noncurrent_version_expiration_days > 0 ? 1 : 0

  bucket = aws_s3_bucket.this.id

  # Depende do versionamento estar ativo para regra de versões funcionar
  depends_on = [aws_s3_bucket_versioning.this]

  rule {
    id     = "hvt-expire-noncurrent-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_expiration_days
    }

    # Aborta uploads multipart incompletos após 7 dias para evitar custos ocultos
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
