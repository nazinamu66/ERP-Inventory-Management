#!/bin/bash

# === CONFIGURATION ===
DB_NAME="inventrax"
DB_USER="inventrax_user"
DB_HOST="dpg-d0qcv0ripnbc73e977b0-a.oregon-postgres.render.com"   # Masked
DB_PASSWORD="vRzPBXqOgnpHSWIBNSN2I5xbAKwhas5A"             # 🔒 Replace securely
BACKUP_DIR="$HOME/db_backups"
BACKUP_FILE="$BACKUP_DIR/inventrax_backup_$(date +%Y-%m-%d).sql"
RCLONE_REMOTE="dropbox"
RCLONE_DEST="dropbox:/InventraxBackups"

# === CREATE BACKUP DIRECTORY IF NOT EXISTS ===
mkdir -p "$BACKUP_DIR"

# === EXPORT PASSWORD TEMPORARILY ===
export PGPASSWORD="$DB_PASSWORD"

# === RUN BACKUP ===
pg_dump -U "$DB_USER" -h "$DB_HOST" -d "$DB_NAME" -F p > "$BACKUP_FILE"

# === UPLOAD TO DROPBOX ===
rclone copy "$BACKUP_FILE" "$RCLONE_DEST"

# === CLEANUP ENV ===
unset PGPASSWORD

echo "✅ Backup completed and uploaded: $(date)"

