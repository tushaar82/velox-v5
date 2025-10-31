#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Print banner
echo "======================================"
echo "  Velox V5 - Run Script"
echo "======================================"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found. Please run ./install.sh first"
    exit 1
fi

# Determine run mode
MODE=${1:-dev}

if [ "$MODE" != "dev" ] && [ "$MODE" != "prod" ]; then
    print_error "Invalid mode. Use: ./run.sh [dev|prod]"
    echo ""
    echo "Modes:"
    echo "  dev  - Development mode (backend & frontend run locally, infrastructure in Docker)"
    echo "  prod - Production mode (everything runs in Docker)"
    exit 1
fi

print_info "Starting Velox V5 in $MODE mode..."
echo ""

# Start infrastructure services
print_info "Starting infrastructure services..."
cd infrastructure
docker compose up -d postgres timescaledb redis zookeeper kafka prometheus
print_success "Infrastructure services started"

# Wait for services to be healthy
print_info "Waiting for services to be ready..."
sleep 5

# Check PostgreSQL
print_info "Checking PostgreSQL..."
until docker compose exec -T postgres pg_isready -U velox > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo ""
print_success "PostgreSQL is ready"

# Check TimescaleDB
print_info "Checking TimescaleDB..."
until docker compose exec -T timescaledb pg_isready -U velox > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo ""
print_success "TimescaleDB is ready"

# Check Redis
print_info "Checking Redis..."
until docker compose exec -T redis redis-cli --pass velox_redis_password ping > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
print_success "Redis is ready"

print_info "Waiting for Kafka to initialize..."
sleep 10
print_success "Kafka should be ready"

cd ..
echo ""

if [ "$MODE" = "prod" ]; then
    # Production mode - run everything in Docker
    print_info "Starting backend and frontend in Docker..."
    cd infrastructure
    docker compose up -d backend frontend
    cd ..

    print_success "All services started in production mode"
    echo ""
    echo "======================================"
    echo "  Services Running"
    echo "======================================"
    echo "  Frontend:    http://localhost:3000"
    echo "  Backend API: http://localhost:8000"
    echo "  API Docs:    http://localhost:8000/docs"
    echo "  Prometheus:  http://localhost:9090"
    echo "======================================"
    echo ""
    echo "To view logs:"
    echo "  docker compose -f infrastructure/docker-compose.yml logs -f backend"
    echo "  docker compose -f infrastructure/docker-compose.yml logs -f frontend"
    echo ""
    echo "To stop all services:"
    echo "  ./stop.sh"
    echo ""

elif [ "$MODE" = "dev" ]; then
    # Development mode - run backend and frontend locally
    print_info "Starting backend and frontend in development mode..."

    # Check if ports are available
    if check_port 8000; then
        print_warning "Port 8000 is already in use"
    fi
    if check_port 3000; then
        print_warning "Port 3000 is already in use"
    fi

    # Create log directory
    mkdir -p logs

    # Start backend
    print_info "Starting backend on port 8000..."
    cd backend
    source .venv/bin/activate

    # Run migrations
    print_info "Running database migrations..."
    alembic upgrade head
    print_success "Migrations completed"

    # Start backend in background
    nohup uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../logs/backend.pid
    print_success "Backend started (PID: $BACKEND_PID)"
    cd ..

    # Wait for backend to be ready
    print_info "Waiting for backend to be ready..."
    sleep 5
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "Backend is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Backend failed to start. Check logs/backend.log"
            exit 1
        fi
        echo -n "."
        sleep 2
    done
    echo ""

    # Start frontend
    print_info "Starting frontend on port 3000..."
    cd frontend
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../logs/frontend.pid
    print_success "Frontend started (PID: $FRONTEND_PID)"
    cd ..

    # Wait for frontend to be ready
    print_info "Waiting for frontend to be ready..."
    sleep 10
    print_success "Frontend should be ready"

    echo ""
    print_success "All services started in development mode"
    echo ""
    echo "======================================"
    echo "  Services Running"
    echo "======================================"
    echo "  Frontend:    http://localhost:3000"
    echo "  Backend API: http://localhost:8000"
    echo "  API Docs:    http://localhost:8000/docs"
    echo "  Prometheus:  http://localhost:9090"
    echo "======================================"
    echo ""
    echo "Process IDs:"
    echo "  Backend:  $BACKEND_PID (logs/backend.log)"
    echo "  Frontend: $FRONTEND_PID (logs/frontend.log)"
    echo ""
    echo "To view logs:"
    echo "  tail -f logs/backend.log"
    echo "  tail -f logs/frontend.log"
    echo ""
    echo "To stop all services:"
    echo "  ./stop.sh"
    echo ""
fi
