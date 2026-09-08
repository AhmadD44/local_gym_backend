#!/bin/sh
# Restores a Postgres backup created by backup_postgres.sh. DESTRUCTIVE:
# this replaces the current contents of the database (the dump was made
# with --clean --if-exists, so it drops existing objects before recreating
# them). Confirms before proceeding.
#
# Usage: ./scripts/restore_postgres.sh path/to/gym_backup_XXXXXXXX.sql.gz

set -eu

BACKUP_FILE="${1:?Usage: $0 path/to/backup.sql.gz}"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: backup file not found: $BACKUP_FILE" >&2
    exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. Run this from the project root on the server." >&2
    exit 1
fi

# shellcheck disable=SC1090
. "$ENV_FILE"
POSTGRES_USER="${POSTGRES_USER:-gym}"
POSTGRES_DB="${POSTGRES_DB:-gym}"

echo "This will DROP AND RECREATE objects in database '$POSTGRES_DB' from $BACKUP_FILE."
printf "Type 'yes' to continue: "
read -r confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

gunzip -c "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "Restore complete."
