# Setup and Running Instructions

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or Docker)
- Docker and Docker Compose (optional, for containerized setup)

## Quick Start with Docker Compose

The easiest way to run the entire system:

```bash
# Start all services (PostgreSQL, Backend, Microservice)
docker-compose up

# Or run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

The services will be available at:
- Backend API: http://localhost:8000
- Microservice: http://localhost:8001
- PostgreSQL: localhost:5432

## Local Development Setup

### 1. Install PostgreSQL

Ensure PostgreSQL is installed and running on your system.

### 2. Create Database

```bash
createdb retrosynthesis
# Or using psql:
psql -U postgres -c "CREATE DATABASE retrosynthesis;"
```

### 3. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Microservice
cd ../microservice
pip install -r requirements.txt

# Scripts (for testing)
cd ../scripts
pip install -r requirements.txt
```

### 4. Set Environment Variables (Optional)

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/retrosynthesis

# Backend
API_HOST=0.0.0.0
API_PORT=8000
CALLBACK_HOST=localhost

# Microservice
MICROSERVICE_URL=http://localhost:8001

# Logging
LOG_LEVEL=INFO
```

### 5. Initialize Database

```bash
python -m backend.init_db
```

### 6. Start Services

**Option A: Using startup scripts**

```bash
# Linux/Mac
./scripts/start_local.sh

# Windows PowerShell
.\scripts\start_local.ps1
```

**Option B: Manual start**

Terminal 1 - Backend:
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2 - Microservice:
```bash
cd microservice
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## Testing

Use the provided mock client to test the system:

```bash
cd scripts
python mock_client.py "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
```

Or with custom backend URL:
```bash
python mock_client.py "CN1C=NC2=C1C(=O)N(C(=O)N2C)C" --backend-url http://localhost:8000
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
.
├── backend/              # Backend API service
│   ├── main.py          # FastAPI application
│   ├── database.py      # Database configuration
│   ├── db_models.py     # SQLAlchemy models
│   ├── models.py        # Pydantic models
│   └── config.py        # Configuration
├── microservice/        # Retrosynthesis microservice
│   ├── main.py         # FastAPI application
│   ├── models.py       # Pydantic models
│   └── get_routes.py   # Route loading logic
├── scripts/             # Utility scripts
│   └── mock_client.py  # Test client
└── docker-compose.yml   # Docker Compose configuration
```

## Troubleshooting

### Database Connection Issues

- Ensure PostgreSQL is running: `pg_isready`
- Check DATABASE_URL environment variable
- Verify database exists: `psql -l | grep retrosynthesis`

### Port Already in Use

- Change ports in `docker-compose.yml` or environment variables
- Kill existing processes: `lsof -ti:8000 | xargs kill` (Linux/Mac)

### Docker Issues

- Ensure Docker is running
- Check logs: `docker-compose logs backend` or `docker-compose logs microservice`
- Rebuild images: `docker-compose build --no-cache`
