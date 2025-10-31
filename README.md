# Velox V5 - High-Frequency Algorithmic Trading Platform

A comprehensive, production-ready algorithmic trading platform built with FastAPI and Next.js, designed for high-frequency trading with real-time analytics, multi-broker integration, and advanced risk management.

![Version](https://img.shields.io/badge/version-5.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Next.js](https://img.shields.io/badge/next.js-14.0-black)

## 🎯 Overview

Velox V5 is a complete algorithmic trading platform that enables traders to:
- Execute automated trading strategies in real-time
- Manage risk with sophisticated loss limits and trailing stop-loss
- Backtest strategies against historical data
- Monitor performance with live analytics dashboards
- Connect to multiple brokers seamlessly
- Switch between live and paper trading modes

## ✨ Key Features

### 🚀 Core Trading Engine
- **Real-time Strategy Execution**: Execute trades based on custom strategy signals
- **Technical Indicators**: 8+ built-in indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP, Stochastic)
- **Multiple Strategy Support**: Momentum, mean reversion, and custom strategies
- **High-Performance Processing**: Async/await architecture for non-blocking operations

### 🛡️ Risk Management
- **Daily Loss Limits**: Automatic position closure when thresholds are breached
- **Drawdown Monitoring**: Real-time tracking with alerts
- **Position Size Limits**: Per-strategy sizing controls
- **Trailing Stop-Loss**: Automatic profit protection with dynamic adjustment
- **Risk Metrics Dashboard**: Live visualization of exposure

### 📊 Analytics & Reporting
- **Real-Time Dashboard**: WebSocket-powered live updates
- **Performance Metrics**: 20+ metrics including Sharpe, Sortino, Calmar ratios
- **Equity Curve Tracking**: Visual representation of growth
- **Daily P&L Charts**: Detailed profit/loss analysis
- **Trade History**: Complete audit trail

### 🔄 Strategy Backtesting
- **Historical Simulation**: Test strategies against historical data
- **Comprehensive Metrics**: Win rate, profit factor, max drawdown
- **Multiple Timeframes**: Various timeframe analysis
- **Data Generation**: Built-in simulated data for testing

### 🏦 Multi-Broker Integration
- **Broker Adapter Pattern**: Standardized interface for brokers
- **Supported Brokers**: NSE, Zerodha (extensible architecture)
- **Connection Management**: Test connections, validate credentials
- **Balance Synchronization**: Real-time account updates
- **Order Routing**: Intelligent routing to configured brokers

### 🎮 Trading Modes
- **Live Trading**: Execute with real money through brokers
- **Paper Trading**: Risk-free testing with virtual money
- **Mode Switching**: Safe transitions with position checks

### 👥 User Management
- **Authentication**: JWT-based secure authentication
- **Role-Based Access**: Admin, Trader, Analyst roles
- **User Registration**: Self-service account creation
- **Profile Management**: Update information and passwords
- **Audit Logging**: Complete trail of all actions

## 🏗️ Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Databases**: PostgreSQL, TimescaleDB (time-series)
- **Cache**: Redis
- **Message Queue**: Apache Kafka
- **ORM**: SQLAlchemy (async)
- **Auth**: JWT with bcrypt
- **WebSockets**: Real-time bidirectional communication
- **Monitoring**: Prometheus

### Frontend
- **Framework**: Next.js 14 (React 18)
- **Language**: TypeScript
- **UI Library**: shadcn/ui + Radix UI
- **Styling**: Tailwind CSS
- **Charts**: Recharts + lightweight-charts
- **State Management**: Zustand
- **WebSocket**: Socket.io-client

## 📁 Project Structure

```
velox-v5/
├── backend/
│   ├── src/
│   │   ├── api/endpoints/       # API route handlers
│   │   ├── core/                # Security, config, database
│   │   ├── models/              # SQLAlchemy models
│   │   ├── services/            # Business logic
│   │   │   ├── analytics/       # Performance & backtesting
│   │   │   ├── broker_adapter/  # Multi-broker integration
│   │   │   ├── market_data/     # Data processing
│   │   │   └── strategy_engine/ # Strategy execution
│   │   └── utils/               # Logging, monitoring
│   ├── tests/                   # Test suites
│   └── alembic/                 # Database migrations
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Next.js pages
│   │   ├── services/            # API & WebSocket clients
│   │   └── types/               # TypeScript types
│   └── package.json
├── infrastructure/
│   └── docker-compose.yml       # Service orchestration
└── specs/                       # Documentation
```

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Kafka 3.0+

