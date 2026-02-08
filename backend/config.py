import os
from typing import Optional


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/retrosynthesis"
    )

    MICROSERVICE_URL: str = os.getenv(
        "MICROSERVICE_URL",
        "http://localhost:8001"
    )

    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    CALLBACK_HOST: str = os.getenv("CALLBACK_HOST", "localhost")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
