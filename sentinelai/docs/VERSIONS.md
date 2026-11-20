# Dependency Version Choices

Pinned versions used in v0.1 (validated on Python 3.13 / intended for 3.12+):

| Package | Version | Notes |
|---------|---------|-------|
| FastAPI | 0.115.6 | Stable ASGI API framework |
| Uvicorn | 0.34.3 | ASGI server |
| SQLAlchemy | 2.0.36 | Async ORM |
| Alembic | 1.14.0 | Migrations |
| Pydantic | 2.14.4 | Compatible with Python 3.13 wheels |
| asyncpg | 0.30.0 | Async Postgres driver |
| Redis (client) | 5.2.1 | Cache/queue client |
| OpenAI SDK | 1.57.4 | Optional provider |
| Anthropic SDK | 0.40.0 | Optional provider |
| Prometheus client | 0.21.1 | /metrics exposition |
| Next.js | 15.x | Planned Milestone 9 |
| PostgreSQL image | pgvector/pgvector:pg16 | Compose |
| Redis image | 7.4-alpine | Compose |

Update this file when pins change after verification.
