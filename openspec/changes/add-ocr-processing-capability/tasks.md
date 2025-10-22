# Implementation Tasks

## 1. Project Setup
- [ ] 1.1 Initialize Python project structure (pyproject.toml or setup.py)
- [ ] 1.2 Create directory structure (src/, tests/, docs/, scripts/)
- [ ] 1.3 Set up .gitignore for Python, venv, __pycache__, build artifacts
- [ ] 1.4 Create .env.example with configuration template
- [ ] 1.5 Add README.md with project overview and quick start
- [ ] 1.6 Set up requirements.txt or pyproject.toml with dependencies
- [ ] 1.7 Configure development tools (Black, isort, mypy, pytest)
- [ ] 1.8 Add pre-commit hooks for code quality

## 2. Core Dependencies
- [ ] 2.1 Install nats-py for NATS client
- [ ] 2.2 Install httpx for async HTTP client
- [ ] 2.3 Install pydantic for data validation
- [ ] 2.4 Install transformers and torch for DeepSeek-OCR
- [ ] 2.5 Install vllm for inference (or client for vLLM API)
- [ ] 2.6 Install pdf2image and Pillow for image processing
- [ ] 2.7 Install python-docx, python-pptx, openpyxl for office docs
- [ ] 2.8 Install structlog or Python logging for structured logging
- [ ] 2.9 Install pytest, pytest-asyncio, pytest-cov for testing
- [ ] 2.10 Install FastAPI and uvicorn (optional, if HTTP API needed)

## 3. Data Schemas (Pydantic Models)
- [ ] 3.1 Create src/schemas/job.py with OCRJob model
- [ ] 3.2 Create src/schemas/result.py with OCRResult model
- [ ] 3.3 Add CloudEvents envelope models
- [ ] 3.4 Add validation methods and custom validators
- [ ] 3.5 Add configuration schema (src/schemas/config.py)
- [ ] 3.6 Write unit tests for schema validation

## 4. OCR Engine Adapter
- [ ] 4.1 Define src/ocr/engine.py interface (Protocol class for OCREngine)
- [ ] 4.2 Implement src/ocr/deepseek.py (DeepSeekEngine with vLLM client)
- [ ] 4.3 Add async inference method with timeout support
- [ ] 4.4 Implement retry logic with tenacity or manual exponential backoff
- [ ] 4.5 Add structured error types (ValidationError, TransientError, PermanentError)
- [ ] 4.6 Create src/ocr/mock.py for testing without GPU
- [ ] 4.7 Add engine configuration and initialization
- [ ] 4.8 Write unit tests for engine adapter with mocks

## 5. Format Converters
- [ ] 5.1 Create src/converters/base.py with FormatConverter protocol
- [ ] 5.2 Implement src/converters/image.py (Pillow-based validation and normalization)
- [ ] 5.3 Implement src/converters/pdf.py (pdf2image wrapper)
- [ ] 5.4 Implement src/converters/office.py (python-docx, python-pptx, openpyxl)
- [ ] 5.5 Add MIME type detection and validation
- [ ] 5.6 Implement async file I/O where applicable
- [ ] 5.7 Add temporary file cleanup with context managers
- [ ] 5.8 Write unit tests with sample files in tests/fixtures/

## 6. Simple-Content HTTP Client
- [ ] 6.1 Create src/clients/content.py with SimpleContentClient class
- [ ] 6.2 Implement async download method using presigned URLs
- [ ] 6.3 Implement async upload method for derived content
- [ ] 6.4 Add metadata attachment for derived content
- [ ] 6.5 Implement status update methods
- [ ] 6.6 Add retry logic with httpx retry transport
- [ ] 6.7 Add authentication/authorization handling if required
- [ ] 6.8 Write integration tests with mocked httpx responses

## 7. Worker Service (NATS Consumer)
- [ ] 7.1 Create src/worker/main.py with async main function
- [ ] 7.2 Load configuration from environment variables (src/config.py)
- [ ] 7.3 Initialize NATS connection with nats-py
- [ ] 7.4 Subscribe to job queue with queue group ("ocr-workers")
- [ ] 7.5 Implement async job handler (download → convert → OCR → upload → publish)
- [ ] 7.6 Add idempotency checks (query existing derived content)
- [ ] 7.7 Implement lifecycle event publishing (started, progress, completed, failed)
- [ ] 7.8 Add graceful shutdown with signal handlers (SIGTERM, SIGINT)
- [ ] 7.9 Add structured logging with correlation IDs (job_id)
- [ ] 7.10 Add error handling and classification (validation, transient, permanent)

## 8. Lifecycle Events
- [ ] 8.1 Create src/events/publisher.py for event publishing
- [ ] 8.2 Implement CloudEvents v1.0 envelope formatting
- [ ] 8.3 Add event types (job.started, job.progress, job.completed, job.failed)
- [ ] 8.4 Implement async event publishing to NATS subjects
- [ ] 8.5 Add event serialization with pydantic
- [ ] 8.6 Write unit tests for event publishing

## 9. Job Processing Logic
- [ ] 9.1 Create src/processor/ocr_processor.py with main processing logic
- [ ] 9.2 Implement job validation (required fields, format support)
- [ ] 9.3 Implement content download and temporary storage
- [ ] 9.4 Implement format conversion pipeline
- [ ] 9.5 Implement OCR invocation with timeout
- [ ] 9.6 Implement multi-page handling for PDFs
- [ ] 9.7 Implement result aggregation (concatenate page markdown)
- [ ] 9.8 Implement derived content upload
- [ ] 9.9 Implement cleanup of temporary files
- [ ] 9.10 Add comprehensive error handling throughout

