"""Airflow DAG — scheduled SENTINELAI evaluation (optional profile).

This DAG calls the API evaluation endpoint. It does not fabricate scores.
Requires AIRFLOW + API connectivity when the compose airflow profile is enabled.
"""

from __future__ import annotations

from datetime import datetime

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:  # pragma: no cover - airflow optional locally
    DAG = None  # type: ignore
    PythonOperator = None  # type: ignore


def trigger_evaluation(**_context) -> str:
    import os

    import httpx

    base = os.getenv("SENTINELAI_API_URL", "http://api:8000/api/v1")
    email = os.getenv("EVAL_USER_EMAIL", "admin@example.com")
    password = os.getenv("EVAL_USER_PASSWORD", "ChangeMeAdmin123!")
    with httpx.Client(timeout=120.0) as client:
        login = client.post(f"{base}/auth/login", json={"email": email, "password": password})
        login.raise_for_status()
        token = login.json()["access_token"]
        resp = client.post(
            f"{base}/evaluation/runs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "dataset_version": "v1",
                "provider": os.getenv("EVAL_PROVIDER", "deterministic"),
                "model": os.getenv("EVAL_MODEL", "rules-v1"),
            },
        )
        resp.raise_for_status()
        return resp.json()["id"]


if DAG is not None:
    with DAG(
        dag_id="sentinelai_evaluation_v1",
        start_date=datetime(2026, 1, 1),
        schedule="0 6 * * *",
        catchup=False,
        tags=["sentinelai", "evaluation"],
    ) as dag:
        PythonOperator(
            task_id="run_evaluation",
            python_callable=trigger_evaluation,
        )
