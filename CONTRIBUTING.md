# Development Guide

## Local Development

### Prerequisites
- Python 3.10+
- Node.js 20+
- Docker and Docker Compose (optional)

### Setting up the backend

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r backend/requirements.txt
```

3. Run the backend:
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Run tests locally
make test-local

# Or directly with pytest
python -m pytest backend/tests

# Run tests in Docker
make test
```

### Using Docker Compose

```bash
# Build and run all services
make run

# Build only
make build
```

## Deployment

### Docker Deployment

The Dockerfile is configured to work out of the box:

```bash
docker build -f backend/Dockerfile -t oss-subfinder .
docker run -p 8000:8000 oss-subfinder
```

### Coolify Deployment

1. Connect your repository to Coolify
2. Use the following settings:
   - Build Context: `.`
   - Dockerfile Path: `backend/Dockerfile`
   - Port: 8000

### Environment Variables

The application supports these environment variables:

- `POSTGRES_DSN`: PostgreSQL connection string
- `MASSDNS_BIN`: Path to massdns binary
- `MASSDNS_RESOLVERS_FILE`: Path to resolvers file
- `REDIS_URL`: Redis connection string (optional)

## Project Structure

```
├── backend/
│   ├── app/           # FastAPI application
│   ├── scripts/       # Utility scripts
│   ├── tests/         # Test files
│   └── requirements.txt
├── frontend/          # React frontend
├── docs/             # Documentation
└── docker-compose.yml
```

## Common Issues

### ModuleNotFoundError: No module named 'app'

If you encounter this error:
1. Ensure you're running from the correct directory
2. For local development: `cd backend` before running
3. For Docker: The Dockerfile handles this automatically
4. For tests: Use `make test-local` or run from project root

### Frontend Development

```bash
cd frontend
npm install
npm run dev