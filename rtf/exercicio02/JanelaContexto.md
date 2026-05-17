# Context Window Content

## User Prompt

#Role
Voce é um SRE senior e especialista em postgresql, aws e shell script.

#Task
Criar um shell script para rotina de backup diario usando cron as 3:00AM de um banco de dados em uma EC2.
O script precisa fazer o dump com pg_dump, compactar com gzip, subir o arquivo pro bucket S3 de nome hvt-ledger-backups (está na mesma regiao do banco) via aws s3 cp, manter 30 dias de retenção no S3 (removendo os mais antigos). Considere que o aws cli já está instalado na ec2. 
Cada vez que o script for executado, deve ter o registro  em /var/log/ledger-backup.log com timestamp, e sair com exit code adequado em caso de falha.
Dados do banco:
Host: ledger-db.internal.hvt.io
Porta: 5432
Banco: ledger_prod
Usuário de backup: backup_user
Senha: variável de ambiente PGPASSWORD, populada pelo AWS Secrets Manager via IAM role da instância
Região AWS: us-east-1
SO da instância: Ubuntu 22.04 LTS
Diretório de trabalho com 80 GB livres: /var/backups/ledger
Tamanho médio atual do dump compactado: ~12 GB

#Format
Script Bash comentado, com cabeçalho explicando uso e variáveis configuráveis no topo do arquivo. Gravado em C:\estudo\github\aiops_eng_prompts\rtf\exercicio02.

## Model Response

O script de backup do banco de dados PostgreSQL foi criado com sucesso no caminho solicitado.

O script inclui:
- **Agendamento no cabeçalho:** Comentado, mostrando o formato exato para agendamento no Cron (`0 3 * * *`).
- **Validação e Log:** O script escreve o log em `/var/log/ledger-backup.log` utilizando timestamps para cada operação. Asseguramos o uso do diretório `/var/backups/ledger`.
- **Tratamento de Erros:** O script foi configurado com `set -e` e `set -o pipefail`. Adicionado um `trap` em `ERR` que captará qualquer erro ocorrido (mesmo no fluxo do pipe) reportando o `exit code` e a linha do problema no log antes de fechar com exit code 1.
- **Processamento Concorrente:** Realiza o pg_dump pipeando a saída diretamente para a compressão via `gzip`, economizando I/O de disco.
- **Integração S3 e Retenção:** Executa o `aws s3 cp` para subida do arquivo em us-east-1. Adicionado também a lógica de limpeza baseada na consulta à API do S3 buscando apenas o que passou de 30 dias usando `aws s3api list-objects-v2` e removendo com `aws s3 rm`. O script também limpa diretório local para não estourar os 80GB de disco.

O arquivo pode ser encontrado aqui: `C:\estudo\github\aiops_eng_prompts\rtf\exercicio02\ledger_backup.sh`