### Development Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd velox-v5
```

2. **Setup environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start infrastructure services**
```bash
cd infrastructure
docker-compose up -d postgres timescaledb redis kafka
```

4. **Backend setup**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Frontend setup**
```bash
cd frontend
npm install
npm run dev
```

6. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Metrics: http://localhost:8000/metrics

### Docker Setup

Run the entire stack:
```bash
cd infrastructure
docker-compose up
```

## 📚 API Documentation

### Authentication Endpoints

**Register User**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "trader@example.com",
  "username": "trader123",
  "password": "SecurePass123!",
  "full_name": "John Trader"
}
```

**Login**
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=trader123&password=SecurePass123!
```

### Strategy Endpoints

**Create Strategy Instance**
```http
POST /api/v1/strategies/instances
Authorization: Bearer {token}

{
  "strategy_id": 1,
  "name": "My Momentum Strategy",
  "symbol": "RELIANCE",
  "timeframe": "1h",
  "parameters": {"sma_period": 20},
  "max_position_size": 100000,
  "trading_mode": "paper"
}
```

**Start Strategy**
```http
POST /api/v1/strategies/instances/{id}/start
Authorization: Bearer {token}
```

### Trading Endpoints

**Get Positions**
```http
GET /api/v1/trading/positions?strategy_instance_id=1
Authorization: Bearer {token}
```

**Close Position**
```http
POST /api/v1/trading/positions/{id}/close
Authorization: Bearer {token}
```

### Analytics Endpoints

**Get Performance Metrics**
```http
GET /api/v1/analytics/performance/{strategy_instance_id}
Authorization: Bearer {token}
```

**Run Backtest**
```http
POST /api/v1/analytics/backtest
Authorization: Bearer {token}

{
  "strategy_id": 1,
  "symbol": "NIFTY50",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "initial_capital": 100000
}
```

### Broker Endpoints

**Add Broker Account**
```http
POST /api/v1/brokers
Authorization: Bearer {token}

{
  "broker_type": "zerodha",
  "account_name": "My Zerodha",
  "account_id": "ABC123",
  "api_key": "key",
  "api_secret": "secret",
  "is_primary": true
}
```

## 🔌 WebSocket API

```javascript
import { io } from 'socket.io-client';

const socket = io('ws://localhost:8000/ws/strategy/1', {
  query: { token: 'jwt_token' }
});

socket.on('tick_update', (data) => {
  console.log('Price update:', data);
});

socket.on('position_update', (data) => {
  console.log('Position update:', data);
});

socket.on('risk_alert', (data) => {
  console.log('Risk alert:', data);
});
```

## 🧪 Testing

**Backend Tests**
```bash
cd backend
pytest
pytest --cov=src --cov-report=html
```

**Frontend Tests**
```bash
cd frontend
npm test
npm run test:coverage
```

## 🔒 Security

- JWT tokens with expiration
- Password hashing with bcrypt
- SQL injection protection via ORM
- CORS configuration
- Rate limiting
- Audit logging for all trades
- Session management

## 📊 Performance Metrics

The platform calculates 20+ metrics:

**Returns**
- Total Return (absolute & %)
- Annualized Return
- ROI

**Risk Metrics**
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Maximum Drawdown

**Trading Stats**
- Win Rate
- Profit Factor
- Average Win/Loss
- Largest Win/Loss

## 🎯 Implemented Features

✅ **User Story 1**: Real-Time Trading Strategy Execution
✅ **User Story 2**: Risk Management with Daily Loss Limits
✅ **User Story 2.1**: Strategy-Based Trailing Stop-Loss
✅ **User Story 3**: Real-Time Analytics Dashboard
✅ **User Story 4**: Multi-Broker Integration
✅ **User Story 5**: Strategy Backtesting and Validation
✅ **User Story 6**: Live and Paper Trading Modes
✅ **User Story 7**: User Account Management

## 🛠️ Development

### Code Style

**Backend:**
- Black (formatting)
- isort (imports)
- mypy (type checking)
- flake8 (linting)

**Frontend:**
- ESLint (linting)
- Prettier (formatting)
- TypeScript strict mode

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 📈 Monitoring

### Prometheus Metrics
Exposed at `/metrics`:
- Request latency
- Trade execution duration
- Strategy performance counters
- Error rates

### Logging
Structured logging for:
- Strategy execution
- Risk events
- Trade confirmations
- Errors with context

## 🗺️ Roadmap

### Future Features
- [ ] Options trading support
- [ ] Advanced order types
- [ ] ML strategy recommendations
- [ ] Mobile app
- [ ] Additional broker integrations
- [ ] Portfolio optimization
- [ ] Crypto trading support

## 📊 Performance Targets

- Strategy execution: < 10ms
- WebSocket delivery: < 5ms
- API response (p95): < 100ms
- Database query (p95): < 50ms
- Concurrent strategies: 1000+

## 📝 License

Proprietary - All rights reserved

## 📞 Support

For issues and questions, please open an issue in the repository.

---

Built with ❤️ for algorithmic traders

**Happy Trading! 📈**
