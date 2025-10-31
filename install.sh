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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Print banner
echo "======================================"
echo "  Velox V5 - Installation Script"
echo "======================================"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python found: $PYTHON_VERSION"
else
    print_error "Python 3.11+ is required but not found"
    exit 1
fi

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found: $NODE_VERSION"
else
    print_error "Node.js 20+ is required but not found"
    exit 1
fi

# Check npm
if command_exists npm; then
    NPM_VERSION=$(npm --version)
    print_success "npm found: $NPM_VERSION"
else
    print_error "npm is required but not found"
    exit 1
fi

# Check Docker
if command_exists docker; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    print_success "Docker found: $DOCKER_VERSION"
else
    print_error "Docker is required but not found"
    exit 1
fi

# Check Docker Compose
if docker compose version >/dev/null 2>&1; then
    COMPOSE_VERSION=$(docker compose version | cut -d' ' -f4)
    print_success "Docker Compose found: $COMPOSE_VERSION"
else
    print_error "Docker Compose is required but not found"
    exit 1
fi

echo ""

# Setup environment file
print_info "Setting up environment configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    print_success "Created .env file from .env.example"
    print_warning "Please review and update .env file with your configuration"
else
    print_success ".env file already exists"
fi

echo ""

# Backend setup
print_info "Setting up backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv .venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
print_info "Installing backend dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
print_success "Backend dependencies installed"

cd ..
echo ""

# Frontend setup
print_info "Setting up frontend..."
cd frontend

print_info "Installing frontend dependencies..."
npm install
print_success "Frontend dependencies installed"

cd ..
echo ""

# Infrastructure setup
print_info "Setting up infrastructure services..."
cd infrastructure

print_info "Starting infrastructure services (PostgreSQL, TimescaleDB, Redis, Kafka)..."
docker compose up -d postgres timescaledb redis zookeeper kafka
print_success "Infrastructure services started"

echo ""
print_info "Waiting for services to be healthy (this may take 30-60 seconds)..."
sleep 10

# Wait for PostgreSQL
print_info "Waiting for PostgreSQL..."
until docker compose exec -T postgres pg_isready -U velox > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo ""
print_success "PostgreSQL is ready"

# Wait for TimescaleDB
print_info "Waiting for TimescaleDB..."
until docker compose exec -T timescaledb pg_isready -U velox > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo ""
print_success "TimescaleDB is ready"

# Wait for Redis
print_info "Waiting for Redis..."
until docker compose exec -T redis redis-cli --pass velox_redis_password ping > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
print_success "Redis is ready"

# Wait for Kafka
print_info "Waiting for Kafka..."
sleep 15
print_success "Kafka should be ready"

cd ..
echo ""

# Run database migrations
print_info "Running database migrations..."
cd backend
source .venv/bin/activate
alembic upgrade head
print_success "Database migrations completed"
cd ..

echo ""
echo "======================================"
print_success "Installation completed successfully!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. Review and update .env file if needed"
echo "  2. Run './run.sh dev' to start in development mode"
echo "  3. Run './run.sh prod' to start in production mode (Docker)"
echo "  4. Access the application:"
echo "     - Frontend: http://localhost:3000"
echo "     - Backend API: http://localhost:8000"
echo "     - API Docs: http://localhost:8000/docs"
echo "     - Prometheus: http://localhost:9090"
echo ""
echo "For more information, see README.md"
echo ""
