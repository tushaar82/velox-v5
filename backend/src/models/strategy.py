"""Strategy models and related entities."""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.database import Base


class StrategyStatus(str, Enum):
    """Strategy status enumeration."""

    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class TradingMode(str, Enum):
    """Trading mode enumeration."""

    LIVE = "live"
    PAPER = "paper"


class StrategyInstance(Base):
    """Strategy instance model."""

    __tablename__ = "strategy_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    strategy_code = Column(Text, nullable=False)  # Python code for the strategy
    parameters = Column(JSON, nullable=False)  # Strategy-specific parameters
    symbols = Column(JSON, nullable=False)  # List of symbols to trade
    timeframe = Column(String(20), nullable=False)  # e.g., "1m", "5m", "1h"
    status = Column(SQLEnum(StrategyStatus), default=StrategyStatus.PAUSED, nullable=False)
    trading_mode = Column(SQLEnum(TradingMode), default=TradingMode.PAPER, nullable=False)
    max_positions = Column(Integer, default=5, nullable=False)
    position_size = Column(Float, nullable=False)  # Position size per trade
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime)
    stopped_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="strategies")
    performance = relationship(
        "StrategyPerformance", back_populates="strategy", cascade="all, delete-orphan"
    )
    backtest_results = relationship(
        "BacktestResult", back_populates="strategy", cascade="all, delete-orphan"
    )


class BacktestResult(Base):
    """Backtest results for strategies."""

    __tablename__ = "backtest_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("strategy_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    losing_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    profit_factor = Column(Float, nullable=False)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float, nullable=False)
    avg_trade_duration = Column(Float)  # in seconds
    parameters = Column(JSON)  # Parameters used for this backtest
    trades = Column(JSON)  # All trades from the backtest
    equity_curve = Column(JSON)  # Equity curve data points
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    strategy = relationship("StrategyInstance", back_populates="backtest_results")
