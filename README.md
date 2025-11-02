# Velox Trading Platform v5

A high-frequency algorithmic trading platform built with FastAPI, Next.js, and modern trading infrastructure.

## Project Status

### ✅ Phase 1: Setup (Complete)
- Modular project structure (backend/, frontend/, infrastructure/)
- Python backend with FastAPI and comprehensive dependencies
- TypeScript frontend with Next.js 14
- Linting and formatting (pre-commit, ESLint, Prettier, Black, isort)
- Testing frameworks (pytest, Jest)
- Docker configurations for all services
- Docker Compose infrastructure setup

### ✅ Phase 2: Foundational Infrastructure (Complete)
- Database models (User, Strategy, MarketData, Trading)
- Authentication/authorization with JWT and RBAC
- API routing and middleware (error handling, CORS)
- Environment configuration management
- Structured logging with structlog
- Performance monitoring with Prometheus
- Kafka integration for real-time data streaming
- Redis client for caching and pub/sub
- Main FastAPI application with lifecycle management

### ✅ Phase 3: User Story 1 - Real-Time Trading (Partial)
- Strategy engine base classes
- Technical indicators calculator (SMA, EMA, RSI, MACD, Bollinger Bands, etc.)
- Tick processor for real-time market data
- Strategy execution service
- API endpoints:
  - Authentication (register, login, user info)
  - Strategies (create, list, start, stop)
  - Trading (positions, orders)

## Architecture

### Backend Stack
- **Framework**: FastAPI 0.109.0
- **Language**: Python 3.11
- **Databases**:
  - PostgreSQL (relational data)
  - TimescaleDB (time-series data)
- **Caching**: Redis
- **Message Queue**: Kafka
- **Monitoring**: Prometheus + Grafana

### Frontend Stack
- **Framework**: Next.js 14.1.0
- **Language**: TypeScript 5.3.3
- **UI**: Tailwind CSS + shadcn/ui components
- **Charts**: Recharts, Lightweight Charts

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### Environment Setup

1. Copy environment example:
```bash
cp .env.example .env
```

2. Start infrastructure services:
```bash
cd infrastructure
docker-compose up -d postgres timescaledb redis zookeeper kafka
```

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn src.main:app --reload
```

Backend will be available at: http://localhost:8000
API documentation: http://localhost:8000/docs

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:3000

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

### Strategies
- `POST /api/strategies/` - Create a new strategy
- `GET /api/strategies/` - List user strategies
- `POST /api/strategies/{id}/start` - Start a strategy
- `POST /api/strategies/{id}/stop` - Stop a strategy

### Trading
- `GET /api/trading/positions` - Get open positions
- `GET /api/trading/orders` - Get trade orders

## Project Structure

```
velox-v5/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── endpoints/       # API route handlers
│   │   │   └── middleware/      # Request middleware
│   │   ├── core/                # Core utilities
│   │   │   ├── config.py        # Configuration
│   │   │   ├── security.py      # Authentication
│   │   │   └── redis_client.py  # Redis client
│   │   ├── models/              # Database models
│   │   │   ├── user.py
│   │   │   ├── strategy.py
│   │   │   ├── trading.py
│   │   │   └── market_data.py
│   │   ├── services/
│   │   │   ├── strategy_engine/ # Strategy execution
│   │   │   ├── market_data/     # Market data processing
│   │   │   └── broker_adapter/  # Broker integrations
│   │   ├── utils/               # Utilities
│   │   │   ├── logging.py
│   │   │   └── monitoring.py
│   │   └── main.py              # FastAPI app
│   ├── tests/                   # Test suites
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js app router
│   │   ├── components/          # React components
│   │   └── services/            # API services
│   ├── package.json
│   └── Dockerfile
├── infrastructure/
│   ├── docker-compose.yml       # Infrastructure services
│   └── prometheus.yml           # Prometheus config
└── specs/                       # Design documents
```

## Features

### Implemented
- ✅ User authentication and authorization
- ✅ Strategy creation and management
- ✅ Real-time tick processing
- ✅ Technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, Stochastic, ADX, VWAP)
- ✅ Order and position management
- ✅ Structured logging
- ✅ Performance monitoring with Prometheus
- ✅ Kafka message streaming
- ✅ Redis caching
- ✅ API documentation (FastAPI Swagger)

### To Be Implemented
- ⏳ Risk management (daily loss limits, drawdown monitoring)
- ⏳ Trailing stop-loss
- ⏳ Real-time analytics dashboard
- ⏳ WebSocket support for live updates
- ⏳ Live and paper trading modes
- ⏳ Multi-broker integration
- ⏳ Strategy backtesting
- ⏳ Advanced user management
- ⏳ Data export functionality
- ⏳ Alert notifications

## Development

### Code Quality

```bash
# Backend - Run linting and formatting
cd backend
black src/
isort src/
flake8 src/
mypy src/

# Frontend - Run linting
cd frontend
npm run lint
npm run type-check
```

### Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Pre-commit Hooks

Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

## Monitoring

### Prometheus Metrics
Available at: http://localhost:9090

Key metrics:
- `http_requests_total` - Total HTTP requests
- `strategy_executions_total` - Strategy executions
- `trade_orders_total` - Trade orders
- `active_strategies` - Active strategies count
- `daily_pnl` - Daily profit/loss

### Grafana Dashboards
Available at: http://localhost:3001
- Username: admin
- Password: admin

## Contributing

1. Create a feature branch from the main branch
2. Make your changes
3. Run tests and linting
4. Create a pull request

## License

Proprietary - All rights reserved

## Support

For issues and questions, please refer to the task documentation in `specs/001-algo-trading-platform/tasks.md`
