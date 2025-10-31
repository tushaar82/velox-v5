"""
Trading-related database models.
Includes TradeOrder, Position, TrailingStoploss, TradeExecution,
StrategyPerformance, and PerformanceMetrics models.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, DateTime, Enum as SQLEnum, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from .database import Base


class OrderType(str, enum.Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, enum.Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, enum.Enum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionStatus(str, enum.Enum):
    """Position status enumeration."""
    OPEN = "open"
    CLOSED = "closed"


class TradeOrder(Base):
    """Trade order model."""

    __tablename__ = "trade_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("strategy_instances.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Order details
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    order_type: Mapped[OrderType] = mapped_column(SQLEnum(OrderType), nullable=False)
    side: Mapped[OrderSide] = mapped_column(SQLEnum(OrderSide), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Price information
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stop_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    filled_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    filled_quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Order status
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)

    # Broker information
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    filled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Additional information
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Position(Base):
    """Trading position model."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("strategy_instances.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Position details
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    side: Mapped[OrderSide] = mapped_column(SQLEnum(OrderSide), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Entry information
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Exit information
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Current price and P&L
    current_price: Mapped[float] = mapped_column(Float, nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Position status
    status: Mapped[PositionStatus] = mapped_column(SQLEnum(PositionStatus), default=PositionStatus.OPEN)

    # Stop loss and take profit
    stop_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    take_profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    trailing_stoploss: Mapped[Optional["TrailingStoploss"]] = relationship(
        "TrailingStoploss", back_populates="position", uselist=False, cascade="all, delete-orphan"
    )


class TrailingStoploss(Base):
    """Trailing stoploss configuration for a position."""

    __tablename__ = "trailing_stoplosses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    position_id: Mapped[int] = mapped_column(Integer, ForeignKey("positions.id"), unique=True, nullable=False)

    # Trailing configuration
    trailing_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    trailing_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Current trailing values
    highest_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_stop_price: Mapped[float] = mapped_column(Float, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    position: Mapped["Position"] = relationship("Position", back_populates="trailing_stoploss")


class TradeExecution(Base):
    """Trade execution record from broker."""

    __tablename__ = "trade_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("trade_orders.id"), nullable=False)
    broker_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("broker_accounts.id"), nullable=False
    )

    # Execution details
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[OrderSide] = mapped_column(SQLEnum(OrderSide), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    # Broker information
    broker_execution_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    broker_order_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Fees and costs
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    tax: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)

    # Timestamp
    executed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StrategyPerformance(Base):
    """Strategy performance tracking."""

    __tablename__ = "strategy_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("strategy_instances.id"), nullable=False, unique=True
    )

    # Performance metrics
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    total_pnl_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)

    # Trading statistics
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Position statistics
    total_positions: Mapped[int] = mapped_column(Integer, default=0)
    open_positions: Mapped[int] = mapped_column(Integer, default=0)
    closed_positions: Mapped[int] = mapped_column(Integer, default=0)

    # Risk metrics
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    current_drawdown: Mapped[float] = mapped_column(Float, default=0.0)

    # Return metrics
    daily_return: Mapped[float] = mapped_column(Float, default=0.0)
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sortino_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PerformanceMetrics(Base):
    """Detailed performance metrics snapshots."""

    __tablename__ = "performance_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("strategy_instances.id"), nullable=False, index=True
    )

    # Snapshot time
    snapshot_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Equity curve
    equity: Mapped[float] = mapped_column(Float, nullable=False)
    cash: Mapped[float] = mapped_column(Float, nullable=False)

    # P&L
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)

    # Positions
    open_positions_count: Mapped[int] = mapped_column(Integer, default=0)
    open_positions_value: Mapped[float] = mapped_column(Float, default=0.0)

    # Drawdown
    drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    drawdown_percentage: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
