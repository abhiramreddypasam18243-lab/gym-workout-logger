#!/bin/sh
set -e

# Apply database migrations and seeds
echo "Running database initialization and migrations..."
python -m app.init_db

# Start the application (listen on PORT or default to 8000)
PORT="${PORT:-8000}"
echo "Starting backend server on port ${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1
