"""
CORS middleware configuration.
"""
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from ...core.config import get_settings


settings = get_settings()


def setup_cors(app: FastAPI) -> None:
    """
    Setup CORS middleware.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )
