"""
Application configuration management.
Uses pydantic-settings for environment variable validation.
"""
from functools import lru_cache
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Velox Trading Platform"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://velox:velox_password@localhost:5432/velox_trading",
        description="PostgreSQL connection URL"
    )
    TIMESCALE_URL: str = Field(
        default="postgresql+asyncpg://velox:velox_password@localhost:5433/velox_market_data",
        description="TimescaleDB connection URL"
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://:velox_redis_password@localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_MAX_CONNECTIONS: int = 50

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers"
    )
    KAFKA_MARKET_DATA_TOPIC: str = "market_data"
    KAFKA_TRADE_EXECUTION_TOPIC: str = "trade_execution"
    KAFKA_CONSUMER_GROUP: str = "velox_trading_group"

    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT encoding"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )

    # API
    API_V1_PREFIX: str = "/api/v1"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Trading Configuration
    MAX_ACTIVE_STRATEGIES: int = 10
    MAX_POSITIONS_PER_STRATEGY: int = 50
    DEFAULT_RISK_PERCENTAGE: float = 2.0
    MAX_DAILY_LOSS_PERCENTAGE: float = 5.0

    # Performance Thresholds (milliseconds)
    TICK_PROCESSING_TARGET_MS: int = 50
    INDICATOR_UPDATE_TARGET_MS: int = 50
    TRADE_EXECUTION_TARGET_MS: int = 100
    DASHBOARD_UPDATE_TARGET_MS: int = 1000
    RISK_MANAGEMENT_TARGET_MS: int = 200

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MESSAGE_QUEUE_SIZE: int = 1000

    # Monitoring
    PROMETHEUS_METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9090

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("KAFKA_BOOTSTRAP_SERVERS")
    @classmethod
    def validate_kafka_servers(cls, v: str) -> str:
        """Validate Kafka bootstrap servers format."""
        if not v:
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS cannot be empty")
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key."""
        if v == "your-secret-key-change-in-production":
            raise ValueError(
                "SECRET_KEY must be changed from default value in production"
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
