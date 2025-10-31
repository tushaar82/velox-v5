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

# Print banner
echo "======================================"
echo "  Velox V5 - Stop Script"
echo "======================================"
echo ""

# Parse options
CLEAN_VOLUMES=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN_VOLUMES=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo ""
            echo "Usage: ./stop.sh [options]"
            echo ""
            echo "Options:"
            echo "  --clean    Remove all data volumes (WARNING: This will delete all data!)"
            echo "  --force    Force stop without confirmation"
            exit 1
            ;;
    esac
done

# Confirmation for clean
if [ "$CLEAN_VOLUMES" = true ] && [ "$FORCE" = false ]; then
    print_warning "WARNING: --clean will remove all data volumes including database data!"
    echo -n "Are you sure you want to continue? (yes/no): "
    read -r response
    if [ "$response" != "yes" ]; then
        print_info "Cancelled"
        exit 0
    fi
fi

print_info "Stopping Velox V5 services..."
echo ""

# Stop local development processes if running
if [ -f logs/backend.pid ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        print_info "Stopping backend process (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true

        # Wait for process to stop
        for i in {1..10}; do
            if ! kill -0 $BACKEND_PID 2>/dev/null; then
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if kill -0 $BACKEND_PID 2>/dev/null; then
            print_warning "Force killing backend process..."
            kill -9 $BACKEND_PID 2>/dev/null || true
        fi

        print_success "Backend process stopped"
    fi
    rm -f logs/backend.pid
fi

if [ -f logs/frontend.pid ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        print_info "Stopping frontend process (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null || true

        # Wait for process to stop
        for i in {1..10}; do
            if ! kill -0 $FRONTEND_PID 2>/dev/null; then
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            print_warning "Force killing frontend process..."
            kill -9 $FRONTEND_PID 2>/dev/null || true
        fi

        print_success "Frontend process stopped"
    fi
    rm -f logs/frontend.pid
fi

# Also try to kill by process name (in case PID files are missing)
print_info "Cleaning up any remaining backend/frontend processes..."
pkill -f "uvicorn src.main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 2

echo ""

# Stop Docker containers
print_info "Stopping Docker containers..."
cd infrastructure

if [ "$CLEAN_VOLUMES" = true ]; then
    print_info "Stopping containers and removing volumes..."
    docker compose down -v
    print_success "All containers stopped and volumes removed"
else
    docker compose down
    print_success "All containers stopped"
fi

cd ..

# Clean up log files if requested
if [ "$CLEAN_VOLUMES" = true ]; then
    print_info "Cleaning up log files..."
    rm -rf logs/*.log
    print_success "Log files removed"
fi

echo ""
echo "======================================"
print_success "All services stopped successfully"
echo "======================================"
echo ""

if [ "$CLEAN_VOLUMES" = true ]; then
    print_warning "All data has been removed. You will need to run ./install.sh again"
    echo ""
    echo "Next steps:"
    echo "  1. Run ./install.sh to reinitialize the system"
    echo "  2. Run ./run.sh [dev|prod] to start services"
else
    echo "Data volumes are preserved. You can restart with:"
    echo "  ./run.sh [dev|prod]"
fi
echo ""
