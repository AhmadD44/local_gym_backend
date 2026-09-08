#!/bin/sh
# Dumps the production Postgres database to a timestamped, gzip-compressed
# file and deletes local backups older than RETENTION_DAYS. Run this via
# cron on the host (see DEPLOYMENT.md) — it shells out to `docker compose
# exec`, so it must run on the server, in the project directory, not inside
# a container.
#
# Usage: ./scripts/backup_postgres.sh [backup_dir] [retention_days]
#
# Crontab example (daily at 3am, keep 14 days, adjust the path):
#   0 3 * * * cd /opt/gym-backend && ./scripts/backup_postgres.sh /opt/gym-backend/backups 14 >> /var/log/gym-backup.log 2>&1
#
# For anything beyond "good enough for a single small server", also copy
# backups off-box (S3/rsync to another host) — a backup that only lives on
# the same disk as the database doesn't protect against disk/host failure.

set -eu

BACKUP_DIR="${1:-./backups}"
RETENTION_DAYS="${2:-14}"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. Run this from the project root on the server." >&2
    exit 1
fi

# shellcheck disable=SC1090
. "$ENV_FILE"

POSTGRES_USER="${POSTGRES_USER:-gym}"
POSTGRES_DB="${POSTGRES_DB:-gym}"

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
outfile="$BACKUP_DIR/gym_backup_${timestamp}.sql.gz"

echo "Backing up database '$POSTGRES_DB' to $outfile ..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --clean --if-exists \
    | gzip > "$outfile"

echo "Backup complete: $(du -h "$outfile" | cut -f1)"

echo "Pruning backups older than $RETENTION_DAYS days in $BACKUP_DIR ..."
find "$BACKUP_DIR" -name 'gym_backup_*.sql.gz' -mtime "+${RETENTION_DAYS}" -print -delete

echo "Done."