## 10. Retry and Dead Letter Queue
- [ ] 10.1 Implement retry logic with exponential backoff
- [ ] 10.2 Add retry count tracking in job metadata
- [ ] 10.3 Implement maximum retry limit (e.g., 3 retries)
- [ ] 10.4 Implement dead letter queue publishing for permanent failures
- [ ] 10.5 Add DLQ subject configuration ("ocr.dlq")
- [ ] 10.6 Write tests for retry scenarios

## 11. Backfill Utility
- [ ] 11.1 Create src/backfill/main.py with CLI using Click or argparse
- [ ] 11.2 Implement content enumeration via simple-content API
- [ ] 11.3 Add filtering (by MIME type, tenant, owner, date range)
- [ ] 11.4 Add filter for content without existing OCR
- [ ] 11.5 Implement job submission to NATS
- [ ] 11.6 Add dry-run mode (--dry-run flag)
- [ ] 11.7 Add batch processing with rate limiting
- [ ] 11.8 Add progress reporting (tqdm or similar)
- [ ] 11.9 Implement checkpoint/resume capability
- [ ] 11.10 Write CLI tests

## 12. Optional HTTP API (FastAPI)
- [ ] 12.1 Create src/api/main.py with FastAPI app
- [ ] 12.2 Add /health endpoint for readiness checks
- [ ] 12.3 Add POST /ocr endpoint for synchronous OCR requests
- [ ] 12.4 Implement async job submission to NATS
- [ ] 12.5 Add request validation with pydantic
- [ ] 12.6 Add response models
- [ ] 12.7 Add CORS middleware if needed
- [ ] 12.8 Write API integration tests with FastAPI TestClient

## 13. Configuration Management
- [ ] 13.1 Create src/config.py with Pydantic BaseSettings
- [ ] 13.2 Load from environment variables
- [ ] 13.3 Support .env file loading with python-dotenv
- [ ] 13.4 Add validation for required configuration
- [ ] 13.5 Add default values for optional configuration
- [ ] 13.6 Document all configuration options in .env.example
- [ ] 13.7 Write tests for configuration loading

## 14. Logging and Observability
- [ ] 14.1 Set up structured logging with structlog
- [ ] 14.2 Add JSON log formatter for production
- [ ] 14.3 Add correlation IDs (job_id, request_id) to all log entries
- [ ] 14.4 Implement log level configuration (DEBUG, INFO, WARNING, ERROR)
- [ ] 14.5 Add timing metrics (processing duration per stage)
- [ ] 14.6 Add Prometheus metrics collection (optional)
- [ ] 14.7 Document logging format and fields

## 15. Testing
- [ ] 15.1 Write unit tests for converters (src/converters/)
- [ ] 15.2 Write unit tests for OCR engine adapter with mocks
- [ ] 15.3 Write unit tests for schemas and validation
- [ ] 15.4 Write integration tests for NATS worker
- [ ] 15.5 Write integration tests for simple-content client
- [ ] 15.6 Write end-to-end test with sample documents
- [ ] 15.7 Add test fixtures (sample images, PDFs, office docs)
- [ ] 15.8 Set up pytest configuration (pytest.ini or pyproject.toml)
- [ ] 15.9 Run tests with coverage (pytest-cov)
- [ ] 15.10 Add performance benchmarks (pytest-benchmark)

## 16. Documentation
- [ ] 16.1 Write README.md with architecture overview
- [ ] 16.2 Document configuration options
- [ ] 16.3 Document vLLM deployment and setup
- [ ] 16.4 Document format support and limitations
- [ ] 16.5 Create installation guide (docs/installation.md)
- [ ] 16.6 Create troubleshooting guide (docs/troubleshooting.md)
- [ ] 16.7 Document API endpoints (if FastAPI used)
- [ ] 16.8 Add example usage and code samples
- [ ] 16.9 Document monitoring and observability
- [ ] 16.10 Add architecture diagrams (optional)

## 17. Deployment
- [ ] 17.1 Create Dockerfile with multi-stage build
- [ ] 17.2 Create docker-compose.yml for local development
- [ ] 17.3 Add environment variable templates (.env.example)
- [ ] 17.4 Create deployment guide (docs/deployment.md)
- [ ] 17.5 Document GPU requirements and CUDA setup
- [ ] 17.6 Create Kubernetes manifests (optional)
- [ ] 17.7 Document scaling recommendations
- [ ] 17.8 Create health check scripts

## 18. CI/CD
- [ ] 18.1 Set up GitHub Actions or GitLab CI
- [ ] 18.2 Add linting workflow (Black, isort, mypy, flake8)
- [ ] 18.3 Add test workflow (pytest with coverage)
- [ ] 18.4 Add Docker build workflow
- [ ] 18.5 Add dependency security scanning (pip-audit, safety)
- [ ] 18.6 Add automated release workflow (optional)

## 19. Final Integration and Testing
- [ ] 19.1 Deploy vLLM service with DeepSeek-OCR model
- [ ] 19.2 Deploy worker service (1 instance initially)
- [ ] 19.3 Configure NATS subjects and queue groups
- [ ] 19.4 Validate with test documents (images, PDFs, office docs)
- [ ] 19.5 Test error scenarios (missing content, invalid format, timeouts)
- [ ] 19.6 Test scaling (multiple workers)
- [ ] 19.7 Load testing with realistic workload
- [ ] 19.8 Monitor logs and metrics
- [ ] 19.9 Verify lifecycle events are published correctly
- [ ] 19.10 Document any issues and resolutions
