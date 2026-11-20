import os


class SimulatorSettings:
    def __init__(self, service_name: str, port: int) -> None:
        self.service_name = service_name
        self.port = port
        self.environment = os.getenv("APP_ENV", "local")
        self.api_base_url = os.getenv("SENTINELAI_API_URL", "http://localhost:8000/api/v1")
        self.simulator_token = os.getenv("SIMULATOR_INTERNAL_TOKEN", "change-me-simulator-token")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.database_url = os.getenv(
            "SIM_DATABASE_URL",
            "postgresql://sentinelai:sentinelai@localhost:5432/sentinelai",
        )
        self.traffic_interval_seconds = float(os.getenv("TRAFFIC_INTERVAL_SECONDS", "2"))
