import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.app_factory import create_service_app
from common.failures import FAILURES


async def route() -> dict:
    if FAILURES.redis_down():
        return {"routed": False, "error": "redis_unavailable"}
    return {"routed": True, "service": "api-gateway"}


app = create_service_app("api-gateway", 8100, handlers={"/api/route": route})

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8100)
