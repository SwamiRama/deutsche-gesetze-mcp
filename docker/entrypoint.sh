#!/bin/sh
set -e

DB_PATH="${GESETZE_DATABASE_PATH:-/tmp/gesetze.db}"
XML_DIR="${GESETZE_DATA_DIR:-/data}/xml"

if [ ! -f "$DB_PATH" ] || [ ! -s "$DB_PATH" ]; then
    if [ -d "$XML_DIR" ] && [ "$(ls -A "$XML_DIR" 2>/dev/null)" ]; then
        echo "Database not found, rebuilding from cached XML files..."
        python /app/scripts/update_laws.py
        echo "Data load complete."
    else
        echo "No database and no cached XML files. Starting with empty database."
        echo "Run 'python /app/scripts/update_laws.py' to populate data."
    fi
fi

exec "$@"
