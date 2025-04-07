from flask import Flask, render_template
import paramiko
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
import os
from collections import defaultdict, Counter

app = Flask(__name__)

VM_IPS = ["192.168.88.10", "192.168.88.11", "192.168.88.12"]
SSH_USERNAME = "sftp"
SSH_KEY_PATH = os.path.expanduser("~/.ssh/vagrant_host_key")
REMOTE_LOG_DIR = "uploads"
STATIC_DIR = os.path.join(app.root_path, 'static')
os.makedirs(STATIC_DIR, exist_ok=True)

def get_ssh_key():
    return paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)

def fetch_logs_from_vm(ip, pkey):
    logs = []
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=ip, username=SSH_USERNAME, pkey=pkey, timeout=10)
        with client.open_sftp() as sftp:
            try:
                files = sftp.listdir(REMOTE_LOG_DIR)
                for file in files:
                    if file.startswith("from_") and file.endswith(".txt"):
                        with sftp.file(f"{REMOTE_LOG_DIR}/{file}", 'r') as f:
                            for line in f:
                                logs.append((ip, line.strip()))
            except FileNotFoundError:
                print(f"{REMOTE_LOG_DIR} not found on {ip}")
    except Exception as e:
        print(f"Failed to connect to {ip}: {e}")
    finally:
        client.close()
    return logs

def parse_logs():
    pkey = get_ssh_key()
    parsed = []
    for ip in VM_IPS:
        print(f"Fetching logs from {ip}...")
        logs = fetch_logs_from_vm(ip, pkey)
        for vm_ip, entry in logs:
            try:
                ts_part, meta = entry.split('] ')
                timestamp = datetime.strptime(ts_part[1:], "%Y-%m-%d %H:%M:%S")
                created_by = meta.split('=')[1]
                parsed.append({'timestamp': timestamp, 'created_by': created_by, 'source_vm': vm_ip})
            except Exception as e:
                print(f"Skipping malformed entry '{entry}': {e}")
    return parsed

def generate_plots(logs):
    plots = {}
    date_counts = defaultdict(int)
    vm_counts = defaultdict(int)

    for entry in logs:
        date_str = entry['timestamp'].date().isoformat()
        date_counts[date_str] += 1
        vm_counts[entry['source_vm']] += 1

    plt.figure(figsize=(12, 6))
    dates = sorted(date_counts)
    plt.bar(dates, [date_counts[d] for d in dates])
    plt.title('Number of Log Entries Per Day')
    plt.ylabel("Entries")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    path = os.path.join(STATIC_DIR, 'daily_activity.png')
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    plots['daily_activity'] = 'daily_activity.png'

    plt.figure(figsize=(10, 6))
    vms = sorted(vm_counts)
    plt.bar(vms, [vm_counts[v] for v in vms])
    plt.title('Activity by VM')
    plt.tight_layout()
    path = os.path.join(STATIC_DIR, 'vm_activity.png')
    plt.savefig(path, bbox_inches='tight')
    plt.close()
    plots['vm_activity'] = 'vm_activity.png'

    return plots

@app.route('/')
def dashboard():
    logs = parse_logs()
    if not logs:
        return "No log data found."

    timestamps = [entry['timestamp'] for entry in logs]
    vms = set(entry['source_vm'] for entry in logs)

    stats = {
        'total_entries': len(logs),
        'unique_vms': len(vms),
        'first_entry': min(timestamps).strftime("%Y-%m-%d %H:%M:%S"),
        'last_entry': max(timestamps).strftime("%Y-%m-%d %H:%M:%S")
    }

    plots = generate_plots(logs)
    return render_template('logs_dashboard.html', stats=stats, plots=plots)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
