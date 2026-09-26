# Roda como root na VM (via admin_sudo), depois de conforme.sh. Introduz um desvio por regra
# que o usuário comum consegue ver, mais os que ele não consegue (login de root).
# Recebe: USUARIO_COLETA, CHAVE_PESSOAL, CHAVE_HOSTIL, CHAVE_LEGADO.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# swap.habilitado (crítico)
if ! swapon --show=NAME --noheadings | grep -qx /swapfile; then
  fallocate -l 1G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
fi

# portas_em_escuta.somente_rede_interna (crítico): node_exporter em todos os endereços
mkdir -p /etc/systemd/system/node_exporter.service.d
cat > /etc/systemd/system/node_exporter.service.d/laboratorio.conf <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/local/bin/node_exporter --web.listen-address=0.0.0.0:9100
EOF
systemctl daemon-reload
systemctl restart node_exporter.service

# servicos.proibidos (alto)
apt-get install -y -q rpcbind
systemctl enable --now rpcbind.socket

# servicos.ativos (alto) e ntp.sincronizado (médio): chrony parado; acertar o relógio pelo
# próprio valor marca o kernel como não sincronizado sem esperar horas.
systemctl stop chrony.service
date -s "@$(date +%s)" >/dev/null

# chaves_ssh.emitidas_por (crítico): chave pessoal esquecida e chave com comentário hostil
casa="$(getent passwd "$USUARIO_COLETA" | cut -d: -f6)"
printf '%s\n' "$CHAVE_PESSOAL" "$CHAVE_HOSTIL" >> "$casa/.ssh/authorized_keys"

# chaves_ssh.emitidas_por, de novo: conta de serviço com shell nologin e chave esquecida,
# legível. O shell nologin não impede autenticar (nem abrir túnel): a conta tem de ser lida.
id svc-legado >/dev/null 2>&1 || useradd --system -m -d /var/lib/svc-legado -s /usr/sbin/nologin svc-legado
install -d -m 755 -o svc-legado -g svc-legado /var/lib/svc-legado/.ssh
printf '%s\n' "$CHAVE_LEGADO" > /var/lib/svc-legado/.ssh/authorized_keys
chmod 644 /var/lib/svc-legado/.ssh/authorized_keys
chmod 755 /var/lib/svc-legado

# ssh.login_de_root (alto): root por chave. Invisível ao usuário comum (nao_verificado).
printf 'PermitRootLogin prohibit-password\n' > /etc/ssh/sshd_config.d/10-laboratorio.conf
sshd -t
systemctl try-reload-or-restart ssh.service

echo "--- estado com desvios"
systemctl is-active chrony.service node_exporter.service rpcbind.socket 2>/dev/null || true
swapon --show --noheadings
ss -Hltn
echo "NTPSynchronized=$(timedatectl show -p NTPSynchronized --value)"
wc -l < "$casa/.ssh/authorized_keys"
