#!/bin/bash
# Start services locally (without Docker)

set -e

echo "Starting PostgreSQL..."
# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "PostgreSQL is not running. Please start it first."
    exit 1
fi

echo "Initializing database..."
cd "$(dirname "$0")/.."
python -m backend.init_db

echo "Starting backend API..."
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Starting microservice..."
cd ../microservice
python -m uvicorn main:app --host 0.0.0.0 --port 8001 &
MICROSERVICE_PID=$!

echo "Backend running on http://localhost:8000 (PID: $BACKEND_PID)"
echo "Microservice running on http://localhost:8001 (PID: $MICROSERVICE_PID)"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $BACKEND_PID $MICROSERVICE_PID" EXIT
wait
