# simple-content-ocr

AI-powered OCR service that converts documents (images, PDFs, office documents) to markdown using modern AI-powered OCR models. Built to integrate seamlessly with the simple-content and simple-process ecosystem.

## Features

- **Multi-format Support**: Process images (JPG, PNG, TIFF, etc.), PDFs, and office documents (DOCX, PPTX, XLSX)
- **AI-Powered OCR**: Uses PaddleOCR-VL (recommended), Qwen2-VL, or other LLM-based vision models
- **Markdown Output**: Preserves document structure and layout in clean markdown format
- **Async Processing**: NATS-based worker pattern for scalable job processing
- **Simple Content Integration**: Seamless integration with simple-content API for storage
- **GPU Acceleration**: vLLM for high-performance processing

## Tech Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **OCR Engine**: PaddleOCR-VL (recommended), Qwen2-VL, or other vision-language models
- **Inference**: vLLM for high-performance GPU acceleration
- **Messaging**: NATS with CloudEvents
- **Content Management**: simple-content HTTP API

## Quick Start

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer and resolver
- CUDA-capable GPU (for production OCR, optional for development with mock engine)
- NATS server (or use docker-compose)
- simple-content API (or use docker-compose)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/simple-content-ocr.git
cd simple-content-ocr
```

2. Run the setup script:
```bash
./scripts/setup.sh
```

3. Or manually set up:
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates .venv automatically)
uv sync

# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration
```

### Running with Docker Compose

The easiest way to get started:

```bash
# Start all services (NATS, simple-content, OCR worker, OCR API)
docker-compose up -d

# View logs
docker-compose logs -f ocr-worker

# Stop services
docker-compose down
```

### Running Locally

1. Start NATS and simple-content (or use external services)
2. Configure `.env` with your service URLs
3. Start the OCR worker:

```bash
uv run python -m simple_ocr.workers.nats_worker
# Or: make run-worker
```

4. Or start the HTTP API:

```bash
uv run uvicorn simple_ocr.main:app --host 0.0.0.0 --port 8000 --reload
# Or: make run-api
```

### Inference Server Setup

The OCR service requires a vision-language model inference server.

#### ⚠️ Important: PaddleOCR-VL is NOT compatible with vLLM

**Use the Custom PaddleOCR Server instead:**

```bash
# Install dependencies (one-time setup)
uv venv --python 3.12 --seed
uv sync

# Start the custom server (uses HuggingFace transformers with trust_remote_code=True)
uv run python scripts/run_paddleocr_server.py --host 0.0.0.0 --port 8000
```

The custom server:
- ✅ Uses regular HuggingFace `transformers` (not vLLM)
- ✅ Provides OpenAI-compatible API
- ✅ Works with all GPUs (~1.8GB VRAM)

See `CUSTOM_SERVER_SETUP.md` for detailed setup.

**Configure OCR service to use the custom server:**

```bash
export OCR_ENGINE=vllm  # Uses OpenAI-compatible API
export VLLM_URL=http://localhost:8000
export MODEL_NAME=PaddlePaddle/PaddleOCR-VL
```

## Development

### Project Structure

```
simple-content-ocr/
├── src/simple_ocr/
│   ├── adapters/       # OCR engines and external service adapters
│   ├── models/         # Data models
│   ├── routes/         # FastAPI routes
│   ├── services/       # Business logic
│   ├── workers/        # NATS worker implementations
│   ├── config.py       # Configuration management
│   └── main.py         # FastAPI application
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── docs/               # Documentation
├── scripts/            # Utility scripts
└── openspec/           # OpenSpec change proposals
```

### Development Commands

```bash
# Sync dependencies
make sync  # or: uv sync

# Run tests with coverage
make test  # or: uv run pytest

# Run linters
make lint  # or: uv run ruff check src/ tests/

# Format code
make format  # or: uv run black src/ tests/

# Run API server
make run-api

# Run worker
make run-worker

# Clean build artifacts
make clean
```

### Testing

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest tests/unit/

# Run with coverage report
uv run pytest --cov=simple_ocr --cov-report=html

# Run specific test
uv run pytest tests/unit/test_config.py
```

### Code Quality

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **Ruff** for linting
- **mypy** for type checking

Run all checks with:
```bash
make lint    # Check code quality
make format  # Auto-format code
```

**Why uv?**
- 10-100x faster than pip
- Reliable dependency resolution
- Built-in virtual environment management
- Deterministic builds with lockfile

## Architecture

### Worker Pattern

The service follows a worker-based architecture:

1. Jobs are published to NATS JetStream as CloudEvents
2. Workers subscribe to job streams and process documents asynchronously
3. Results are stored back to simple-content as derived content
4. Status updates are published via NATS for monitoring

### OCR Processing Pipeline

1. **Download**: Fetch source content via presigned URL from simple-content
2. **Preprocess**: Convert documents to images (PDF → images, Office docs → images)
3. **OCR**: Process images with AI model to extract text and structure
4. **Post-process**: Format output as markdown
5. **Upload**: Store markdown as derived content via simple-content API
6. **Notify**: Publish completion event via NATS

## Configuration

See `.env.example` for all available configuration options.

Key settings:
- `OCR_ENGINE`: Choose between `deepseek` (requires GPU) or `mock` (for testing)
- `NATS_URL`: NATS server connection URL
- `CONTENT_API_URL`: simple-content API base URL
- `VLLM_GPU_MEMORY_UTILIZATION`: GPU memory allocation (0.0-1.0)

## Contributing

This project uses OpenSpec for managing changes. See `openspec/AGENTS.md` for details on the proposal and implementation workflow.

1. Create a proposal using `/openspec:proposal`
2. Implement the approved change using `/openspec:apply`
3. Archive deployed changes using `/openspec:archive`

## License

MIT License - see LICENSE file for details

## Related Projects

- [simple-content](https://github.com/tendant/simple-content) - Content storage and management API
- [simple-process](https://github.com/tendant/simple-process) - Job processing framework
- [DeepSeek-OCR](https://github.com/deepseek-ai/DeepSeek-OCR) - AI-powered OCR model
- [vLLM](https://github.com/vllm-project/vllm) - High-performance LLM inference

## Support

For issues and questions, please open a GitHub issue.