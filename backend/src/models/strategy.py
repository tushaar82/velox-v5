"""
Strategy-related database models.
Includes Strategy, StrategyInstance, and BacktestResult models.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Float, Integer, DateTime, JSON, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from .database import Base


class TradingMode(str, enum.Enum):
    """Trading mode enumeration."""
    LIVE = "live"
    PAPER = "paper"


class StrategyStatus(str, enum.Enum):
    """Strategy status enumeration."""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class StrategyType(str, enum.Enum):
    """Strategy type enumeration."""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    ARBITRAGE = "arbitrage"
    CUSTOM = "custom"


class Strategy(Base):
    """Trading strategy definition."""

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strategy_type: Mapped[StrategyType] = mapped_column(SQLEnum(StrategyType), nullable=False)

    # Strategy code or configuration
    code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    configuration: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Strategy parameters
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Version control
    version: Mapped[int] = mapped_column(Integer, default=1)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    instances: Mapped[list["StrategyInstance"]] = relationship(
        "StrategyInstance", back_populates="strategy", cascade="all, delete-orphan"
    )
    backtest_results: Mapped[list["BacktestResult"]] = relationship(
        "BacktestResult", back_populates="strategy", cascade="all, delete-orphan"
    )


class StrategyInstance(Base):
    """Active instance of a trading strategy."""

    __tablename__ = "strategy_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(Integer, ForeignKey("strategies.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[StrategyStatus] = mapped_column(SQLEnum(StrategyStatus), default=StrategyStatus.STOPPED)
    trading_mode: Mapped[TradingMode] = mapped_column(SQLEnum(TradingMode), default=TradingMode.PAPER)

    # Symbols this instance is trading
    symbols: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Instance-specific parameters (overrides strategy defaults)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Risk management
    max_position_size: Mapped[float] = mapped_column(Float, default=10000.0)
    max_daily_loss: Mapped[float] = mapped_column(Float, default=1000.0)
    trailing_stoploss_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    trailing_stoploss_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Broker configuration
    broker_account_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("broker_accounts.id"), nullable=True
    )

    # Performance tracking
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="instances")


class BacktestResult(Base):
    """Backtesting results for a strategy."""

    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(Integer, ForeignKey("strategies.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Backtest configuration
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    symbols: Mapped[list] = mapped_column(JSON, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Float, nullable=False)

    # Performance metrics
    total_return: Mapped[float] = mapped_column(Float, default=0.0)
    total_return_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    annualized_return: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown_percentage: Mapped[float] = mapped_column(Float, default=0.0)

    # Trading statistics
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Risk metrics
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sortino_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calmar_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Additional metrics
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Trade details
    trades: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="backtest_results")
