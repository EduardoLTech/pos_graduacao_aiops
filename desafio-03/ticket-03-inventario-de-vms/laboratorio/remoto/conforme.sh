# Roda como root na VM (via admin_sudo). Deixa o host conforme ao baseline.
# Recebe: USUARIO_COLETA, CHAVE_COLETA, NODE_EXPORTER_VERSAO.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# Usuário de coleta: useradd, fora do mecanismo de chaves por metadata do GCP (ADR 005), sem
# sudo, com uma única chave — a da plataforma.
id "$USUARIO_COLETA" >/dev/null 2>&1 || useradd -m -s /bin/bash "$USUARIO_COLETA"
casa="$(getent passwd "$USUARIO_COLETA" | cut -d: -f6)"
install -d -m 700 -o "$USUARIO_COLETA" -g "$USUARIO_COLETA" "$casa/.ssh"
printf '%s\n' "$CHAVE_COLETA" > "$casa/.ssh/authorized_keys"
chown "$USUARIO_COLETA:$USUARIO_COLETA" "$casa/.ssh/authorized_keys"
chmod 600 "$casa/.ssh/authorized_keys"

# Desfaz a conta de serviço com chave esquecida do estado com desvios.
if id svc-legado >/dev/null 2>&1; then userdel -r svc-legado 2>/dev/null || true; fi

apt-get update -q
apt-get install -y -q containerd chrony

# node_exporter com o nome de unidade que o baseline cita (o pacote do Ubuntu chama
# prometheus-node-exporter e não satisfaria a regra).
if [[ ! -x /usr/local/bin/node_exporter ]]; then
  base="https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSAO}"
  pacote="node_exporter-${NODE_EXPORTER_VERSAO}.linux-amd64.tar.gz"
  tmp="$(mktemp -d)"
  curl -fsSL -o "$tmp/$pacote" "$base/$pacote"
  curl -fsSL -o "$tmp/sha256sums.txt" "$base/sha256sums.txt"
  (cd "$tmp" && grep " $pacote\$" sha256sums.txt | sha256sum -c -)
  tar -xzf "$tmp/$pacote" -C "$tmp"
  install -m 755 "$tmp/node_exporter-${NODE_EXPORTER_VERSAO}.linux-amd64/node_exporter" /usr/local/bin/
  rm -rf "$tmp"
fi
id node_exporter >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin node_exporter
ip_interno="$(hostname -I | awk '{print $1}')"
cat > /etc/systemd/system/node_exporter.service <<EOF
[Unit]
Description=Node Exporter
After=network-online.target
Wants=network-online.target

[Service]
User=node_exporter
ExecStart=/usr/local/bin/node_exporter --web.listen-address=${ip_interno}:9100
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
rm -rf /etc/systemd/system/node_exporter.service.d
systemctl daemon-reload
systemctl enable node_exporter.service
systemctl restart node_exporter.service

# Sem swap.
swapoff -a
rm -f /swapfile
sed -i '\|^/swapfile |d' /etc/fstab

# Nenhum serviço proibido ativo.
systemctl disable --now rpcbind.socket rpcbind.service 2>/dev/null || true
systemctl disable --now telnet.socket 2>/dev/null || true

# Login de root desligado. O Ubuntu lê sshd_config.d antes do resto e vale o primeiro valor.
printf 'PermitRootLogin no\n' > /etc/ssh/sshd_config.d/10-laboratorio.conf
sshd -t
systemctl try-reload-or-restart ssh.service

# Relógio sincronizado.
systemctl enable --now chrony.service
chronyc -a makestep >/dev/null || true
chronyc waitsync 12 >/dev/null || true

echo "--- estado conforme"
id "$USUARIO_COLETA"
systemctl is-active ssh.service ssh.socket containerd.service chrony.service \
  node_exporter.service rpcbind.socket 2>/dev/null || true
echo "swap: $(swapon --show --noheadings | wc -l) área(s)"
ss -Hltn
echo "NTPSynchronized=$(timedatectl show -p NTPSynchronized --value)"
