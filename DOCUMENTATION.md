# Velox V5 - Technical Documentation

**Version**: 5.0.0
**Last Updated**: 2025-10-31
**Status**: Production Ready

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Technology Stack](#technology-stack)
3. [Database Schema](#database-schema)
4. [API Reference](#api-reference)
5. [WebSocket API](#websocket-api)
6. [Configuration](#configuration)
7. [Deployment Guide](#deployment-guide)
8. [Development Guide](#development-guide)
9. [Security](#security)
10. [Monitoring & Logging](#monitoring--logging)
11. [Performance](#performance)
12. [Troubleshooting](#troubleshooting)
13. [Contributing](#contributing)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Next.js 14 + TypeScript + Tailwind CSS + shadcn/ui     │  │
│  │  - Dashboard  - Auth  - Settings  - Analytics            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP/REST + WebSocket
┌────────────────────┴────────────────────────────────────────────┐
│                         API Gateway                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI (Python 3.11+)                                  │  │
│  │  - Authentication  - Rate Limiting  - CORS               │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────┬──────────┬──────────┬──────────┬─────────────────────┘
         │          │          │          │
┌────────┴──────┐ ┌─┴────────┐ ┌┴────────┐ ┌┴─────────────────┐
│   Strategy    │ │   Risk   │ │  Broker │ │   Analytics      │
│   Engine      │ │  Manager │ │ Adapter │ │   Engine         │
└───────┬───────┘ └────┬─────┘ └┬────────┘ └──────┬───────────┘
        │              │         │                 │
┌───────┴──────────────┴─────────┴─────────────────┴───────────┐
│                      Data Layer                               │
│  ┌──────────┐  ┌────────────┐  ┌──────┐  ┌────────────────┐ │
│  │PostgreSQL│  │TimescaleDB │  │ Redis│  │ Apache Kafka   │ │
│  │(Relational)│ │(Time-Series)│ │(Cache)│ │(Streaming)     │ │
│  └──────────┘  └────────────┘  └──────┘  └────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### Component Overview

#### Frontend Layer
- **Next.js Application**: Server-side rendered React application
- **Real-time Updates**: WebSocket connections for live data
- **State Management**: Zustand for global state
- **UI Components**: shadcn/ui + Radix UI primitives

#### Backend Layer
- **API Gateway**: FastAPI with async/await support
- **Strategy Engine**: Real-time strategy execution
- **Risk Manager**: Risk monitoring and enforcement
- **Broker Adapters**: Multi-broker integration layer
- **Analytics Engine**: Performance metrics and backtesting

#### Data Layer
- **PostgreSQL**: User accounts, strategies, configurations
- **TimescaleDB**: Time-series market data (ticks, candles)
- **Redis**: Session management, caching
- **Kafka**: Real-time market data streaming

---

## Technology Stack

### Backend Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | FastAPI | Latest | Async web framework |
| Language | Python | 3.11+ | Core language |
| Database | PostgreSQL | 16+ | Relational data |
| Time-Series DB | TimescaleDB | Latest | Market data |
| Cache | Redis | 7+ | Session & caching |
| Message Queue | Apache Kafka | 3.0+ | Streaming data |
| ORM | SQLAlchemy | 2.0+ | Database ORM |
| Migrations | Alembic | Latest | Schema migrations |
| Authentication | JWT + bcrypt | Latest | Security |
| Validation | Pydantic | 2.0+ | Data validation |
| Testing | pytest | Latest | Unit/integration tests |
| Monitoring | Prometheus | Latest | Metrics collection |

### Frontend Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | Next.js | 14+ | React framework |
| Language | TypeScript | 5.0+ | Type safety |
| UI Library | shadcn/ui | Latest | Component library |
| Styling | Tailwind CSS | 3.0+ | Utility-first CSS |
| Charts | Recharts | Latest | Analytics charts |
| Trading Charts | lightweight-charts | Latest | TradingView-style |
| State | Zustand | Latest | State management |
| WebSocket | Socket.io-client | Latest | Real-time updates |
| HTTP Client | Axios | Latest | API requests |
| Forms | React Hook Form | Latest | Form management |
| Icons | Lucide React | Latest | Icon library |

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Containerization | Docker | Application packaging |
| Orchestration | Docker Compose | Multi-container apps |
| Monitoring | Prometheus | Metrics collection |
| Load Balancer | Nginx (optional) | Reverse proxy |

---

## Database Schema

### PostgreSQL Schema (Relational Data)

#### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'TRADER',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
```

#### Strategies Table
```sql
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL,
    code TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Strategy Instances Table
```sql
CREATE TABLE strategy_instances (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id),
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    parameters JSONB,
    status VARCHAR(50) DEFAULT 'STOPPED',
    trading_mode VARCHAR(50) DEFAULT 'PAPER',
    max_position_size DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_strategy_instances_user ON strategy_instances(user_id);
CREATE INDEX idx_strategy_instances_status ON strategy_instances(status);
```

#### Positions Table
```sql
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    strategy_instance_id INTEGER REFERENCES strategy_instances(id),
    user_id INTEGER REFERENCES users(id),
    symbol VARCHAR(50) NOT NULL,
    quantity DECIMAL(15,4) NOT NULL,
    entry_price DECIMAL(15,4) NOT NULL,
    current_price DECIMAL(15,4),
    pnl DECIMAL(15,2),
    pnl_percentage DECIMAL(8,4),
    side VARCHAR(10) NOT NULL,
    status VARCHAR(50) DEFAULT 'OPEN',
    opened_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_positions_strategy ON positions(strategy_instance_id);
CREATE INDEX idx_positions_user ON positions(user_id);
CREATE INDEX idx_positions_status ON positions(status);
```

#### Trade Orders Table
```sql
CREATE TABLE trade_orders (
    id SERIAL PRIMARY KEY,
    strategy_instance_id INTEGER REFERENCES strategy_instances(id),
    user_id INTEGER REFERENCES users(id),
    symbol VARCHAR(50) NOT NULL,
    order_type VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(15,4) NOT NULL,
    price DECIMAL(15,4),
    status VARCHAR(50) DEFAULT 'PENDING',
    broker_order_id VARCHAR(255),
    filled_quantity DECIMAL(15,4) DEFAULT 0,
    filled_price DECIMAL(15,4),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    executed_at TIMESTAMP
);

CREATE INDEX idx_orders_strategy ON trade_orders(strategy_instance_id);
CREATE INDEX idx_orders_status ON trade_orders(status);
CREATE INDEX idx_orders_created ON trade_orders(created_at);
```

#### Broker Accounts Table
```sql
CREATE TABLE broker_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    broker_type VARCHAR(50) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    api_key TEXT,
    api_secret TEXT,
    is_primary BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_broker_accounts_user ON broker_accounts(user_id);
```

#### Risk Parameters Table
```sql
CREATE TABLE risk_parameters (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    daily_loss_limit DECIMAL(15,2),
    max_drawdown_percentage DECIMAL(8,4),
    max_position_size DECIMAL(15,2),
    max_positions INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Trailing Stop Loss Table
```sql
CREATE TABLE trailing_stoploss (
    id SERIAL PRIMARY KEY,
    position_id INTEGER REFERENCES positions(id),
    strategy_instance_id INTEGER REFERENCES strategy_instances(id),
    activation_percentage DECIMAL(8,4) NOT NULL,
    trail_percentage DECIMAL(8,4) NOT NULL,
    initial_price DECIMAL(15,4) NOT NULL,
    current_stop_price DECIMAL(15,4) NOT NULL,
    highest_price DECIMAL(15,4) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trailing_stoploss_position ON trailing_stoploss(position_id);
```

#### Backtest Results Table
```sql
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id),
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255),
    symbol VARCHAR(50) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    initial_capital DECIMAL(15,2) NOT NULL,
    final_capital DECIMAL(15,2),
    metrics JSONB,
    trades JSONB,
    equity_curve JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_backtest_strategy ON backtest_results(strategy_id);
CREATE INDEX idx_backtest_user ON backtest_results(user_id);
```

#### User Sessions Table
```sql
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_token ON user_sessions(token_jti);
```

#### Audit Logs Table
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100),
    resource_id INTEGER,
    details JSONB,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
```

### TimescaleDB Schema (Time-Series Data)

#### Ticks Table (Hypertable)
```sql
CREATE TABLE ticks (
    id BIGSERIAL,
    symbol VARCHAR(50) NOT NULL,
    price DECIMAL(15,4) NOT NULL,
    volume DECIMAL(15,4),
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(50)
);

SELECT create_hypertable('ticks', 'timestamp');
CREATE INDEX idx_ticks_symbol_time ON ticks(symbol, timestamp DESC);
```

#### Candles Table (Hypertable)
```sql
CREATE TABLE candles (
    id BIGSERIAL,
    symbol VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    open DECIMAL(15,4) NOT NULL,
    high DECIMAL(15,4) NOT NULL,
    low DECIMAL(15,4) NOT NULL,
    close DECIMAL(15,4) NOT NULL,
    volume DECIMAL(15,4) NOT NULL,
    timestamp TIMESTAMP NOT NULL
);

SELECT create_hypertable('candles', 'timestamp');
CREATE INDEX idx_candles_symbol_timeframe ON candles(symbol, timeframe, timestamp DESC);
```

#### Indicator Values Table (Hypertable)
```sql
CREATE TABLE indicator_values (
    id BIGSERIAL,
    strategy_instance_id INTEGER NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    indicator_name VARCHAR(100) NOT NULL,
    value DECIMAL(15,8),
    metadata JSONB,
    timestamp TIMESTAMP NOT NULL
);

SELECT create_hypertable('indicator_values', 'timestamp');
CREATE INDEX idx_indicators_strategy ON indicator_values(strategy_instance_id, timestamp DESC);
```

#### Strategy Performance Table (Hypertable)
```sql
CREATE TABLE strategy_performance (
    id BIGSERIAL,
    strategy_instance_id INTEGER NOT NULL,
    total_pnl DECIMAL(15,2),
    daily_pnl DECIMAL(15,2),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    timestamp TIMESTAMP NOT NULL
);

SELECT create_hypertable('strategy_performance', 'timestamp');
CREATE INDEX idx_performance_strategy ON strategy_performance(strategy_instance_id, timestamp DESC);
```

---

## API Reference

### Base URL
```
Development: http://localhost:8000
Production: https://your-domain.com
```

### Authentication

All authenticated endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

### Authentication Endpoints

#### POST /api/v1/auth/register
Register a new user account.

**Request Body:**
```json
{
  "email": "trader@example.com",
  "username": "trader123",
  "password": "SecurePass123!",
  "full_name": "John Trader"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "email": "trader@example.com",
  "username": "trader123",
  "full_name": "John Trader",
  "role": "TRADER",
  "is_active": true,
  "created_at": "2025-10-31T10:00:00Z"
}
```

---

#### POST /api/v1/auth/login
Authenticate user and receive JWT token.

**Request Body (Form Data):**
```
username=trader123&password=SecurePass123!
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

#### GET /api/v1/auth/me
Get current user profile.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "trader@example.com",
  "username": "trader123",
  "full_name": "John Trader",
  "role": "TRADER",
  "is_active": true
}
```

---

#### POST /api/v1/auth/change-password
Change user password.

**Request Body:**
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewPass456!"
}
```

**Response (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

---

#### POST /api/v1/auth/logout
Invalidate current session.

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

---

### Strategy Endpoints

#### GET /api/v1/strategies
List all available strategies.

**Query Parameters:**
- `skip`: int (default: 0) - Pagination offset
- `limit`: int (default: 100) - Results per page

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "name": "Momentum Strategy",
    "description": "Trend-following momentum strategy",
    "strategy_type": "MOMENTUM",
    "created_by": 1,
    "created_at": "2025-10-30T10:00:00Z"
  }
]
```

---

#### POST /api/v1/strategies
Create a new strategy.

**Request Body:**
```json
{
  "name": "My Custom Strategy",
  "description": "Custom mean reversion strategy",
  "strategy_type": "MEAN_REVERSION",
  "code": "# Strategy code here"
}
```

**Response (201 Created):**
```json
{
  "id": 2,
  "name": "My Custom Strategy",
  "description": "Custom mean reversion strategy",
  "strategy_type": "MEAN_REVERSION",
  "created_by": 1,
  "created_at": "2025-10-31T10:00:00Z"
}
```

---

#### GET /api/v1/strategies/instances
List user's strategy instances.

**Query Parameters:**
- `status`: string (optional) - Filter by status (RUNNING, STOPPED, PAUSED)
- `skip`: int (default: 0)
- `limit`: int (default: 100)

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "strategy_id": 1,
    "user_id": 1,
    "name": "My Momentum Instance",
    "symbol": "RELIANCE",
    "timeframe": "1h",
    "parameters": {
      "sma_period": 20,
      "rsi_period": 14
    },
    "status": "RUNNING",
    "trading_mode": "PAPER",
    "max_position_size": 100000,
    "created_at": "2025-10-31T09:00:00Z"
  }
]
```

---

#### POST /api/v1/strategies/instances
Create a new strategy instance.

**Request Body:**
```json
{
  "strategy_id": 1,
  "name": "NIFTY Momentum",
  "symbol": "NIFTY50",
  "timeframe": "15m",
  "parameters": {
    "sma_period": 50,
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30
  },
  "max_position_size": 500000,
  "trading_mode": "PAPER"
}
```

**Response (201 Created):**
```json
{
  "id": 2,
  "strategy_id": 1,
  "user_id": 1,
  "name": "NIFTY Momentum",
  "symbol": "NIFTY50",
  "timeframe": "15m",
  "parameters": {
    "sma_period": 50,
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30
  },
  "status": "STOPPED",
  "trading_mode": "PAPER",
  "max_position_size": 500000,
  "created_at": "2025-10-31T10:00:00Z"
}
```

---

#### POST /api/v1/strategies/instances/{id}/start
Start a strategy instance.

**Response (200 OK):**
```json
{
  "id": 2,
  "status": "RUNNING",
  "message": "Strategy started successfully"
}
```

---

#### POST /api/v1/strategies/instances/{id}/stop
Stop a strategy instance.

**Response (200 OK):**
```json
{
  "id": 2,
  "status": "STOPPED",
  "message": "Strategy stopped successfully"
}
```

---

#### DELETE /api/v1/strategies/instances/{id}
Delete a strategy instance (must be stopped).

**Response (204 No Content)**

---

### Trading Endpoints

#### GET /api/v1/trading/positions
Get user's open positions.

**Query Parameters:**
- `strategy_instance_id`: int (optional) - Filter by strategy
- `status`: string (optional) - Filter by status (OPEN, CLOSED)

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "strategy_instance_id": 1,
    "user_id": 1,
    "symbol": "RELIANCE",
    "quantity": 100,
    "entry_price": 2450.50,
    "current_price": 2475.00,
    "pnl": 2450.00,
    "pnl_percentage": 1.00,
    "side": "LONG",
    "status": "OPEN",
    "opened_at": "2025-10-31T09:30:00Z"
  }
]
```

---

#### POST /api/v1/trading/positions/{id}/close
Close a position manually.

**Response (200 OK):**
```json
{
  "id": 1,
  "status": "CLOSED",
  "closed_at": "2025-10-31T10:00:00Z",
  "final_pnl": 2450.00,
  "message": "Position closed successfully"
}
```

---

#### GET /api/v1/trading/orders
Get user's trade orders.

**Query Parameters:**
- `strategy_instance_id`: int (optional)
- `status`: string (optional) - Filter by status
- `skip`: int (default: 0)
- `limit`: int (default: 100)

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "strategy_instance_id": 1,
    "user_id": 1,
    "symbol": "RELIANCE",
    "order_type": "MARKET",
    "side": "BUY",
    "quantity": 100,
    "price": null,
    "status": "FILLED",
    "broker_order_id": "ORDER123",
    "filled_quantity": 100,
    "filled_price": 2450.50,
    "created_at": "2025-10-31T09:30:00Z",
    "executed_at": "2025-10-31T09:30:01Z"
  }
]
```

---

#### POST /api/v1/trading/orders
Place a manual order.

**Request Body:**
```json
{
  "strategy_instance_id": 1,
  "symbol": "RELIANCE",
  "order_type": "LIMIT",
  "side": "BUY",
  "quantity": 50,
  "price": 2440.00
}
```

**Response (201 Created):**
```json
{
  "id": 2,
  "strategy_instance_id": 1,
  "symbol": "RELIANCE",
  "order_type": "LIMIT",
  "side": "BUY",
  "quantity": 50,
  "price": 2440.00,
  "status": "PENDING",
  "created_at": "2025-10-31T10:00:00Z"
}
```

---

### Market Data Endpoints

#### GET /api/v1/market-data/ticks/{symbol}
Get recent tick data for a symbol.

**Query Parameters:**
- `limit`: int (default: 100) - Number of ticks
- `start_time`: datetime (optional) - Start timestamp
- `end_time`: datetime (optional) - End timestamp

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "symbol": "RELIANCE",
    "price": 2475.50,
    "volume": 1000,
    "timestamp": "2025-10-31T10:00:00Z",
    "source": "NSE"
  }
]
```

---

#### GET /api/v1/market-data/candles/{symbol}
Get candle data for a symbol.

**Query Parameters:**
- `timeframe`: string (required) - Timeframe (1m, 5m, 15m, 1h, 1d)
- `limit`: int (default: 100)
- `start_time`: datetime (optional)
- `end_time`: datetime (optional)

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "symbol": "RELIANCE",
    "timeframe": "1h",
    "open": 2450.00,
    "high": 2480.00,
    "low": 2445.00,
    "close": 2475.00,
    "volume": 50000,
    "timestamp": "2025-10-31T09:00:00Z"
  }
]
```

---

### Analytics Endpoints

#### GET /api/v1/analytics/performance/{strategy_instance_id}
Get performance metrics for a strategy instance.

**Response (200 OK):**
```json
{
  "strategy_instance_id": 1,
  "total_pnl": 15000.50,
  "total_pnl_percentage": 15.00,
  "daily_pnl": 2450.00,
  "total_trades": 150,
  "winning_trades": 95,
  "losing_trades": 55,
  "win_rate": 63.33,
  "profit_factor": 1.85,
  "sharpe_ratio": 2.15,
  "sortino_ratio": 3.20,
  "calmar_ratio": 1.75,
  "max_drawdown": 8.50,
  "max_drawdown_percentage": 8.50,
  "average_win": 250.00,
  "average_loss": -150.00,
  "largest_win": 1500.00,
  "largest_loss": -800.00,
  "current_equity": 115000.50,
  "updated_at": "2025-10-31T10:00:00Z"
}
```

---

#### GET /api/v1/analytics/equity-curve/{strategy_instance_id}
Get equity curve data.

**Query Parameters:**
- `start_date`: datetime (optional)
- `end_date`: datetime (optional)

**Response (200 OK):**
```json
[
  {
    "timestamp": "2025-10-01T00:00:00Z",
    "equity": 100000.00
  },
  {
    "timestamp": "2025-10-15T00:00:00Z",
    "equity": 107500.00
  },
  {
    "timestamp": "2025-10-31T00:00:00Z",
    "equity": 115000.50
  }
]
```

---

#### POST /api/v1/analytics/backtest
Run a strategy backtest.

**Request Body:**
```json
{
  "strategy_id": 1,
  "symbol": "NIFTY50",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "initial_capital": 100000,
  "name": "NIFTY 2024 Backtest"
}
```

**Response (202 Accepted):**
```json
{
  "backtest_id": 1,
  "status": "RUNNING",
  "message": "Backtest started successfully"
}
```

---

#### GET /api/v1/analytics/backtest/{id}
Get backtest results.

**Response (200 OK):**
```json
{
  "id": 1,
  "strategy_id": 1,
  "user_id": 1,
  "name": "NIFTY 2024 Backtest",
  "symbol": "NIFTY50",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "initial_capital": 100000,
  "final_capital": 135000,
  "metrics": {
    "total_return": 35000,
    "total_return_percentage": 35.00,
    "annualized_return": 35.00,
    "sharpe_ratio": 2.5,
    "sortino_ratio": 3.2,
    "calmar_ratio": 2.1,
    "max_drawdown": 12.5,
    "win_rate": 65.0,
    "profit_factor": 2.2,
    "total_trades": 250
  },
  "trades": [...],
  "equity_curve": [...],
  "created_at": "2025-10-31T10:00:00Z"
}
```

---

### Broker Endpoints

#### POST /api/v1/brokers
Add a broker account.

**Request Body:**
```json
{
  "broker_type": "ZERODHA",
  "account_name": "My Zerodha Account",
  "account_id": "ABC123",
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "is_primary": true
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "user_id": 1,
  "broker_type": "ZERODHA",
  "account_name": "My Zerodha Account",
  "account_id": "ABC123",
  "is_primary": true,
  "is_active": true,
  "created_at": "2025-10-31T10:00:00Z"
}
```

---

#### GET /api/v1/brokers
List user's broker accounts.

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "broker_type": "ZERODHA",
    "account_name": "My Zerodha Account",
    "account_id": "ABC123",
    "is_primary": true,
    "is_active": true,
    "created_at": "2025-10-31T10:00:00Z"
  }
]
```

---

#### POST /api/v1/brokers/{id}/test-connection
Test broker connection.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Connection successful",
  "balance": 150000.00
}
```

---

#### GET /api/v1/brokers/{id}/balance
Get broker account balance.

**Response (200 OK):**
```json
{
  "broker_id": 1,
  "available_balance": 150000.00,
  "used_margin": 50000.00,
  "total_balance": 200000.00,
  "timestamp": "2025-10-31T10:00:00Z"
}
```

---

### Risk Management Endpoints

#### GET /api/v1/risk/parameters
Get user's risk parameters.

**Response (200 OK):**
```json
{
  "id": 1,
  "user_id": 1,
  "daily_loss_limit": 5000.00,
  "max_drawdown_percentage": 20.00,
  "max_position_size": 100000.00,
  "max_positions": 5,
  "created_at": "2025-10-30T10:00:00Z"
}
```

---

#### PUT /api/v1/risk/parameters
Update risk parameters.

**Request Body:**
```json
{
  "daily_loss_limit": 7500.00,
  "max_drawdown_percentage": 15.00,
  "max_position_size": 150000.00,
  "max_positions": 8
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "user_id": 1,
  "daily_loss_limit": 7500.00,
  "max_drawdown_percentage": 15.00,
  "max_position_size": 150000.00,
  "max_positions": 8,
  "updated_at": "2025-10-31T10:00:00Z"
}
```

---

## WebSocket API

### Connection

Connect to WebSocket endpoint for real-time updates:

```javascript
import { io } from 'socket.io-client';

const socket = io('ws://localhost:8000/ws/strategy/1', {
  query: { token: 'your_jwt_token' }
});
```

### Events

#### Client -> Server Events

**subscribe_ticks**
```javascript
socket.emit('subscribe_ticks', { symbol: 'RELIANCE' });
```

**unsubscribe_ticks**
```javascript
socket.emit('unsubscribe_ticks', { symbol: 'RELIANCE' });
```

---

#### Server -> Client Events

**tick_update**
```javascript
socket.on('tick_update', (data) => {
  console.log('New tick:', data);
  // {
  //   symbol: 'RELIANCE',
  //   price: 2475.50,
  //   volume: 1000,
  //   timestamp: '2025-10-31T10:00:00Z'
  // }
});
```

**position_update**
```javascript
socket.on('position_update', (data) => {
  console.log('Position updated:', data);
  // {
  //   id: 1,
  //   symbol: 'RELIANCE',
  //   current_price: 2475.00,
  //   pnl: 2450.00,
  //   pnl_percentage: 1.00
  // }
});
```

**order_update**
```javascript
socket.on('order_update', (data) => {
  console.log('Order updated:', data);
  // {
  //   id: 1,
  //   status: 'FILLED',
  //   filled_quantity: 100,
  //   filled_price: 2450.50
  // }
});
```

**risk_alert**
```javascript
socket.on('risk_alert', (data) => {
  console.log('Risk alert:', data);
  // {
  //   type: 'DAILY_LOSS_LIMIT',
  //   message: 'Daily loss limit breached',
  //   current_loss: 5100.00,
  //   limit: 5000.00
  // }
});
```

**strategy_status**
```javascript
socket.on('strategy_status', (data) => {
  console.log('Strategy status:', data);
  // {
  //   strategy_instance_id: 1,
  //   status: 'RUNNING',
  //   message: 'Strategy running normally'
  // }
});
```

**performance_update**
```javascript
socket.on('performance_update', (data) => {
  console.log('Performance updated:', data);
  // {
  //   strategy_instance_id: 1,
  //   total_pnl: 15000.50,
  //   daily_pnl: 2450.00,
  //   win_rate: 63.33
  // }
});
```

---

## Configuration

### Environment Variables

#### Backend (.env)

```bash
# Database Configuration
DATABASE_URL=postgresql://velox:velox_password@localhost:5432/velox_trading
TIMESCALE_URL=postgresql://velox:velox_password@localhost:5433/velox_market_data

# Redis Configuration
REDIS_URL=redis://:velox_redis_password@localhost:6379/0

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Settings
LOG_LEVEL=INFO
DEBUG=false
ALLOWED_ORIGINS=http://localhost:3000,https://your-domain.com

# Broker API Keys (optional)
ZERODHA_API_KEY=your_zerodha_key
ZERODHA_API_SECRET=your_zerodha_secret

# Email Configuration (optional for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Monitoring
PROMETHEUS_PORT=9090
```

#### Frontend (.env.local)

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Feature Flags
NEXT_PUBLIC_ENABLE_BACKTESTING=true
NEXT_PUBLIC_ENABLE_LIVE_TRADING=true
```

---

## Deployment Guide

### Production Deployment with Docker

#### 1. Prepare Environment

```bash
# Clone repository
git clone <repository-url>
cd velox-v5

# Copy environment file
cp .env.example .env

# Update .env with production values
nano .env
```

#### 2. Build and Start Services

```bash
# Run installation
./install.sh

# Start in production mode
./run.sh prod
```

#### 3. Verify Services

```bash
# Check service status
docker ps

# Check logs
docker logs velox-backend
docker logs velox-frontend

# Check API health
curl http://localhost:8000/health
```

---

### Kubernetes Deployment (Advanced)

#### Create namespace
```bash
kubectl create namespace velox
```

#### Deploy PostgreSQL
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: velox
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        env:
        - name: POSTGRES_USER
          value: velox
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: velox-secrets
              key: postgres-password
        - name: POSTGRES_DB
          value: velox_trading
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 50Gi
```

#### Deploy Backend
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: velox-backend
  namespace: velox
spec:
  replicas: 3
  selector:
    matchLabels:
      app: velox-backend
  template:
    metadata:
      labels:
        app: velox-backend
    spec:
      containers:
      - name: backend
        image: your-registry/velox-backend:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: velox-secrets
              key: database-url
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

---

### SSL/TLS Configuration

#### Using Nginx as Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## Development Guide

### Local Development Setup

#### 1. Install Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Git

#### 2. Clone and Setup
```bash
git clone <repository-url>
cd velox-v5
./install.sh
```

#### 3. Start Development Mode
```bash
./run.sh dev
```

This will:
- Start infrastructure in Docker (PostgreSQL, Redis, Kafka)
- Run backend locally with hot-reload
- Run frontend locally with hot-reload

#### 4. Access Services
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090

---

### Code Style

#### Backend (Python)

Use Black, isort, mypy, and flake8:

```bash
cd backend

# Format code
black src/

# Sort imports
isort src/

# Type checking
mypy src/

# Linting
flake8 src/
```

#### Frontend (TypeScript)

Use ESLint and Prettier:

```bash
cd frontend

# Lint
npm run lint

# Format
npm run format

# Type check
npm run type-check
```

---

### Database Migrations

#### Create Migration
```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "Add new table"
```

#### Apply Migrations
```bash
alembic upgrade head
```

#### Rollback Migration
```bash
alembic downgrade -1
```

---

### Testing

#### Backend Tests
```bash
cd backend
source .venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_strategy_engine.py
```

#### Frontend Tests
```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

---

## Security

### Authentication Flow

1. User registers or logs in
2. Backend validates credentials
3. JWT token generated with expiry
4. Token sent to frontend
5. Frontend includes token in all requests
6. Backend validates token on each request

### Password Security

- Passwords hashed using bcrypt (cost factor: 12)
- Minimum password length: 8 characters
- Passwords never logged or exposed in responses
- Password reset via email verification

### API Security

- CORS configured for allowed origins only
- Rate limiting on authentication endpoints
- SQL injection protection via ORM
- Input validation using Pydantic
- XSS protection in frontend

### Broker Credentials

- API keys encrypted at rest
- Never exposed in API responses
- Stored securely in database
- Accessed only during order execution

---

## Monitoring & Logging

### Prometheus Metrics

Access metrics at: http://localhost:9090

**Available Metrics:**
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request duration
- `strategy_execution_duration_seconds` - Strategy execution time
- `trade_orders_total` - Total trade orders
- `positions_open` - Currently open positions
- `risk_alerts_total` - Total risk alerts

**Example Queries:**
```promql
# Request rate
rate(http_requests_total[5m])

# Average response time
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Error rate
rate(http_requests_total{status="5xx"}[5m])
```

---

### Logging

Logs are structured JSON format with the following levels:
- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

**Log Locations:**
- Backend: `logs/backend.log`
- Frontend: `logs/frontend.log`
- Docker: `docker logs <container-name>`

**Example Log Entry:**
```json
{
  "timestamp": "2025-10-31T10:00:00.000Z",
  "level": "INFO",
  "logger": "strategy_engine",
  "message": "Strategy started",
  "context": {
    "strategy_instance_id": 1,
    "user_id": 1,
    "symbol": "RELIANCE"
  }
}
```

---

### Audit Logging

All critical operations are logged to `audit_logs` table:
- User authentication
- Strategy start/stop
- Trade executions
- Position changes
- Risk parameter updates
- Broker account changes

**Audit Log Query:**
```sql
SELECT * FROM audit_logs
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 100;
```

---

## Performance

### Target Performance Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Strategy Execution | < 10ms | Time to process signal and place order |
| WebSocket Delivery | < 5ms | Time to deliver update to client |
| API Response (p95) | < 100ms | 95th percentile response time |
| Database Query (p95) | < 50ms | 95th percentile query time |
| Concurrent Strategies | 1000+ | Number of simultaneous strategies |

---

### Optimization Tips

#### Backend
- Use connection pooling for databases
- Enable Redis caching for frequently accessed data
- Use async/await for I/O operations
- Index database tables appropriately
- Batch database operations where possible

#### Frontend
- Code splitting with Next.js
- Lazy load components
- Optimize images
- Use React.memo for expensive components
- Debounce API calls

#### Database
- Regular VACUUM on PostgreSQL
- Partition TimescaleDB hypertables
- Create appropriate indexes
- Use materialized views for complex queries

---

## Troubleshooting

### Common Issues

#### Backend won't start
**Symptom:** Backend fails to start with database connection error

**Solution:**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check database logs
docker logs velox-postgres

# Verify connection
psql -h localhost -p 5432 -U velox -d velox_trading
```

---

#### Frontend shows connection error
**Symptom:** Frontend can't connect to backend API

**Solution:**
```bash
# Check backend is running
curl http://localhost:8000/health

# Check CORS configuration in backend/.env
ALLOWED_ORIGINS=http://localhost:3000

# Check frontend environment
cat frontend/.env.local
```

---

#### Strategy not executing trades
**Symptom:** Strategy is running but no trades

**Solution:**
1. Check strategy status: `GET /api/v1/strategies/instances/{id}`
2. Verify market data is flowing: `GET /api/v1/market-data/ticks/{symbol}`
3. Check logs for errors: `tail -f logs/backend.log`
4. Verify risk parameters allow trading
5. Check trading mode (paper vs live)

---

#### WebSocket disconnects frequently
**Symptom:** Real-time updates stop working

**Solution:**
```javascript
// Add reconnection logic
socket.on('disconnect', () => {
  setTimeout(() => {
    socket.connect();
  }, 1000);
});

// Add error handling
socket.on('error', (error) => {
  console.error('WebSocket error:', error);
});
```

---

#### High memory usage
**Symptom:** Backend consuming excessive memory

**Solution:**
1. Check for memory leaks in strategy code
2. Reduce candle/tick retention period
3. Optimize database queries
4. Increase container memory limits
5. Enable garbage collection logging

---

### Debug Mode

Enable debug mode for verbose logging:

**Backend:**
```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

**Frontend:**
```bash
# In frontend/.env.local
NEXT_PUBLIC_DEBUG=true
```

---

## Contributing

### Development Workflow

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes and test thoroughly
4. Run linters and tests
5. Commit with descriptive message
6. Push and create pull request

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No console.log statements
- [ ] Error handling implemented
- [ ] Performance considered
- [ ] Security implications reviewed
- [ ] Database migrations included (if needed)

---

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| Strategy Instance | A running instance of a trading strategy |
| Tick | Single price update for an instrument |
| Candle | OHLCV data for a specific timeframe |
| Position | Open trade with entry price |
| Order | Request to buy or sell |
| Execution | Filled order |
| Backtest | Historical strategy simulation |
| Drawdown | Peak-to-trough decline |
| Sharpe Ratio | Risk-adjusted return metric |

---

### Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Next.js Documentation**: https://nextjs.org/docs
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/
- **TimescaleDB Documentation**: https://docs.timescale.com/
- **Prometheus Documentation**: https://prometheus.io/docs/

---

**End of Documentation**

For support, please open an issue on GitHub or contact the development team.

**Version**: 5.0.0
**Last Updated**: 2025-10-31
