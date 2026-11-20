import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.app_factory import create_service_app
from common.failures import FAILURES


async def get_user() -> dict:
    if FAILURES.db_slow():
        await asyncio.sleep(FAILURES.extra_latency_ms() / 1000.0)
    return {"id": "u-100", "email": "user@example.com", "service": "user-service"}


app = create_service_app("user-service", 8101, handlers={"/api/users/me": get_user})

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8101)
