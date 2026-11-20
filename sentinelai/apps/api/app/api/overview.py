import asyncio
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.sse import sse_pack, user_from_access_token
from app.core.database import AsyncSessionLocal
from app.core.deps import CurrentUser, DbSession
from app.models.user import User
from app.schemas.overview import OverviewResponse
from app.services.overview import build_overview

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=OverviewResponse)
async def get_overview(
    db: DbSession,
    _user: CurrentUser,
    service: str | None = Query(default=None),
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
) -> OverviewResponse:
    return await build_overview(db, service_name=service, from_ts=from_ts, to_ts=to_ts)


@router.get("/stream")
async def overview_stream(
    _user: Annotated[User, Depends(user_from_access_token)],
    service: str | None = Query(default=None),
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    max_events: int | None = Query(default=None, ge=1, le=100),
) -> StreamingResponse:
    async def events():
        sent = 0
        while True:
            async with AsyncSessionLocal() as db:
                overview = await build_overview(
                    db, service_name=service, from_ts=from_ts, to_ts=to_ts
                )
            yield sse_pack("overview", overview)
            sent += 1
            if max_events is not None and sent >= max_events:
                return
            await asyncio.sleep(5)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
