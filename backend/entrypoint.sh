#!/bin/sh
set -e

# Apply database migrations
echo "Running database migrations..."
python -m alembic upgrade head

# Start the application (production server, no auto-reload per D1)
echo "Starting backend server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
