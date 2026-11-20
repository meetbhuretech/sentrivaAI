"""In-process failure injection controlled by seed + scenario + duration."""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActiveScenario:
    name: str
    seed: int
    duration_seconds: int
    started_at: float
    rng: random.Random
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def remaining(self) -> float:
        return max(0.0, self.duration_seconds - (time.time() - self.started_at))

    @property
    def active(self) -> bool:
        return self.remaining > 0


class FailureController:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._scenario: ActiveScenario | None = None

    def start(self, name: str, seed: int, duration_seconds: int, **params: Any) -> ActiveScenario:
        with self._lock:
            scenario = ActiveScenario(
                name=name,
                seed=seed,
                duration_seconds=duration_seconds,
                started_at=time.time(),
                rng=random.Random(seed),
                params=params,
            )
            self._scenario = scenario
            return scenario

    def stop(self) -> None:
        with self._lock:
            self._scenario = None

    def current(self) -> ActiveScenario | None:
        with self._lock:
            if self._scenario and not self._scenario.active:
                self._scenario = None
            return self._scenario

    def should_http_500(self) -> bool:
        sc = self.current()
        if not sc or sc.name not in {"http_500_spike", "bad_deployment"}:
            return False
        rate = float(sc.params.get("error_rate", 0.4))
        return sc.rng.random() < rate

    def latency_multiplier(self) -> float:
        sc = self.current()
        if not sc:
            return 1.0
        if sc.name in {"increased_latency", "dependency_timeout", "slow_db_queries"}:
            return float(sc.params.get("latency_multiplier", 5.0))
        if sc.name == "bad_deployment":
            return float(sc.params.get("latency_multiplier", 2.5))
        return 1.0

    def extra_latency_ms(self) -> float:
        sc = self.current()
        if not sc:
            return 0.0
        base = self.latency_multiplier()
        if sc.name == "dependency_timeout":
            return float(sc.params.get("timeout_ms", 3000))
        if base <= 1.0:
            return 0.0
        return sc.rng.uniform(50, 200) * base

    def redis_down(self) -> bool:
        sc = self.current()
        return bool(sc and sc.name == "redis_connection_failure")

    def memory_pressure(self) -> bool:
        sc = self.current()
        return bool(sc and sc.name == "memory_pressure")

    def db_slow(self) -> bool:
        sc = self.current()
        return bool(sc and sc.name == "slow_db_queries")

    def background_job_fail(self) -> bool:
        sc = self.current()
        return bool(sc and sc.name == "failed_background_jobs")


FAILURES = FailureController()

SCENARIO_CATALOG = [
    {
        "name": "slow_db_queries",
        "description": "Injects artificial DB query latency",
        "default_params": {"latency_multiplier": 8.0},
    },
    {
        "name": "http_500_spike",
        "description": "Raises HTTP 500 error rate",
        "default_params": {"error_rate": 0.5},
    },
    {
        "name": "redis_connection_failure",
        "description": "Simulates Redis connection failures",
        "default_params": {},
    },
    {
        "name": "memory_pressure",
        "description": "Reports elevated memory utilization",
        "default_params": {"memory_percent": 92.0},
    },
    {
        "name": "increased_latency",
        "description": "Increases end-to-end latency",
        "default_params": {"latency_multiplier": 6.0},
    },
    {
        "name": "dependency_timeout",
        "description": "Simulates dependency timeouts",
        "default_params": {"timeout_ms": 3500},
    },
    {
        "name": "failed_background_jobs",
        "description": "Fails periodic background jobs",
        "default_params": {},
    },
    {
        "name": "bad_deployment",
        "description": "Regression after a bad deploy (errors + latency)",
        "default_params": {"error_rate": 0.35, "latency_multiplier": 3.0},
    },
]
