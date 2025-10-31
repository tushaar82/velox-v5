"""
Performance monitoring utilities for scalability tracking.
Integrates with Prometheus for metrics collection.
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Dict


# Performance metrics
tick_processing_histogram = Histogram(
    'tick_processing_duration_milliseconds',
    'Time spent processing market ticks',
    buckets=[10, 25, 50, 75, 100, 250, 500, 1000]
)

indicator_update_histogram = Histogram(
    'indicator_update_duration_milliseconds',
    'Time spent updating indicators',
    buckets=[10, 25, 50, 75, 100, 250, 500, 1000]
)

trade_execution_histogram = Histogram(
    'trade_execution_duration_milliseconds',
    'Time spent executing trades',
    buckets=[10, 25, 50, 75, 100, 250, 500, 1000]
)

dashboard_update_histogram = Histogram(
    'dashboard_update_duration_milliseconds',
    'Time spent updating dashboard',
    buckets=[100, 250, 500, 750, 1000, 2500, 5000]
)

risk_management_histogram = Histogram(
    'risk_management_duration_milliseconds',
    'Time spent on risk management checks',
    buckets=[10, 25, 50, 75, 100, 200, 500]
)

# Business metrics
active_strategies_gauge = Gauge(
    'active_strategies_total',
    'Number of active trading strategies'
)

open_positions_gauge = Gauge(
    'open_positions_total',
    'Number of open positions'
)

total_trades_counter = Counter(
    'total_trades_executed',
    'Total number of trades executed',
    ['strategy_id', 'symbol', 'side']
)

risk_limit_breaches_counter = Counter(
    'risk_limit_breaches_total',
    'Number of risk limit breaches',
    ['limit_type']
)

# System metrics
websocket_connections_gauge = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections'
)

database_query_histogram = Histogram(
    'database_query_duration_milliseconds',
    'Database query execution time',
    buckets=[1, 5, 10, 25, 50, 100, 250, 500]
)

cache_hit_counter = Counter(
    'cache_hits_total',
    'Number of cache hits',
    ['cache_type']
)

cache_miss_counter = Counter(
    'cache_misses_total',
    'Number of cache misses',
    ['cache_type']
)


class PerformanceTracker:
    """Context manager for tracking performance metrics."""

    def __init__(self, histogram: Histogram):
        self.histogram = histogram
        self.start_time = None

    def __enter__(self):
        import time
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        if self.start_time:
            duration_ms = (time.perf_counter() - self.start_time) * 1000
            self.histogram.observe(duration_ms)


def get_metrics_summary() -> Dict[str, any]:
    """Get summary of current metrics."""
    return {
        "active_strategies": active_strategies_gauge._value.get(),
        "open_positions": open_positions_gauge._value.get(),
        "websocket_connections": websocket_connections_gauge._value.get(),
    }
