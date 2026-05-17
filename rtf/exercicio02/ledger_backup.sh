#!/usr/bin/env bash
# ==============================================================================
# Script: ledger_backup.sh
# Descrição: Rotina de backup diário do banco de dados PostgreSQL (ledger_prod).
#            Realiza o dump, compacta com gzip, envia para o S3 e limpa backups
#            antigos (retenção de 30 dias).
# Autor: SRE
# SO: Ubuntu 22.04 LTS
# 
# Uso (Cron - 3:00 AM):
# 0 3 * * * /var/backups/ledger/ledger_backup.sh >> /var/log/ledger-backup-cron.log 2>&1
# ==============================================================================

set -e          # Sai imediatamente se um comando falhar
set -o pipefail # Captura falhas em pipes

# ==============================================================================
# Variáveis de Configuração
# ==============================================================================
# Configurações do Banco de Dados
DB_HOST="ledger-db.internal.hvt.io"
DB_PORT="5432"
DB_NAME="ledger_prod"
DB_USER="backup_user"
# A senha é esperada na variável PGPASSWORD. Se necessário buscar ativamente:
# export PGPASSWORD=$(aws secretsmanager get-secret-value --secret-id DB_SECRET_ID --query SecretString --output text --region us-east-1 | jq -r .password)

# Configurações de Diretório e Retenção
BACKUP_DIR="/var/backups/ledger"
S3_BUCKET="s3://hvt-ledger-backups"
RETENTION_DAYS=30
DATE_FORMAT=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE_NAME="${DB_NAME}_${DATE_FORMAT}.sql.gz"
BACKUP_FILE_PATH="${BACKUP_DIR}/${BACKUP_FILE_NAME}"

# Configurações de Log
LOG_FILE="/var/log/ledger-backup.log"

# ==============================================================================
# Funções Auxiliares
# ==============================================================================
log() {
    local type="$1"
    local msg="$2"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[${timestamp}] [${type}] ${msg}" | tee -a "${LOG_FILE}"
}

error_handler() {
    log "ERROR" "Falha na execucao do script na linha $1"
    exit 1
}

# Associa o error_handler a qualquer erro do script
trap 'error_handler $LINENO' ERR

# ==============================================================================
# Processo de Backup
# ==============================================================================
log "INFO" "Iniciando rotina de backup do banco ${DB_NAME}..."

# 1. Validação do diretório de backup local
if [ ! -d "${BACKUP_DIR}" ]; then
    log "INFO" "Criando diretorio de backup ${BACKUP_DIR}"
    mkdir -p "${BACKUP_DIR}"
fi

# 2. Execução do dump e compactação streamada
# Verifica se a variavel PGPASSWORD esta definida (basico)
if [ -z "$PGPASSWORD" ]; then
    log "ERROR" "A variavel de ambiente PGPASSWORD nao esta definida."
    exit 1
fi

log "INFO" "Executando pg_dump e compactando com gzip..."
pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -F p | gzip > "${BACKUP_FILE_PATH}"
log "INFO" "Dump e compactacao concluidos com sucesso: ${BACKUP_FILE_PATH}"

# 3. Upload para o S3
log "INFO" "Enviando arquivo para o S3 (${S3_BUCKET})..."
aws s3 cp "${BACKUP_FILE_PATH}" "${S3_BUCKET}/" --region us-east-1
log "INFO" "Upload concluido com sucesso."

# 4. Limpeza Remota no S3 (Retenção de 30 dias)
# Nota: Idealmente isso é gerenciado via AWS S3 Lifecycle Rules. 
# Abaixo implementamos a deleção via script para atender ao requisito explicitly.
log "INFO" "Removendo backups no S3 mais antigos que ${RETENTION_DAYS} dias..."
DATE_THRESHOLD=$(date -d "${RETENTION_DAYS} days ago" -u +"%Y-%m-%dT%H:%M:%SZ")

aws s3api list-objects-v2 \
    --bucket "hvt-ledger-backups" \
    --query "Contents[?LastModified<='${DATE_THRESHOLD}'].{Key: Key}" \
    --output text \
| while read -r key; do
    if [ -n "$key" ] && [ "$key" != "None" ]; then
        log "INFO" "Removendo backup antigo do S3: $key"
        aws s3 rm "${S3_BUCKET}/${key}"
    fi
done

# 5. Limpeza Local (Opcional, mas recomendado para manter os 80GB livres)
log "INFO" "Removendo backups locais mais antigos que ${RETENTION_DAYS} dias..."
find "${BACKUP_DIR}" -type f -name "${DB_NAME}_*.sql.gz" -mtime +${RETENTION_DAYS} -exec rm -f {} \;

log "INFO" "Rotina de backup finalizada com sucesso."
exit 0
