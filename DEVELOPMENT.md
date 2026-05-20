# Local Development Quick Start Guide

## Prerequisites

- Docker and Docker Compose installed
- Google Cloud service account JSON key (optional, for email/GCS features)
- Python 3.9+ (for running individual services)
- Node.js 18+ (for frontend development)

## Quick Start with Docker Compose

### 1. Set Up Service Account (Optional)

If you want to test email and GCS features:

```bash
# Download your GCP service account key
# Save it as: sa-key.json in the project root

# The docker-compose will automatically mount it for the backend
```

### 2. Start All Services

```bash
# Start all services in the background
docker-compose up -d

# Or, start with logs visible
docker-compose up

# Services will be available at:
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Database Admin: http://localhost:8080 (Adminer)
```

### 3. Database Management

#### Using Adminer (Web UI)
- URL: http://localhost:8080
- System: PostgreSQL
- Server: db
- Username: emailservice
- Password: devpassword123
- Database: crystal_db

#### Using psql CLI
```bash
# Connect to database
docker-compose exec db psql -U emailservice -d crystal_db

# Useful commands:
# \dt                    - List tables
# SELECT * FROM jobs;    - View jobs
# \q                     - Exit
```

### 4. View Logs

```bash
# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### 5. Stop Services

```bash
# Stop all services (keep volumes)
docker-compose stop

# Stop and remove containers (keep volumes)
docker-compose down

# Stop and remove everything (including volumes)
docker-compose down -v
```

## Manual Development Setup (Without Docker Compose)

### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your configuration
# For local development, use SQLite:
# DATABASE_URL=sqlite:///./jobs.db

# Run migrations (if needed)
python -c "from backend.database import Base, engine; Base.metadata.create_all(bind=engine)"

# Start backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Frontend will be available at http://localhost:5173
```

## API Testing

### Using cURL

```bash
# Get suppliers
curl http://localhost:8000/api/suppliers

# Get all jobs
curl http://localhost:8000/api/jobs

# Create a new job
curl -X POST http://localhost:8000/api/jobs/start \
  -H "Content-Type: application/json" \
  -d '{
    "chemical_query": "20000 MT Methanol CFR Singapore",
    "supplier_emails": ["supplier1@example.com", "supplier2@example.com"]
  }'

# Refresh insights for a job
curl -X POST http://localhost:8000/api/jobs/1/insights/refresh
```

### Using Swagger UI

Navigate to http://localhost:8000/docs for interactive API documentation

### Using Python Requests

```python
import requests

# Get suppliers
response = requests.get('http://localhost:8000/api/suppliers')
print(response.json())

# Create job
job_data = {
    "chemical_query": "20000 MT Methanol CFR Singapore",
    "supplier_emails": ["supplier1@example.com"]
}
response = requests.post('http://localhost:8000/api/jobs/start', json=job_data)
print(response.json())
```

## Development Workflows

### Backend Development

1. Make changes to files in `backend/` or `main.py`
2. Code changes are automatically reloaded (uvicorn --reload)
3. Check logs for any errors
4. Test changes via API

### Frontend Development

1. Make changes to files in `frontend/src/`
2. Changes are automatically hot-reloaded by Vite
3. Check console for any errors
4. Refresh browser if needed

### Database Changes

```bash
# If you modify database models in backend/database.py:

# Option 1: Drop and recreate (development only)
docker-compose exec backend python -c \
  "from backend.database import Base, engine; Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)"

# Option 2: Connect and run SQL directly
docker-compose exec db psql -U emailservice -d crystal_db
# Then run your SQL queries
```

### Testing

```bash
# Install pytest
pip install pytest pytest-asyncio httpx

# Create test file: test_main.py
cat > test_main.py << 'EOF'
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_suppliers():
    response = client.get("/api/suppliers")
    assert response.status_code == 200

def test_start_job():
    response = client.post("/api/jobs/start", json={
        "chemical_query": "Test Query",
        "supplier_emails": ["test@example.com"]
    })
    assert response.status_code == 200
EOF

# Run tests
pytest test_main.py -v
```

## Debugging

### Backend Debugging with VS Code

1. Install Python extension
2. Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["main:app", "--reload"],
            "jinja": true
        }
    ]
}
```

3. Set breakpoints and press F5 to start debugging

### Frontend Debugging

1. Open browser DevTools (F12)
2. Use React DevTools browser extension
3. Check Console tab for errors

### Database Debugging

```bash
# Check database size
docker-compose exec db psql -U emailservice -d crystal_db \
  -c "SELECT pg_size_pretty(pg_database_size('crystal_db'));"

# List all tables
docker-compose exec db psql -U emailservice -d crystal_db -c "\dt"

# Check job records
docker-compose exec db psql -U emailservice -d crystal_db \
  -c "SELECT id, chemical_query, status, created_at FROM jobs;"
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000  # Backend
lsof -i :5173  # Frontend
lsof -i :5432  # Database

# Kill process (macOS/Linux)
kill -9 <PID>

# Kill process (Windows)
taskkill /PID <PID> /F
```

### Docker Issues

```bash
# Rebuild images
docker-compose build --no-cache

# Clean everything and start fresh
docker-compose down -v
docker system prune -f
docker-compose up -d
```

### Database Connection Error

```bash
# Check if database is running
docker-compose ps

# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Frontend Not Loading

```bash
# Check frontend logs
docker-compose logs frontend

# Ensure port 5173 is available
netstat -an | grep 5173

# Rebuild frontend
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

## Performance Tips

- Use `docker-compose up -d` to run services in background
- Use `--scale` to run multiple instances of a service
- Mount volumes for code to avoid rebuilds
- Use `.dockerignore` to exclude unnecessary files

## Next Steps

1. Configure `.env` with your GCP credentials
2. Update `suppliers.csv` with your supplier data
3. Customize email templates as needed
4. Test the full workflow end-to-end
5. Deploy to GCP when ready

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
