"""Structured logging and error handling utilities."""
import logging
import sys
from typing import Any, Dict

import structlog
from pythonjsonlogger import jsonlogger

from src.core.config import settings


def setup_logging() -> None:
    """Setup structured logging for the application."""
    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format="%(message)s",
        stream=sys.stdout,
    )

    # Configure JSON formatter
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s %(pathname)s %(lineno)d"
    )
    logHandler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.addHandler(logHandler)
    logger.setLevel(settings.LOG_LEVEL)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def log_strategy_execution(
    logger: structlog.BoundLogger,
    strategy_id: str,
    symbol: str,
    action: str,
    details: Dict[str, Any],
) -> None:
    """Log strategy execution events."""
    logger.info(
        "strategy_execution",
        strategy_id=strategy_id,
        symbol=symbol,
        action=action,
        **details,
    )


def log_trade_order(
    logger: structlog.BoundLogger,
    order_id: str,
    symbol: str,
    order_type: str,
    side: str,
    quantity: float,
    price: float,
    status: str,
) -> None:
    """Log trade order events."""
    logger.info(
        "trade_order",
        order_id=order_id,
        symbol=symbol,
        order_type=order_type,
        side=side,
        quantity=quantity,
        price=price,
        status=status,
    )


def log_risk_management(
    logger: structlog.BoundLogger,
    event_type: str,
    strategy_id: str,
    details: Dict[str, Any],
) -> None:
    """Log risk management events."""
    logger.warning(
        "risk_management",
        event_type=event_type,
        strategy_id=strategy_id,
        **details,
    )


def log_trailing_stoploss(
    logger: structlog.BoundLogger,
    position_id: str,
    symbol: str,
    action: str,
    old_stop: float,
    new_stop: float,
) -> None:
    """Log trailing stoploss events."""
    logger.info(
        "trailing_stoploss",
        position_id=position_id,
        symbol=symbol,
        action=action,
        old_stop=old_stop,
        new_stop=new_stop,
    )


def log_broker_event(
    logger: structlog.BoundLogger,
    broker_name: str,
    event_type: str,
    details: Dict[str, Any],
) -> None:
    """Log broker-related events."""
    logger.info(
        "broker_event",
        broker_name=broker_name,
        event_type=event_type,
        **details,
    )


def log_backtesting(
    logger: structlog.BoundLogger,
    strategy_id: str,
    start_date: str,
    end_date: str,
    results: Dict[str, Any],
) -> None:
    """Log backtesting events."""
    logger.info(
        "backtesting",
        strategy_id=strategy_id,
        start_date=start_date,
        end_date=end_date,
        **results,
    )


def log_user_management(
    logger: structlog.BoundLogger,
    user_id: str,
    action: str,
    details: Dict[str, Any],
) -> None:
    """Log user management events."""
    logger.info(
        "user_management",
        user_id=user_id,
        action=action,
        **details,
    )


def log_trading_mode(
    logger: structlog.BoundLogger,
    strategy_id: str,
    old_mode: str,
    new_mode: str,
) -> None:
    """Log trading mode change events."""
    logger.info(
        "trading_mode_change",
        strategy_id=strategy_id,
        old_mode=old_mode,
        new_mode=new_mode,
    )


class ErrorHandler:
    """Centralized error handling."""

    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger

    def handle_database_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle database errors."""
        self.logger.error(
            "database_error",
            error=str(error),
            error_type=type(error).__name__,
            **context,
        )

    def handle_api_error(self, error: Exception, endpoint: str, context: Dict[str, Any]) -> None:
        """Handle API errors."""
        self.logger.error(
            "api_error",
            error=str(error),
            error_type=type(error).__name__,
            endpoint=endpoint,
            **context,
        )

    def handle_strategy_error(
        self, error: Exception, strategy_id: str, context: Dict[str, Any]
    ) -> None:
        """Handle strategy execution errors."""
        self.logger.error(
            "strategy_error",
            error=str(error),
            error_type=type(error).__name__,
            strategy_id=strategy_id,
            **context,
        )

    def handle_broker_error(
        self, error: Exception, broker_name: str, context: Dict[str, Any]
    ) -> None:
        """Handle broker integration errors."""
        self.logger.error(
            "broker_error",
            error=str(error),
            error_type=type(error).__name__,
            broker_name=broker_name,
            **context,
        )
