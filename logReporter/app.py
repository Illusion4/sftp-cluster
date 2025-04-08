from flask import Flask, render_template
import paramiko
from datetime import datetime
import os
from pymongo import MongoClient

APP = Flask(__name__)

VM_IPS = ["192.168.88.10", "192.168.88.11", "192.168.88.12"]
SSH_CONFIG = {
    "username": "sftp",
    "key_path": os.path.expanduser("~/.ssh/id_rsa"),
    "remote_dir": "uploads",
    "timeout": 10
}

MONGO_CLIENT = MongoClient("mongo", 27017)
DB = MONGO_CLIENT["log_reporter"]
LOG_COLLECTION = DB["logs"]
PROGRESS_COLLECTION = DB["log_progress"]

class SSHManager:
    def __init__(self):
        self.pkey = paramiko.RSAKey.from_private_key_file(SSH_CONFIG["key_path"])

    def _connect(self, ip):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=ip,
            username=SSH_CONFIG["username"],
            pkey=self.pkey,
            timeout=SSH_CONFIG["timeout"]
        )
        return client

    def fetch_logs(self):
        for ip in VM_IPS:
            try:
                with self._connect(ip) as client:
                    self._process_vm_files(client, ip)
            except Exception as e:
                print(f"Connection to {ip} failed: {e}")

    def _process_vm_files(self, client, ip):
        with client.open_sftp() as sftp:
            try:
                files = sftp.listdir(SSH_CONFIG["remote_dir"])
                for filename in self._filter_log_files(files):
                    self._process_file(sftp, ip, filename)
            except FileNotFoundError:
                print(f"Directory {SSH_CONFIG['remote_dir']} not found on {ip}")

    def _filter_log_files(self, files):
        return [
            f for f in files
            if f.startswith("from_") and f.endswith(".txt")
        ]

    def _process_file(self, sftp, ip, filename):
        remote_path = f"{SSH_CONFIG['remote_dir']}/{filename}"
        progress = self._get_progress(ip, filename)
        last_ts = progress.get("last_timestamp", datetime.min)

        with sftp.file(remote_path, 'r') as f:
            entries, max_ts = self._parse_log_lines(f, ip, last_ts)

        if entries:
            LOG_COLLECTION.insert_many(entries)
            self._update_progress(ip, filename, max_ts)

    def _get_progress(self, ip, filename):
        return PROGRESS_COLLECTION.find_one(
            {"vm_ip": ip, "filename": filename}
        ) or {}

    def _parse_log_lines(self, file_obj, ip, last_ts):
        entries = []
        max_ts = last_ts
        for line in file_obj:
            try:
                timestamp, created_by = self._parse_log_line(line)
                if timestamp > last_ts:
                    entries.append({
                        'timestamp': timestamp,
                        'created_by': created_by,
                        'source_vm': ip
                    })
                    max_ts = max(max_ts, timestamp)
            except ValueError as e:
                print(f"Invalid log entry: {line.strip()} - {e}")
        return entries, max_ts

    @staticmethod
    def _parse_log_line(line):
        line = line.strip()
        if not line.startswith('[') or '] from=' not in line:
            raise ValueError("Invalid log format")

        ts_part, from_part = line.split('] from=')
        timestamp = datetime.strptime(ts_part[1:], "%Y-%m-%d %H:%M:%S")
        created_by = from_part.strip()
        return timestamp, created_by

    def _update_progress(self, ip, filename, timestamp):
        PROGRESS_COLLECTION.update_one(
            {"vm_ip": ip, "filename": filename},
            {"$set": {"last_timestamp": timestamp}},
            upsert=True
        )

class AnalyticsEngine:
    @staticmethod
    def get_stats():
        pipeline = [
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "first": {"$min": "$timestamp"},
                "last": {"$max": "$timestamp"},
                "vms": {"$addToSet": "$source_vm"}
            }},
            {"$project": {
                "total": 1,
                "first": 1,
                "last": 1,
                "unique_vms": {"$size": "$vms"}
            }}
        ]
        result = LOG_COLLECTION.aggregate(pipeline)
        return next(result, None)

    @staticmethod
    def get_daily_activity():
        pipeline = [
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        return list(LOG_COLLECTION.aggregate(pipeline))

    @staticmethod
    def get_vm_activity():
        pipeline = [
            {"$group": {"_id": "$source_vm", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        return list(LOG_COLLECTION.aggregate(pipeline))

@APP.route('/')
def dashboard():
    SSHManager().fetch_logs()

    stats = AnalyticsEngine.get_stats()
    if not stats or not stats.get('total'):
        return "No log data available"

    daily_activity = AnalyticsEngine.get_daily_activity()
    vm_activity = AnalyticsEngine.get_vm_activity()

    context = {
        "stats": {
            "total_entries": stats["total"],
            "unique_vms": stats["unique_vms"],
            "first_entry": stats["first"].strftime("%Y-%m-%d %H:%M:%S"),
            "last_entry": stats["last"].strftime("%Y-%m-%d %H:%M:%S")
        },
        "daily_labels": [entry["_id"] for entry in daily_activity],
        "daily_counts": [entry["count"] for entry in daily_activity],
        "vm_labels": [entry["_id"] for entry in vm_activity],
        "vm_counts": [entry["count"] for entry in vm_activity]
    }

    return render_template('logs_dashboard.html', **context)

if __name__ == '__main__':
    APP.run(host='0.0.0.0', port=5000)


