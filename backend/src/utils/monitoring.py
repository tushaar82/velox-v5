"""Performance monitoring and metrics collection."""
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator

from prometheus_client import Counter, Gauge, Histogram, generate_latest

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
)

strategy_executions = Counter(
    "strategy_executions_total",
    "Total strategy executions",
    ["strategy_id", "status"],
)

trade_orders = Counter(
    "trade_orders_total",
    "Total trade orders",
    ["symbol", "side", "status"],
)

active_strategies = Gauge(
    "active_strategies",
    "Number of active strategies",
)

active_positions = Gauge(
    "active_positions",
    "Number of active positions",
)

tick_processing_duration = Histogram(
    "tick_processing_duration_seconds",
    "Tick processing duration",
    ["symbol"],
)

order_execution_duration = Histogram(
    "order_execution_duration_seconds",
    "Order execution duration",
    ["broker"],
)

daily_pnl = Gauge(
    "daily_pnl",
    "Daily profit/loss",
    ["strategy_id"],
)

drawdown = Gauge(
    "drawdown",
    "Current drawdown",
    ["strategy_id"],
)


@contextmanager
def track_time(metric: Histogram, labels: Dict[str, Any]) -> Generator:
    """Context manager to track execution time."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        metric.labels(**labels).observe(duration)
        logger.debug("timing", metric=metric._name, duration=duration, **labels)


def record_http_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """Record HTTP request metrics."""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)


def record_strategy_execution(strategy_id: str, status: str) -> None:
    """Record strategy execution."""
    strategy_executions.labels(strategy_id=strategy_id, status=status).inc()


def record_trade_order(symbol: str, side: str, status: str) -> None:
    """Record trade order."""
    trade_orders.labels(symbol=symbol, side=side, status=status).inc()


def update_active_strategies(count: int) -> None:
    """Update active strategies count."""
    active_strategies.set(count)


def update_active_positions(count: int) -> None:
    """Update active positions count."""
    active_positions.set(count)


def update_daily_pnl(strategy_id: str, pnl: float) -> None:
    """Update daily PnL for a strategy."""
    daily_pnl.labels(strategy_id=strategy_id).set(pnl)


def update_drawdown(strategy_id: str, dd: float) -> None:
    """Update drawdown for a strategy."""
    drawdown.labels(strategy_id=strategy_id).set(dd)


def get_metrics() -> bytes:
    """Get Prometheus metrics."""
    return generate_latest()
