"""Market data models for time-series data."""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from src.models.database import Base


class Tick(Base):
    """Real-time tick data model (stored in TimescaleDB)."""

    __tablename__ = "ticks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    last_price = Column(Float, nullable=False)
    last_quantity = Column(Float, nullable=False)
    bid_price = Column(Float)
    bid_quantity = Column(Float)
    ask_price = Column(Float)
    ask_quantity = Column(Float)
    volume = Column(Float, nullable=False)
    open_interest = Column(Float)

    __table_args__ = (
        Index("idx_ticks_symbol_timestamp", "symbol", "timestamp"),
        # TimescaleDB hypertable creation will be done via migration
    )


class Candle(Base):
    """OHLCV candle data model (stored in TimescaleDB)."""

    __tablename__ = "candles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol = Column(String(50), nullable=False, index=True)
    timeframe = Column(String(20), nullable=False, index=True)  # e.g., "1m", "5m", "1h"
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    trades = Column(Integer)  # Number of trades in this candle

    __table_args__ = (
        Index("idx_candles_symbol_timeframe_timestamp", "symbol", "timeframe", "timestamp"),
        # TimescaleDB hypertable creation will be done via migration
    )


class IndicatorValue(Base):
    """Technical indicator values (stored in TimescaleDB)."""

    __tablename__ = "indicator_values"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol = Column(String(50), nullable=False, index=True)
    timeframe = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    indicator_name = Column(String(100), nullable=False, index=True)
    value = Column(Float, nullable=False)
    metadata = Column(String(500))  # Additional indicator-specific data

    __table_args__ = (
        Index(
            "idx_indicator_values_symbol_timeframe_indicator_timestamp",
            "symbol",
            "timeframe",
            "indicator_name",
            "timestamp",
        ),
        # TimescaleDB hypertable creation will be done via migration
    )
