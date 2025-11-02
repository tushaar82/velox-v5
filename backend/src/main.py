"""Main FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.api.middleware.cors import setup_cors
from src.api.middleware.error_handler import ErrorHandlerMiddleware
from src.core.config import settings
from src.core.redis_client import redis_client
from src.models.database import init_db
from src.services.market_data.kafka_consumer import market_data_consumer, market_data_producer
from src.utils.logging import get_logger, setup_logging
from src.utils.monitoring import get_metrics

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("application_startup", version=settings.VERSION)

    # Initialize database
    try:
        await init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))

    # Connect to Redis
    try:
        await redis_client.connect()
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))

    # Start Kafka producer
    try:
        await market_data_producer.start()
    except Exception as e:
        logger.error("kafka_producer_start_failed", error=str(e))

    # Start Kafka consumer (in background)
    # Note: In production, this should be a separate service
    # asyncio.create_task(market_data_consumer.run())

    yield

    # Shutdown
    logger.info("application_shutdown")

    # Disconnect from Redis
    await redis_client.disconnect()

    # Stop Kafka
    await market_data_consumer.stop()
    await market_data_producer.stop()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="High-Frequency Algorithmic Trading Platform",
    lifespan=lifespan,
)

# Setup CORS
setup_cors(app)

# Add error handling middleware
app.add_middleware(ErrorHandlerMiddleware)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
        }
    )


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return JSONResponse(content=get_metrics().decode("utf-8"))


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return JSONResponse(
        content={
            "message": "Velox Trading Platform API",
            "version": settings.VERSION,
            "docs": "/docs",
        }
    )


# API routes will be added here
# from src.api.endpoints import auth, trading, strategies, analytics, market_data
# app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
# app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
# app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
# app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
# app.include_router(market_data.router, prefix="/api/market-data", tags=["market-data"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
