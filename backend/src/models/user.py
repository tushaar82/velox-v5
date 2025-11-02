"""User models and related entities."""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.database import Base


class UserRole(str, Enum):
    """User role enumeration."""

    ADMIN = "admin"
    TRADER = "trader"
    INVESTOR = "investor"
    VIEWER = "viewer"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SQLEnum(UserRole), default=UserRole.TRADER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    strategies = relationship("StrategyInstance", back_populates="user", cascade="all, delete-orphan")
    broker_accounts = relationship("BrokerAccount", back_populates="user", cascade="all, delete-orphan")
    paper_accounts = relationship("PaperTradingAccount", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class RiskParameters(Base):
    """Risk management parameters for users."""

    __tablename__ = "risk_parameters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    daily_loss_limit = Column(Float, nullable=False)  # Maximum daily loss in currency
    max_position_size = Column(Float, nullable=False)  # Maximum position size per trade
    max_drawdown_percent = Column(Float, nullable=False)  # Maximum drawdown percentage
    max_leverage = Column(Float, default=1.0, nullable=False)
    risk_per_trade = Column(Float, default=2.0, nullable=False)  # Risk percentage per trade
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class BrokerAccount(Base):
    """Broker account model for multi-broker integration."""

    __tablename__ = "broker_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    broker_name = Column(String(100), nullable=False)  # e.g., "Zerodha", "Upstox"
    account_id = Column(String(255), nullable=False)
    api_key = Column(String(255))
    api_secret = Column(String(255))
    access_token = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    credentials = Column(JSON)  # Store encrypted broker-specific credentials
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="broker_accounts")
    balances = relationship("Balance", back_populates="broker_account", cascade="all, delete-orphan")


class Balance(Base):
    """Account balance tracking."""

    __tablename__ = "balances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    broker_account_id = Column(
        UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False
    )
    available_cash = Column(Float, nullable=False, default=0.0)
    used_margin = Column(Float, nullable=False, default=0.0)
    total_equity = Column(Float, nullable=False, default=0.0)
    unrealized_pnl = Column(Float, nullable=False, default=0.0)
    realized_pnl = Column(Float, nullable=False, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    broker_account = relationship("BrokerAccount", back_populates="balances")


class PaperTradingAccount(Base):
    """Paper trading account for virtual trading."""

    __tablename__ = "paper_trading_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    initial_capital = Column(Float, nullable=False, default=100000.0)
    current_capital = Column(Float, nullable=False, default=100000.0)
    total_pnl = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="paper_accounts")


class UserSession(Base):
    """User session tracking."""

    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")


class AuditLog(Base):
    """Audit log for user actions."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(String(255))
    details = Column(JSON)
    ip_address = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
