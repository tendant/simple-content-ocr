#!/bin/bash
# Start PaddleOCR-VL custom server
# Usage: ./scripts/start_paddleocr_server.sh [OPTIONS]

set -e

# Default values
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8001}"
WORKERS="${WORKERS:-1}"
LOG_LEVEL="${LOG_LEVEL:-info}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  PaddleOCR-VL Custom Inference Server${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Check if running in project root
if [ ! -f "requirements-server.txt" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements-server.txt
fi

# Check for GPU
if python -c "import torch; print(torch.cuda.is_available())" | grep -q "True"; then
    echo -e "${GREEN}✓ GPU detected${NC}"
    python -c "import torch; print('  Device:', torch.cuda.get_device_name(0))"
else
    echo "⚠ No GPU detected - running on CPU (will be slow)"
fi

echo ""
echo "Starting server..."
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Workers: $WORKERS"
echo ""

# Run server
python scripts/run_paddleocr_server.py \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL" \
    "$@"
