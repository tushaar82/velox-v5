"""Application configuration management."""
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "Velox Trading Platform"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://velox:velox_password@localhost:5432/velox_trading",
        env="DATABASE_URL",
    )

    # TimescaleDB
    TIMESCALE_URL: str = Field(
        default="postgresql+asyncpg://velox:velox_password@localhost:5433/velox_timeseries",
        env="TIMESCALE_URL",
    )

    # Redis
    REDIS_URL: str = Field(default="redis://:velox_redis@localhost:6379/0", env="REDIS_URL")

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:29092", env="KAFKA_BOOTSTRAP_SERVERS"
    )

    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-here-change-in-production", env="API_SECRET_KEY"
    )
    ALGORITHM: str = Field(default="HS256", env="API_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://frontend:3000",
    ]

    # WebSocket
    WS_MESSAGE_QUEUE_SIZE: int = 100
    WS_HEARTBEAT_INTERVAL: int = 30

    # Trading
    MAX_POSITIONS_PER_STRATEGY: int = 10
    MAX_STRATEGIES_PER_USER: int = 20
    TICK_PROCESSING_BATCH_SIZE: int = 100

    # Performance
    CACHE_TTL: int = 300  # seconds
    MAX_CONCURRENT_REQUESTS: int = 100

    # Monitoring
    METRICS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
