echo "[+] Installing Docker on #{name}..."
apt-get update
apt-get install -y docker.io
curl -SL https://github.com/docker/compose/releases/download/v2.34.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
usermod -aG docker vagrant

sudo mv /tmp/sftp_key /home/vagrant/.ssh/id_rsa
sudo mv /tmp/sftp_authorized_keys /home/vagrant/.ssh/authorized_keys
sudo chmod 600 /home/vagrant/.ssh/id_rsa /home/vagrant/.ssh/authorized_keys 2>/dev/null || true
sudo chown vagrant:vagrant /home/vagrant/.ssh/id_rsa /home/vagrant/.ssh/authorized_keys 2>/dev/null || true
sudo chmod 700 /home/vagrant/.ssh
sudo chown -R vagrant:vagrant /home/vagrant/.ssh

echo "[+] Starting Docker Compose services..."
cd /home/vagrant/dashboard
docker-compose up -d

