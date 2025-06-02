#!/bin/bash

# === CONFIG ===
DROPBOX_FOLDER="InventraxBackups"
DB_NAME="inventrax"
DB_USER="inventrax_user"
DB_HOST="dpg-d0qcv0ripnbc73e977b0-a.oregon-postgres.render.com"
DB_PORT="5432"
DB_PASSWORD="vRzPBXqOgnpHSWIBNSN2I5xbAKwhas5A"
DEST_DIR="/tmp"  # ✅ Add this line

# === STEP 1: Find latest .sql backup ===
echo "📂 Searching for latest backup in Dropbox..."

echo "📂 Searching for latest backup in Dropbox..."

LATEST_FILE=$(rclone lsf dropbox:$DROPBOX_FOLDER --files-only | grep '.sql$' | sort | tail -n 1 | tr -d '\r\n')

if [ -z "$LATEST_FILE" ]; then
  echo "❌ No .sql files found in Dropbox folder '$DROPBOX_FOLDER'"
  exit 1
fi

echo "✅ Found: $LATEST_FILE"
LOCAL_PATH="$DEST_DIR/$LATEST_FILE"

# === STEP 2: Download the file ===
echo "⬇️ Downloading backup to $LOCAL_PATH..."
rclone copy "dropbox:$DROPBOX_FOLDER/$LATEST_FILE" "$DEST_DIR" --progress

if [ ! -f "$LOCAL_PATH" ]; then
  echo "❌ Backup file not found after download"
  exit 1
fi

# === STEP 3: Restore ===
echo "🗄 Restoring database '$DB_NAME' from $LATEST_FILE..."

PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME < "$LOCAL_PATH"

if [ $? -eq 0 ]; then
  echo "✅ Restore completed successfully!"
else
  echo "❌ Restore failed"
fi
