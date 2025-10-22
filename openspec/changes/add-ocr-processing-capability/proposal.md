# Proposal: Add OCR Processing Capability

## Why

Modern document processing requires extracting structured text from images, PDFs, and office documents while preserving layout and formatting. Traditional OCR engines like Tesseract provide character-level recognition but lose semantic understanding and layout context. Recent advances in vision-language models (like DeepSeek-OCR) enable document-to-markdown conversion that maintains structure, understands context, and produces cleaner output suitable for downstream processing.

This OCR service fills a critical gap in the content processing pipeline by converting unstructured visual documents into structured markdown that can be searched, indexed, and analyzed. Following the proven simple-thumbnailer architecture pattern ensures consistency with existing services and leverages the simple-content and simple-process ecosystem.

## What Changes

- **New capability**: OCR service for document-to-markdown conversion
- **Core features**:
  - Process images (PNG, JPEG, TIFF, GIF, BMP, WebP) via AI-powered OCR
  - Extract text from multi-page PDFs with layout preservation
  - Process office documents (DOCX, PPTX, XLSX) by extracting embedded images
  - Automatic language detection via LLM capabilities
  - Output markdown with preserved formatting and structure
- **Architecture**:
  - Python-based worker service consuming NATS jobs
  - Integration with simple-content HTTP API for upload/download
  - Follows simple-process patterns for job orchestration
  - Pluggable OCR engine support (initial: DeepSeek-OCR via vLLM)
  - Optional FastAPI HTTP API for synchronous OCR requests
- **Infrastructure**:
  - vLLM inference server for production deployment
  - Format conversion utilities (Poppler for PDF, LibreOffice for office docs)
  - CUDA-capable GPU infrastructure (A100 recommended)
- **Operations**:
  - Status tracking (pending, processing, completed, failed)
  - Lifecycle event publishing (job.started, job.completed, job.failed)
  - Idempotent job processing with retry support
  - Backfill utility for batch processing existing content

## Impact

### Affected Specs
- **NEW**: `ocr-service` - Core OCR processing capability
- **NEW**: `content-integration` - Integration with simple-content library
- **NEW**: `job-processing` - Integration with simple-process/NATS

### Affected Code
This is a new service with the following structure:
- `src/worker/` - Main NATS consumer service
- `src/backfill/` - Batch processing utility
- `src/api/` - Optional FastAPI HTTP service (if needed)
- `src/ocr/` - OCR engine adapters (DeepSeek, pluggable interface)
- `src/converters/` - Format converters (PDF, office docs)
- `src/schemas/` - Pydantic models for jobs and results
- `src/clients/` - HTTP clients for simple-content API
- `tests/` - Unit and integration tests

### Dependencies
- Python packages: nats-py, transformers, vllm, torch, flash-attn, fastapi, httpx, pydantic, pdf2image, python-docx, python-pptx, openpyxl, Pillow
- System libraries: poppler-utils (for pdf2image), libjpeg, libpng
- GPU: CUDA 11.8+, drivers for A100 or similar
- Python: 3.11+ required

### Deployment Requirements
- GPU infrastructure for OCR engine (A100 with 40GB+ memory)
- NATS server for job distribution
- Storage backend (S3/MinIO or filesystem) via simple-content
- Database (PostgreSQL/MySQL/SQLite) for metadata via simple-content

### Migration Strategy
This is a net-new service with no migration needed. Existing content can be processed via the backfill utility after deployment.
