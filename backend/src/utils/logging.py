"""
Logging and monitoring utilities for the trading platform.
Provides structured logging with performance metrics tracking.
"""
import logging
import sys
import time
from typing import Any, Dict, Optional
from functools import wraps
import structlog
from pythonjsonlogger import jsonlogger


class PerformanceMonitor:
    """Tracks performance metrics for scalability monitoring."""

    def __init__(self) -> None:
        self.metrics: Dict[str, list] = {
            "tick_processing_latency": [],
            "indicator_update_latency": [],
            "trade_execution_latency": [],
            "dashboard_update_latency": [],
            "risk_management_latency": [],
        }

    def record_metric(self, metric_name: str, value: float) -> None:
        """Record a performance metric."""
        if metric_name in self.metrics:
            self.metrics[metric_name].append(value)
        else:
            self.metrics[metric_name] = [value]

    def get_average(self, metric_name: str) -> Optional[float]:
        """Get average value for a metric."""
        if metric_name in self.metrics and self.metrics[metric_name]:
            return sum(self.metrics[metric_name]) / len(self.metrics[metric_name])
        return None

    def get_percentile(self, metric_name: str, percentile: int = 95) -> Optional[float]:
        """Get percentile value for a metric."""
        if metric_name in self.metrics and self.metrics[metric_name]:
            sorted_values = sorted(self.metrics[metric_name])
            index = int(len(sorted_values) * (percentile / 100))
            return sorted_values[min(index, len(sorted_values) - 1)]
        return None

    def clear_metrics(self) -> None:
        """Clear all recorded metrics."""
        for key in self.metrics:
            self.metrics[key] = []


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def setup_logging(log_level: str = "INFO") -> None:
    """Setup structured logging with JSON formatter."""
    # Configure standard logging
    log_handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    log_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def log_performance(metric_name: str):
    """Decorator to log performance metrics."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms
                performance_monitor.record_metric(metric_name, elapsed)
                logger = get_logger(func.__name__)
                logger.info(
                    f"{metric_name}_completed",
                    duration_ms=elapsed,
                    function=func.__name__
                )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms
                performance_monitor.record_metric(metric_name, elapsed)
                logger = get_logger(func.__name__)
                logger.info(
                    f"{metric_name}_completed",
                    duration_ms=elapsed,
                    function=func.__name__
                )

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_strategy_execution(
    strategy_id: str,
    action: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log strategy execution events."""
    logger = get_logger("strategy_execution")
    logger.info(
        "strategy_execution",
        strategy_id=strategy_id,
        action=action,
        details=details or {}
    )


def log_risk_event(
    event_type: str,
    severity: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log risk management events."""
    logger = get_logger("risk_management")
    log_method = getattr(logger, severity.lower(), logger.info)
    log_method(
        "risk_event",
        event_type=event_type,
        details=details or {}
    )


def log_trading_mode_event(
    strategy_id: str,
    old_mode: str,
    new_mode: str,
    user_id: str
) -> None:
    """Log trading mode changes."""
    logger = get_logger("trading_mode")
    logger.info(
        "trading_mode_change",
        strategy_id=strategy_id,
        old_mode=old_mode,
        new_mode=new_mode,
        user_id=user_id
    )


def log_trailing_stoploss_event(
    position_id: str,
    event: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log trailing stoploss events."""
    logger = get_logger("trailing_stoploss")
    logger.info(
        "trailing_stoploss_event",
        position_id=position_id,
        event=event,
        details=details or {}
    )


def log_broker_event(
    broker_name: str,
    event: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log broker-related events."""
    logger = get_logger("broker")
    logger.info(
        "broker_event",
        broker_name=broker_name,
        event=event,
        details=details or {}
    )


def log_backtesting_event(
    backtest_id: str,
    event: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log backtesting events."""
    logger = get_logger("backtesting")
    logger.info(
        "backtesting_event",
        backtest_id=backtest_id,
        event=event,
        details=details or {}
    )


def log_user_management_event(
    user_id: str,
    event: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log user management events."""
    logger = get_logger("user_management")
    logger.info(
        "user_management_event",
        user_id=user_id,
        event=event,
        details=details or {}
    )
