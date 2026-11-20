# Repository Directory Structure

```
sentinelai/
├── apps/
│   ├── web/                      # Next.js App Router UI
│   ├── api/                      # FastAPI control plane
│   │   ├── app/
│   │   │   ├── api/              # Route routers
│   │   │   ├── core/             # Config, security, deps
│   │   │   ├── models/           # SQLAlchemy
│   │   │   ├── schemas/          # Pydantic I/O
│   │   │   ├── services/         # Domain services
│   │   │   ├── agents/           # Investigation state machine
│   │   │   ├── ai/               # Provider adapters
│   │   │   ├── mcp/              # MCP tool server
│   │   │   ├── detection/        # Rules + anomaly
│   │   │   ├── remediation/      # Plans + sandbox
│   │   │   ├── evaluation/       # MLOps runners
│   │   │   └── telemetry/        # Ingest + query
│   │   ├── alembic/
│   │   └── tests/
│   └── simulator/                # Four microservices + scenarios
│       ├── gateway/
│       ├── user_service/
│       ├── order_service/
│       ├── payment_service/
│       ├── common/
│       └── scenarios/
├── packages/
│   └── shared-contracts/         # OpenAPI, JSON Schema, TS/Py types
├── infrastructure/
│   ├── docker/                   # Dockerfiles
│   ├── prometheus/
│   └── grafana/
├── airflow/                      # Evaluation/reporting DAGs
├── datasets/
│   ├── incidents/                # Seeded walkthrough incidents
│   └── evaluation/               # Versioned eval sets
├── scripts/                      # Dev helpers
├── docs/                         # Architecture, ADRs, guides
├── .github/workflows/
├── docker-compose.yml
├── .env.example
└── README.md
```
