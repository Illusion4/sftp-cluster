#!/bin/bash

NEIGHBORS=("192.168.88.10" "192.168.88.11" "192.168.88.12")
THIS_IP=$(hostname -I | awk '{print $2}')
USERNAME="sftp"
REMOTE_DIR="uploads"
KEY_PATH="/home/sftp/.ssh/id_rsa"

TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
LOG_ENTRY="[$TIMESTAMP] created_by=${THIS_IP}"

for IP in "${NEIGHBORS[@]}"; do
  if [[ "$IP" == "$THIS_IP" ]]; then
      continue
  fi

  TARGET_FILE="from_${THIS_IP}.txt"
  TMP_LOCAL="/tmp/${TARGET_FILE}"

  if sftp -i "$KEY_PATH" -o StrictHostKeyChecking=no "${USERNAME}@${IP}" <<< "ls ${REMOTE_DIR}/${TARGET_FILE}" &>/dev/null; then
    sftp -i "$KEY_PATH" -o StrictHostKeyChecking=no "${USERNAME}@${IP}" <<EOF
    cd $REMOTE_DIR
    get $TARGET_FILE $TMP_LOCAL
EOF
    echo "$LOG_ENTRY" >> "$TMP_LOCAL"
  else
    echo "$LOG_ENTRY" > "$TMP_LOCAL"
  fi

  sftp -i "$KEY_PATH" -o StrictHostKeyChecking=no "${USERNAME}@${IP}" <<EOF
  cd $REMOTE_DIR
  put $TMP_LOCAL $TARGET_FILE
EOF

  rm -f "$TMP_LOCAL"
done
