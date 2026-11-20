import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.app_factory import create_service_app
from common.failures import FAILURES


async def create_order() -> dict:
    current = FAILURES.current()
    if FAILURES.db_slow() or (current and current.name == "dependency_timeout"):
        await asyncio.sleep(max(FAILURES.extra_latency_ms(), 1) / 1000.0)
    if FAILURES.background_job_fail():
        return {"status": "accepted", "warning": "async_job_degraded"}
    return {"order_id": "ord-200", "status": "created", "service": "order-service"}


app = create_service_app("order-service", 8102, handlers={"/api/orders": create_order})

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8102)
