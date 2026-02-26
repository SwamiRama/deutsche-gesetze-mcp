#!/bin/sh
set -e

DB_PATH="${GESETZE_DATABASE_PATH:-/tmp/gesetze.db}"
BUNDLED_DB="/app/gesetze.db"

if [ ! -f "$DB_PATH" ] || [ ! -s "$DB_PATH" ]; then
    if [ -f "$BUNDLED_DB" ]; then
        echo "Copying bundled database to $DB_PATH..."
        cp "$BUNDLED_DB" "$DB_PATH"
        echo "Database ready."
    else
        echo "No bundled database found. Starting with empty database."
    fi
fi

exec "$@"
