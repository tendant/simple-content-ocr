#!/bin/bash
set -e

echo "Setting up simple-ocr development environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "Please restart your shell or run: source $HOME/.cargo/env"
    exit 1
fi

# Sync dependencies and create virtual environment
echo "Syncing dependencies with uv..."
uv sync

# Create .env from example if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "Please edit .env with your configuration"
fi

# Create temp directory
mkdir -p /tmp/simple-ocr

echo ""
echo "Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "Or use uv to run commands directly:"
echo "  uv run pytest"
echo "  uv run uvicorn simple_ocr.main:app --reload"
