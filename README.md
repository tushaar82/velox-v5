# Velox Trading Platform

High-Frequency Algorithmic Trading Platform built with FastAPI, Next.js, and TimescaleDB.

## Features

- Real-time trading strategy execution with tick-by-tick data processing
- Risk management with daily loss limits and trailing stoploss
- Multi-broker integration for Indian stock markets
- Real-time analytics dashboard
- Live and paper trading modes
- Strategy backtesting and validation
- User account management with role-based access control

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Databases**: PostgreSQL, TimescaleDB
- **Caching**: Redis
- **Message Queue**: Kafka
- **Authentication**: JWT
- **Monitoring**: Prometheus

### Frontend
- **Framework**: Next.js 14
- **UI**: shadcn/ui, TailwindCSS
- **Charts**: Lightweight Charts, Recharts
- **State Management**: Zustand
- **Real-time**: Socket.io

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker and Docker Compose

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
   uvicorn src.main:app --reload
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

Run the entire stack with Docker:

```bash
cd infrastructure
docker-compose up
```

## Project Structure

```
velox-v5/
├── backend/           # FastAPI backend
│   ├── src/
│   │   ├── api/      # API endpoints and middleware
│   │   ├── core/     # Core configuration and utilities
│   │   ├── models/   # Database models
│   │   ├── services/ # Business logic
│   │   └── utils/    # Utilities and helpers
│   ├── tests/        # Tests
│   └── alembic/      # Database migrations
├── frontend/         # Next.js frontend
│   ├── src/
│   │   ├── app/      # Next.js app router
│   │   ├── components/ # React components
│   │   ├── services/ # API clients
│   │   └── utils/    # Utilities
│   └── tests/        # Tests
├── infrastructure/   # Docker compose and configs
└── specs/           # Specifications and documentation
```

## Development

### Running Tests

**Backend:**
```bash
cd backend
pytest
pytest --cov=src --cov-report=html
```

**Frontend:**
```bash
cd frontend
npm test
npm run test:coverage
```

### Code Quality

**Backend:**
```bash
# Format code
black src/
isort src/

# Lint
flake8 src/
mypy src/
pylint src/
```

**Frontend:**
```bash
# Format code
npm run format

# Lint
npm run lint

# Type check
npm run type-check
```

## Performance Targets

- Tick processing: < 50ms
- Indicator updates: < 50ms
- Trade execution: < 100ms
- Dashboard updates: < 1s
- Risk management response: < 200ms

## License

Proprietary - All rights reserved

## Support

For issues and questions, please open an issue in the repository.
