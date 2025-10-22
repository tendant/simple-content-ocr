# Multi-stage build for simple-ocr service
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    python3.11 \
    python3.11-dev \
    poppler-utils \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Copy application code
COPY src/ ./src/

# Install dependencies using uv
RUN uv sync --frozen --no-dev --no-install-project

# Install the project
RUN uv sync --frozen --no-dev

# Create temp directory
RUN mkdir -p /tmp/simple-ocr

# Non-root user for security
RUN useradd -m -u 1000 ocr && \
    chown -R ocr:ocr /app /tmp/simple-ocr

USER ocr

# Expose port
EXPOSE 8000

# Default command (can be overridden for worker vs API)
CMD ["uv", "run", "uvicorn", "simple_ocr.main:app", "--host", "0.0.0.0", "--port", "8000"]
