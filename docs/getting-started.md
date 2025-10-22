# Getting Started with Simple Content OCR

This guide will help you set up and start developing with the simple-content-ocr service.

## Initial Setup Complete

The project structure has been initialized with:

- **Python package configuration** (`pyproject.toml`)
- **Dependency management** with **uv** (`uv.lock` for reproducible builds)
- **Configuration system** (`.env.example`, `config.py`)
- **Docker setup** (`Dockerfile`, `docker-compose.yml`)
- **Development tools** (`Makefile`, `pytest.ini`)
- **Basic application structure** (`src/simple_ocr/`)
- **Test structure** (`tests/`)

## Next Steps

### 1. Set Up Your Development Environment

**Using uv (recommended):**

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run the setup script
./scripts/setup.sh

# Or manually:
uv sync                  # Install all dependencies
cp .env.example .env     # Configure environment
# Edit .env as needed
```

**Why uv?**
- 10-100x faster than pip for dependency installation
- Automatic virtual environment management (creates `.venv`)
- Lockfile (`uv.lock`) ensures reproducible builds
- Single tool for package management and running commands

### 2. Core Components to Implement

The following components need to be implemented (use OpenSpec workflow):

#### A. OCR Engine Adapters (`src/simple_ocr/adapters/`)
- `ocr_base.py` - Abstract base class for OCR engines
- `deepseek_ocr.py` - DeepSeek-OCR implementation
- `mock_ocr.py` - Mock OCR for testing
- `content_client.py` - Simple Content API client

#### B. Services (`src/simple_ocr/services/`)
- `document_processor.py` - Document preprocessing (PDF to images, etc.)
- `ocr_service.py` - OCR orchestration logic
- `storage_service.py` - Content storage integration

#### C. Workers (`src/simple_ocr/workers/`)
- `nats_worker.py` - NATS consumer for async job processing
- `job_handler.py` - Job execution logic

#### D. Routes (`src/simple_ocr/routes/`)
- `jobs.py` - Job submission and status endpoints
- `health.py` - Health check endpoints

### 3. Implementation Workflow

This project uses **OpenSpec** for managing changes. For each component:

1. **Create a proposal**:
   ```bash
   # Use the slash command
   /openspec:proposal
   ```

2. **Implement the change**:
   ```bash
   # After approval
   /openspec:apply
   ```

3. **Archive when deployed**:
   ```bash
   # After deployment
   /openspec:archive
   ```

### 4. Suggested Implementation Order

1. **Mock OCR Engine** - Start with a simple mock for testing
2. **Content Client** - Implement simple-content API integration
3. **Document Processor** - Add preprocessing for different formats
4. **OCR Service** - Implement core orchestration
5. **NATS Worker** - Add async job processing
6. **API Routes** - Add HTTP endpoints
7. **DeepSeek Integration** - Add real OCR engine
8. **Tests** - Add comprehensive test coverage

### 5. Testing as You Go

```bash
# Run tests
make test                                    # or: uv run pytest

# Run specific test
uv run pytest tests/unit/test_config.py -v

# Check code quality
make lint                                    # or: uv run ruff check src/ tests/
make format                                  # or: uv run black src/ tests/
```

### 6. Running the Service

#### Development Mode

```bash
# Start API server
make run-api                                 # or: uv run uvicorn simple_ocr.main:app --reload

# Start worker (once implemented)
make run-worker                              # or: uv run python -m simple_ocr.workers.nats_worker
```

#### Docker Mode

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f ocr-worker

# Stop
docker-compose down
```

## Architecture Overview

```
┌─────────────────┐
│  simple-content │
│      API        │
└────────┬────────┘
         │
         │ Presigned URLs
         │
┌────────▼────────┐     ┌──────────────┐
│  NATS JetStream │◄────┤  OCR Worker  │
│   (Job Queue)   │     │   (Consumer) │
└────────┬────────┘     └──────┬───────┘
         │                     │
         │                     │ Process
         │                     ▼
         │              ┌──────────────┐
         │              │  OCR Engine  │
         │              │ (DeepSeek)   │
         │              └──────────────┘
         │
         │ Store Results
         ▼
┌─────────────────┐
│  simple-content │
│   (Derived)     │
└─────────────────┘
```

## Key Design Decisions

1. **Async-First**: All I/O operations use async/await
2. **Pluggable OCR**: Abstract adapter pattern for different OCR engines
3. **Presigned URLs**: No data copying, stream directly from storage
4. **CloudEvents**: Standard event format for NATS messages
5. **Type Safety**: Full type hints with mypy checking
6. **Idempotency**: Job IDs ensure safe retries

## Resources

- [OpenSpec Documentation](../openspec/AGENTS.md)
- [Project Specifications](../openspec/project.md)
- [Simple Content API](https://github.com/tendant/simple-content)
- [DeepSeek-OCR](https://github.com/deepseek-ai/DeepSeek-OCR)
- [vLLM Documentation](https://docs.vllm.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [NATS Documentation](https://docs.nats.io/)

## Getting Help

- Check the OpenSpec AGENTS.md for AI assistant guidelines
- Review existing patterns in simple-content and simple-process repos
- Open GitHub issues for bugs or questions
