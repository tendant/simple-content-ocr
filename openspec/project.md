# Project Context

## Purpose
OCR service that converts documents (images, PDFs, office documents) to markdown using modern AI-powered OCR models. Built to integrate seamlessly with the simple-content and simple-process ecosystem following the simple-thumbnailer architecture pattern.

## Tech Stack
- **Language**: Python 3.11+
- **Web Framework**: FastAPI (for HTTP API if needed)
- **OCR Engine**: DeepSeek-OCR (LLM-based vision-language model) or other generative AI models
- **Inference**: vLLM for production serving (~2500 tokens/sec on A100)
- **Messaging**: NATS with CloudEvents for async job processing
- **Content Management**: simple-content HTTP API for storage abstraction
- **Process Framework**: simple-process patterns for job orchestration
- **Key Libraries**:
  - transformers (DeepSeek-OCR integration)
  - vllm (high-performance LLM inference)
  - nats-py (NATS client)
  - pdf2image/pypdfium2 (PDF to image conversion)
  - python-docx, python-pptx, openpyxl (Office document parsing)
  - Pillow (image processing)
  - pydantic (data validation)

## Project Conventions

### Code Style
- Follow PEP 8 with Black formatter and isort for imports
- Use type hints throughout (enforced with mypy)
- Use structured logging (structlog or Python's logging with JSON formatter)
- Async/await patterns for I/O operations
- Clear separation between application layers (routes, services, adapters)

### Architecture Patterns
- **Worker Pattern**: NATS consumer processing jobs asynchronously
- **Adapter Pattern**: Pluggable OCR engines for flexibility
- **Repository Pattern**: Abstract storage and metadata persistence
- **Lifecycle Events**: Publish job status updates via NATS
- **Idempotency**: Job IDs ensure safe retries
- **Presigned URLs**: Stream content without copying payloads

### Testing Strategy
- pytest for unit and integration tests
- pytest-asyncio for async test cases
- Mock OCR engine for testing without GPU dependencies
- Integration tests with NATS using testcontainers or nats-py test utilities
- httpx for testing HTTP client interactions with simple-content API
- Coverage target: 80%+ with pytest-cov
- Performance benchmarks using pytest-benchmark

### Git Workflow
- Main branch: `main`
- Feature branches: `feature/<description>`
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- OpenSpec workflow: proposal → implementation → archive

## Domain Context
- **Derived Content**: OCR output stored as derived content linked to source files
- **Multi-Format Support**: Different preprocessing pipelines for images vs PDFs vs office docs
- **Status Tracking**: Three-tier system (Content Status, Object Status, Derived Content Status)
- **Multi-Tenant**: Support for owner/tenant ID filtering and isolation
- **Language Detection**: Automatic via LLM capabilities (no explicit configuration needed)

## Important Constraints
- **GPU Requirements**: DeepSeek-OCR requires CUDA-capable GPU (A100 recommended for production)
- **Model Size**: Large model downloads (~10GB+) required for deployment
- **Latency**: LLM inference slower than traditional OCR (trade-off for quality/layout preservation)
- **Memory**: vLLM requires significant GPU memory for concurrent requests
- **Python Version**: Requires Python 3.11+ for best async performance and type hint support
- **Async I/O**: All I/O operations must be async to avoid blocking NATS event loop

## External Dependencies
- **simple-content**: Content storage and retrieval via HTTP API (https://github.com/tendant/simple-content)
- **simple-process**: Job processing patterns (https://github.com/tendant/simple-process)
- **DeepSeek-OCR**: AI model for document understanding (https://github.com/deepseek-ai/DeepSeek-OCR)
- **vLLM**: High-performance inference server (https://github.com/vllm-project/vllm)
- **NATS**: Message broker for job distribution
- **Poppler**: PDF rendering utilities (via pdf2image Python wrapper)
- **System libraries**: libpoppler, libjpeg, libpng (for image processing)
