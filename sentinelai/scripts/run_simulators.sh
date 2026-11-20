#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps/simulator"

if [[ ! -d .venv ]]; then
  python3.13 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi

export SENTINELAI_API_URL="${SENTINELAI_API_URL:-http://localhost:8000/api/v1}"
export SIMULATOR_INTERNAL_TOKEN="${SIMULATOR_INTERNAL_TOKEN:-change-me-simulator-token}"
export TRAFFIC_INTERVAL_SECONDS="${TRAFFIC_INTERVAL_SECONDS:-2}"

uvicorn gateway.main:app --app-dir . --host 0.0.0.0 --port 8100 &
uvicorn user_service.main:app --app-dir . --host 0.0.0.0 --port 8101 &
uvicorn order_service.main:app --app-dir . --host 0.0.0.0 --port 8102 &
uvicorn payment_service.main:app --app-dir . --host 0.0.0.0 --port 8103 &

echo "Simulators started on 8100-8103"
wait
