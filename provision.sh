set -e

echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf > /dev/null

echo "[+] Updating package lists and installing sshpass..."

export DEBIAN_FRONTEND=noninteractive
apt-get update 
apt-get install -y rkhunter sshpass

if ! id "sftp" &>/dev/null; then
    echo "[+] Creating user 'sftp' and group 'sftp'"
    sudo groupadd sftp
    sudo useradd -m sftp -g sftp
    echo "sftp:passtemp123" | chpasswd
else
    echo "[✓] User 'sftp' already exists"
fi

echo "[+] Configuring SSH for SFTP-only access..."

sudo bash -c 'cat <<EOF > /etc/ssh/sshd_config
Subsystem sftp internal-sftp

Match User sftp
ChrootDirectory /home/sftp
X11Forwarding no
AllowTcpForwarding no
PubkeyAuthentication yes
PasswordAuthentication no
AuthorizedKeysFile /home/sftp/.ssh/authorized_keys
EOF'

echo "[+] Setting up SFTP directory structure..."

sudo mkdir -p /home/sftp/uploads
sudo chown sftp:sftp /home/sftp/uploads
sudo chmod 700 /home/sftp/uploads

sudo chown root:root /home/sftp
sudo chmod 755 /home/sftp

echo "[+] Preparing .ssh directory for user 'sftp'..."

sudo mkdir -p /home/sftp/.ssh
sudo touch /home/sftp/.ssh/authorized_keys
sudo chmod 700 /home/sftp/.ssh
sudo chmod 600 /home/sftp/.ssh/authorized_keys
sudo chown -R sftp:sftp /home/sftp/.ssh

echo "[+] Moving and setting up SFTP scripts..."

sudo mkdir -p /home/sftp/scripts
sudo mv /tmp/scripts/* /home/sftp/scripts 2>/dev/null || echo "[!] No scripts found to move."
sudo chown -R sftp:sftp /home/sftp/scripts
sudo chmod -R 755 /home/sftp/scripts

echo "[+] Setting up SFTP private key and authorized_keys..."

sudo mv /tmp/sftp_key /home/sftp/.ssh/id_rsa 2>/dev/null || echo "[!] No /tmp/sftp_key found."
sudo mv /tmp/sftp_authorized_keys /home/sftp/.ssh/authorized_keys 2>/dev/null || echo "[!] No /tmp/sftp_authorized_keys found."
sudo chmod 600 /home/sftp/.ssh/id_rsa /home/sftp/.ssh/authorized_keys 2>/dev/null || true
sudo chown sftp:sftp /home/sftp/.ssh/id_rsa /home/sftp/.ssh/authorized_keys 2>/dev/null || true

echo "[+] Configuring cron job for sftp-exchange.sh..."

sudo -u sftp crontab -l | { cat; echo "*/5 * * * * /home/sftp/scripts/sftp-exchange.sh"; } | sudo -u sftp crontab -

echo "[✓] Cron job installed."

echo "[🔒] Hardening SSH settings..."

sudo sed -i -E 's/^#?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i -E 's/^#?PermitEmptyPasswords .*/PermitEmptyPasswords no/' /etc/ssh/sshd_config

echo "[✓] Password authentication disabled"

echo "[↻] Restarting SSH service..."

sudo systemctl restart ssh

sudo sed -i 's|^WEB_CMD=.*|WEB_CMD=|' /etc/rkhunter.conf
sudo sed -i 's/^MIRRORS_MODE=.*/MIRRORS_MODE=0/' /etc/rkhunter.conf || echo "MIRRORS_MODE=0" | sudo tee -a /etc/rkhunter.conf

rkhunter --update
rkhunter --propupd
rkhunter --check --sk || true

echo "[✅] Provisioning complete. SFTP setup and SSH hardened."
