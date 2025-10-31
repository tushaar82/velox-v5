"""
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from prometheus_client import make_asgi_app

from .core.config import get_settings
from .core.redis_client import redis_client
from .models.database import DatabaseManager, db_manager as _db_manager
from .services.market_data.kafka_consumer import market_data_consumer, market_data_producer
from .utils.logging import setup_logging, get_logger
from .api.middleware import (
    validation_exception_handler,
    general_exception_handler,
    database_exception_handler,
    RateLimiterMiddleware,
    setup_cors
)


settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Manages startup and shutdown of connections and services.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")

    # Initialize database
    global _db_manager
    _db_manager = DatabaseManager(
        postgres_url=settings.DATABASE_URL,
        timescale_url=settings.TIMESCALE_URL,
        echo=settings.DEBUG
    )
    await _db_manager.create_tables()
    logger.info("Database initialized")

    # Initialize Redis
    await redis_client.connect()
    logger.info("Redis connected")

    # Initialize Kafka (optional - only if enabled)
    # await market_data_consumer.start()
    # await market_data_producer.start()
    # logger.info("Kafka initialized")

    yield

    # Shutdown
    logger.info("Shutting down application")

    # Close Kafka
    # await market_data_consumer.stop()
    # await market_data_producer.stop()

    # Close Redis
    await redis_client.disconnect()

    # Close database
    await _db_manager.close()

    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="High-Frequency Algorithmic Trading Platform",
    docs_url=settings.DOCS_URL if settings.DEBUG else None,
    redoc_url=settings.REDOC_URL if settings.DEBUG else None,
    lifespan=lifespan
)

# Setup CORS
setup_cors(app)

# Add middleware
app.add_middleware(RateLimiterMiddleware)

# Add exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Mount Prometheus metrics
if settings.PROMETHEUS_METRICS_ENABLED:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "docs": settings.DOCS_URL if settings.DEBUG else None
    }


# Import and include routers
from .api.endpoints import strategies, trading, market_data, risk

app.include_router(strategies.router, prefix=f"{settings.API_V1_PREFIX}/strategies", tags=["strategies"])
app.include_router(trading.router, prefix=f"{settings.API_V1_PREFIX}/trading", tags=["trading"])
app.include_router(market_data.router, prefix=f"{settings.API_V1_PREFIX}/market-data", tags=["market-data"])
app.include_router(risk.router, prefix=f"{settings.API_V1_PREFIX}/risk", tags=["risk"])

# TODO: Add remaining routers as we implement more user stories
# from .api.endpoints import auth, analytics
# app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])
# app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["analytics"])
