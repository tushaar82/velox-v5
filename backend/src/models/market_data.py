"""
Market data models for time-series data in TimescaleDB.
Includes Tick, Candle, and IndicatorValue models.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, DateTime, BigInteger, Index, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum
from .database import TimescaleBase


class CandleInterval(str, enum.Enum):
    """Candle interval enumeration."""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"


class Tick(TimescaleBase):
    """Real-time tick data stored in TimescaleDB."""

    __tablename__ = "ticks"

    # TimescaleDB uses time as the primary dimension
    time: Mapped[datetime] = mapped_column(DateTime, primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), primary_key=True, nullable=False)

    # Price data
    price: Mapped[float] = mapped_column(Float, nullable=False)
    bid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ask: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Volume
    volume: Mapped[int] = mapped_column(Integer, default=0)
    bid_volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ask_volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    exchange: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        Index('ix_ticks_symbol_time', 'symbol', 'time'),
        Index('ix_ticks_time', 'time'),
    )


class Candle(TimescaleBase):
    """OHLCV candle data stored in TimescaleDB."""

    __tablename__ = "candles"

    # TimescaleDB dimensions
    time: Mapped[datetime] = mapped_column(DateTime, primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), primary_key=True, nullable=False)
    interval: Mapped[CandleInterval] = mapped_column(
        SQLEnum(CandleInterval), primary_key=True, nullable=False
    )

    # OHLCV data
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, default=0)

    # Additional metrics
    trades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vwap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index('ix_candles_symbol_interval_time', 'symbol', 'interval', 'time'),
        Index('ix_candles_time', 'time'),
    )


class IndicatorValue(TimescaleBase):
    """Technical indicator values stored in TimescaleDB."""

    __tablename__ = "indicator_values"

    # TimescaleDB dimensions
    time: Mapped[datetime] = mapped_column(DateTime, primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), primary_key=True, nullable=False)
    indicator_name: Mapped[str] = mapped_column(String(100), primary_key=True, nullable=False)
    strategy_instance_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    # Indicator value (can be composite for multi-line indicators like Bollinger Bands)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    # For multi-line indicators (e.g., upper/middle/lower bands)
    line_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        Index('ix_indicator_values_symbol_strategy_time', 'symbol', 'strategy_instance_id', 'time'),
        Index('ix_indicator_values_time', 'time'),
    )


# Note: After creating these tables in TimescaleDB, you need to run SQL to convert them to hypertables:
# SELECT create_hypertable('ticks', 'time', if_not_exists => TRUE);
# SELECT create_hypertable('candles', 'time', if_not_exists => TRUE);
# SELECT create_hypertable('indicator_values', 'time', if_not_exists => TRUE);
