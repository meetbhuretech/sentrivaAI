"""Optional background detection loop for local demos."""

from __future__ import annotations

import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.detection.engine import DetectionEngine
from app.detection.rules import DetectionThresholds

logger = logging.getLogger(__name__)


async def detection_loop(interval_seconds: float = 30.0) -> None:
    engine = DetectionEngine(DetectionThresholds())
    while True:
        try:
            async with AsyncSessionLocal() as session:
                result = await engine.run(session)
                await session.commit()
                logger.info(
                    "scheduled detection: candidates=%s incidents_created=%s",
                    len(result.candidates),
                    result.incidents_created,
                )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("scheduled detection failed")
        await asyncio.sleep(interval_seconds)
