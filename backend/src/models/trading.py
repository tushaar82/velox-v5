"""Trading models for orders, positions, and executions."""
from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, JSON, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.database import Base


class OrderType(str, Enum):
    """Order type enumeration."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LOSS_LIMIT = "stop_loss_limit"
    TRAILING_STOP_LOSS = "trailing_stop_loss"


class OrderSide(str, Enum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionStatus(str, Enum):
    """Position status enumeration."""

    OPEN = "open"
    CLOSED = "closed"
    PARTIALLY_CLOSED = "partially_closed"


class TradeOrder(Base):
    """Trade order model."""

    __tablename__ = "trade_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("strategy_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol = Column(String(50), nullable=False, index=True)
    order_type = Column(SQLEnum(OrderType), nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float)  # For limit orders
    stop_price = Column(Float)  # For stop orders
    filled_quantity = Column(Float, default=0.0, nullable=False)
    avg_filled_price = Column(Float)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    broker_order_id = Column(String(255))  # Broker-specific order ID
    metadata = Column(JSON)  # Additional order metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    filled_at = Column(DateTime)


class Position(Base):
    """Trading position model."""

    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("strategy_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(SQLEnum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    unrealized_pnl = Column(Float, nullable=False, default=0.0)
    realized_pnl = Column(Float, nullable=False, default=0.0)
    status = Column(SQLEnum(PositionStatus), default=PositionStatus.OPEN, nullable=False)
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime)

    # Relationships
    trailing_stoploss = relationship(
        "TrailingStoploss", back_populates="position", uselist=False, cascade="all, delete-orphan"
    )


class TrailingStoploss(Base):
    """Trailing stoploss configuration for positions."""

    __tablename__ = "trailing_stoplosses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    position_id = Column(
        UUID(as_uuid=True), ForeignKey("positions.id", ondelete="CASCADE"), nullable=False
    )
    trail_percent = Column(Float, nullable=False)  # Trailing percentage
    trail_amount = Column(Float)  # Fixed trailing amount
    current_stop_price = Column(Float, nullable=False)
    highest_price = Column(Float, nullable=False)  # For long positions
    lowest_price = Column(Float)  # For short positions
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    position = relationship("Position", back_populates="trailing_stoploss")


class TradeExecution(Base):
    """Trade execution record."""

    __tablename__ = "trade_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("trade_orders.id", ondelete="CASCADE"), nullable=False)
    broker_execution_id = Column(String(255))
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, default=0.0, nullable=False)
    tax = Column(Float, default=0.0, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class StrategyPerformance(Base):
    """Strategy performance metrics."""

    __tablename__ = "strategy_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("strategy_instances.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    total_trades = Column(Integer, default=0, nullable=False)
    winning_trades = Column(Integer, default=0, nullable=False)
    losing_trades = Column(Integer, default=0, nullable=False)
    win_rate = Column(Float, default=0.0, nullable=False)
    total_pnl = Column(Float, default=0.0, nullable=False)
    realized_pnl = Column(Float, default=0.0, nullable=False)
    unrealized_pnl = Column(Float, default=0.0, nullable=False)
    max_drawdown = Column(Float, default=0.0, nullable=False)
    sharpe_ratio = Column(Float)
    profit_factor = Column(Float)
    avg_win = Column(Float, default=0.0, nullable=False)
    avg_loss = Column(Float, default=0.0, nullable=False)
    largest_win = Column(Float, default=0.0, nullable=False)
    largest_loss = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    strategy = relationship("StrategyInstance", back_populates="performance")


class PerformanceMetrics(Base):
    """Time-series performance metrics (stored in TimescaleDB)."""

    __tablename__ = "performance_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    equity = Column(Float, nullable=False)
    pnl = Column(Float, nullable=False)
    drawdown = Column(Float, nullable=False)
    open_positions = Column(Integer, nullable=False)
    daily_volume = Column(Float, nullable=False)
