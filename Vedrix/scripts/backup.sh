#!/bin/bash
# Database backup script for Vedrix
# Usage: ./backup.sh [production|staging]

set -e

ENVIRONMENT=${1:-production}
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
TIMESTAMP_FILE="$BACKUP_DIR/latest_backup"

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

echo "Starting backup for environment: $ENVIRONMENT"

# Determine container name based on environment
if [ "$ENVIRONMENT" = "production" ]; then
    CONTAINER_NAME="vedrix-db-prod"
    DB_NAME="vedrix_prod"
else
    CONTAINER_NAME="vedrix-db-staging"
    DB_NAME="vedrix_staging"
fi

# Check if container exists
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Error: Container $CONTAINER_NAME is not running"
    exit 1
fi

# Create backup filename
BACKUP_FILE="$BACKUP_DIR/vedrix_${ENVIRONMENT}_${DATE}.sql"

# Perform backup
echo "Creating backup: $BACKUP_FILE"
docker exec -it "$CONTAINER_NAME" pg_dump -U postgres -d "$DB_NAME" > "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"
BACKUP_FILE="${BACKUP_FILE}.gz"

# Get file size
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

# Update latest backup symlink
echo "$BACKUP_FILE" > "$TIMESTAMP_FILE"

echo "Backup completed successfully!"
echo "  File: $BACKUP_FILE"
echo "  Size: $SIZE"

# Keep only last 7 backups
echo "Cleaning up old backups (keeping last 7)..."
ls -t "$BACKUP_DIR"/vedrix_${ENVIRONMENT}_*.sql.gz | tail -n +8 | xargs -r rm -f

echo "Done!"