import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import HTTPException

from common.app_factory import create_service_app
from common.failures import FAILURES


async def charge() -> dict:
    if FAILURES.redis_down():
        raise HTTPException(status_code=503, detail="Redis unavailable for payment idempotency")
    return {"payment_id": "pay-300", "status": "authorized", "service": "payment-service"}


app = create_service_app("payment-service", 8103, handlers={"/api/payments/charge": charge})

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8103)
