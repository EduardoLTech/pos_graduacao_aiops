# ============================================================
# outputs.tf – Módulo S3 | Padrão HVT
# ============================================================

output "bucket_name" {
  description = "Nome completo do bucket S3 criado (hvt-<bucket_name>-<environment>)."
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "ARN do bucket S3 criado. Utilize para políticas IAM e configurações de serviços AWS."
  value       = aws_s3_bucket.this.arn
}

output "bucket_domain_name" {
  description = "Endpoint de domínio do bucket no formato <bucket>.s3.amazonaws.com."
  value       = aws_s3_bucket.this.bucket_domain_name
}

output "bucket_regional_domain_name" {
  description = "Endpoint regional do bucket, preferível ao domain_name para evitar latência de redirecionamento."
  value       = aws_s3_bucket.this.bucket_regional_domain_name
}

output "bucket_region" {
  description = "Região AWS onde o bucket foi criado."
  value       = aws_s3_bucket.this.region
}

output "versioning_status" {
  description = "Status atual do versionamento do bucket: Enabled ou Suspended."
  value       = aws_s3_bucket_versioning.this.versioning_configuration[0].status
}

output "encryption_algorithm" {
  description = "Algoritmo SSE configurado no bucket (AES256 ou aws:kms)."
  value       = var.sse_algorithm
}
