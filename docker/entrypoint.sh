#!/bin/sh
set -e

DB_PATH="${GESETZE_DATABASE_PATH:-/tmp/gesetze.db}"

if [ ! -f "$DB_PATH" ] || [ ! -s "$DB_PATH" ]; then
    echo "Database not found at $DB_PATH, running data load..."
    python /app/scripts/update_laws.py
    echo "Data load complete."
fi

exec "$@"
