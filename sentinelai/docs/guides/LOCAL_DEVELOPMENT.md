# Local Development

## Prerequisites

- Docker Desktop (recommended for full stack) **or** local PostgreSQL 14+ and Redis 7+
- Python 3.12+ (3.13 verified for API)
- Node.js 20+ (frontend — Milestone 9)

## API (without Docker)

```bash
cd sentinelai
cp .env.example .env

# Create DB role/database once
createdb sentinelai  # or use SQL from README bootstrap

cd apps/api
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export PYTHONPATH=$PWD
export DATABASE_URL=postgresql+asyncpg://sentinelai:sentinelai@localhost:5432/sentinelai
export DATABASE_URL_SYNC=postgresql://sentinelai:sentinelai@localhost:5432/sentinelai

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs  
Health: http://localhost:8000/api/v1/health

Bootstrap admin (from `.env`): `admin@example.com` / value of `BOOTSTRAP_ADMIN_PASSWORD`.

## Tests

```bash
cd apps/api
source .venv/bin/activate
export PYTHONPATH=$PWD
export DATABASE_URL=postgresql+asyncpg://sentinelai:sentinelai@localhost:5432/sentinelai
export DATABASE_URL_SYNC=postgresql://sentinelai:sentinelai@localhost:5432/sentinelai
export SECRET_KEY=test-secret-key-not-for-production
pytest -q
ruff check app tests
```

## Docker Compose

```bash
cd sentinelai
cp .env.example .env
docker compose up --build
```

Requires Docker daemon. Services: postgres, redis, prometheus, grafana, api.
