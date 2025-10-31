"""
User-related database models.
Includes User, RiskParameters, BrokerAccount, Balance, PaperTradingAccount,
UserSession, and AuditLog models.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Float, Integer, DateTime, JSON, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from .database import Base


class UserRole(str, enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"
    TRADER = "trader"
    INVESTOR = "investor"
    VIEWER = "viewer"


class BrokerType(str, enum.Enum):
    """Broker type enumeration."""
    NSE = "nse"
    ZERODHA = "zerodha"
    UPSTOX = "upstox"
    ANGEL_ONE = "angel_one"
    ICICI_DIRECT = "icici_direct"


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.TRADER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    risk_parameters: Mapped[Optional["RiskParameters"]] = relationship(
        "RiskParameters", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    broker_accounts: Mapped[list["BrokerAccount"]] = relationship(
        "BrokerAccount", back_populates="user", cascade="all, delete-orphan"
    )
    paper_trading_account: Mapped[Optional["PaperTradingAccount"]] = relationship(
        "PaperTradingAccount", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )


class RiskParameters(Base):
    """Risk management parameters for a user."""

    __tablename__ = "risk_parameters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Daily loss limits
    max_daily_loss_percentage: Mapped[float] = mapped_column(Float, default=5.0)
    max_daily_loss_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Position sizing
    max_position_size_percentage: Mapped[float] = mapped_column(Float, default=10.0)
    max_positions_per_strategy: Mapped[int] = mapped_column(Integer, default=50)

    # Drawdown limits
    max_drawdown_percentage: Mapped[float] = mapped_column(Float, default=15.0)

    # Trading limits
    max_trades_per_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_loss_per_trade: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="risk_parameters")


class BrokerAccount(Base):
    """Broker account integration."""

    __tablename__ = "broker_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    broker_type: Mapped[BrokerType] = mapped_column(SQLEnum(BrokerType), nullable=False)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Encrypted credentials (should be encrypted at application level)
    api_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    api_secret: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="broker_accounts")
    balances: Mapped[list["Balance"]] = relationship(
        "Balance", back_populates="broker_account", cascade="all, delete-orphan"
    )


class Balance(Base):
    """Broker account balance."""

    __tablename__ = "balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    broker_account_id: Mapped[int] = mapped_column(Integer, ForeignKey("broker_accounts.id"), nullable=False)

    available_cash: Mapped[float] = mapped_column(Float, default=0.0)
    total_cash: Mapped[float] = mapped_column(Float, default=0.0)
    margin_used: Mapped[float] = mapped_column(Float, default=0.0)
    margin_available: Mapped[float] = mapped_column(Float, default=0.0)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    broker_account: Mapped["BrokerAccount"] = relationship("BrokerAccount", back_populates="balances")


class PaperTradingAccount(Base):
    """Paper trading (virtual money) account."""

    __tablename__ = "paper_trading_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    initial_balance: Mapped[float] = mapped_column(Float, default=100000.0)
    current_balance: Mapped[float] = mapped_column(Float, default=100000.0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="paper_trading_account")


class UserSession(Base):
    """User session tracking."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    session_token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="sessions")


class AuditLog(Base):
    """Audit log for tracking user actions."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
