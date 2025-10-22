# Design: OCR Processing Service

## Context

This service follows the architecture established by simple-thumbnailer, adapted for OCR processing with a Python-first approach. The key differences from thumbnailer:
- OCR requires GPU infrastructure (vs CPU-only thumbnail generation)
- Processing latency is higher (~1-5 seconds vs ~50-130ms for thumbnails)
- Output is markdown text (vs image files)
- Multiple preprocessing steps needed for different document formats
- Pure Python implementation (vs Go) for better ML ecosystem integration

The service integrates with:
- **simple-content**: Manages source files and stores OCR output as derived content (via HTTP API)
- **simple-process patterns**: Provides job structure conventions and CloudEvents format
- **vLLM**: Serves DeepSeek-OCR model with high-throughput inference
- **NATS**: Message broker for async job distribution

## Goals / Non-Goals

### Goals
- Convert documents to markdown preserving layout and structure
- Support images, PDFs, and office documents
- Automatic language detection without configuration
- Horizontal scaling via NATS queue groups
- High throughput via vLLM batching (2500+ tokens/sec)
- Graceful degradation (retries for transient failures)
- Observable via structured logging and lifecycle events
- Pure Python for ML ecosystem compatibility
- Async I/O for efficient NATS message processing

### Non-Goals
- Real-time OCR (async processing only via job queue)
- Traditional character-level OCR (focus on LLM-based understanding)
- Manual language selection (rely on model auto-detection)
- On-device processing (GPU infrastructure required)
- Multi-cloud model serving (vLLM on single cluster initially)
- Go implementation (Python-only for simplicity and ML integration)

## Decisions

### Architecture: Python-Only Service

**Decision**: Implement entire service in Python with async I/O

**Rationale**:
- DeepSeek-OCR requires Python/transformers ecosystem - native integration
- nats-py provides async NATS client with comparable performance to Go
- Simple-content HTTP API is language-agnostic (no need for Go client library)
- Single codebase simplifies deployment, debugging, and maintenance
- Python's async/await enables efficient concurrent job processing
- Unified dependency management (single requirements.txt vs multi-language)
- Better alignment with ML/AI ecosystem for future enhancements

**Alternatives considered**:
- Go + Python two-service design: Adds operational complexity, HTTP latency between services, two codebases to maintain
- Go with Python subprocess: Complex lifecycle management, hard to scale, poor error handling
- Pure Go with ONNX: DeepSeek-OCR not available in ONNX, would need model conversion, loses flexibility for other AI models

### OCR Engine: DeepSeek-OCR via vLLM

**Decision**: Use DeepSeek-OCR served via vLLM HTTP API

**Rationale**:
- Native markdown output aligns perfectly with requirements
- Layout preservation superior to traditional OCR
- Automatic language detection built-in
- vLLM provides 2500 tokens/sec throughput on A100
- Released October 2025, actively maintained

**Alternatives considered**:
- Tesseract: Good for character recognition but poor layout preservation, no markdown output
- Cloud APIs (AWS Textract, Google Vision): Vendor lock-in, cost per API call, no layout preservation
- GPT-4V/Claude: Expensive, rate limited, not specialized for OCR
- Other open models: Donut, TrOCR lack markdown output and layout understanding

### Format Handling: Preprocessing Pipeline

**Decision**: Convert all formats to images before OCR using Python libraries

**Pipeline**:
1. Images: Pillow validation → normalize format → OCR
2. PDFs: pdf2image (wraps poppler) → image per page → OCR each page → concatenate markdown
3. Office docs: python-docx/python-pptx/openpyxl → extract images + text → OCR images → merge with text

**Rationale**:
- Consistent interface to OCR engine (always receives images)
- Native Python libraries avoid subprocess complexity
- pdf2image provides async-compatible interface
- Office doc libraries (python-docx, etc.) allow rich content extraction
- Follows thumbnailer pattern adapted to Python

**Alternatives considered**:
- LibreOffice headless conversion: Requires subprocess, heavy dependency, OS-specific setup
- Native PDF text extraction: Misses scanned content, poor layout preservation
- pypdfium2 instead of pdf2image: Similar functionality, chose pdf2image for broader adoption

### Storage: Derived Content Model

**Decision**: Store OCR markdown as derived content linked to source

**Metadata schema**:
```json
{
  "derived_type": "ocr-markdown",
  "ocr_engine": "deepseek-ocr-v1",
  "source_format": "pdf|image|docx|pptx|xlsx",
  "page_count": 5,
  "processing_time_ms": 3420,
  "model_config": {
    "resolution": "640x640",
    "mode": "dynamic"
  }
}
```

**Rationale**:
- Consistent with thumbnailer pattern
- Enables versioning (re-run OCR with new models)
- Preserves lineage (source → derived relationship)
- Queryable metadata for analytics

### Simple-Content Integration: HTTP Client

**Decision**: Use httpx async HTTP client to call simple-content API

**Implementation**:
- httpx for async HTTP requests (compatible with asyncio)
- Presigned URL download/upload for content transfer
- Pydantic models for API request/response validation
- Retry logic with exponential backoff for transient failures

**Rationale**:
- No need for Go-specific client library
- HTTP API is language-agnostic and well-documented
- httpx provides async support needed for NATS event loop
- Simple, testable with httpx.AsyncClient mocking

**Alternatives considered**:
- requests library: Synchronous only, would block event loop
- aiohttp: More complex API, httpx has better ergonomics
- Direct simple-content library import: No Python client available

### Concurrency: NATS Queue Groups + Async I/O

**Decision**: Multiple async worker instances sharing queue group

**Scaling strategy**:
- Each worker runs async event loop with nats-py
- Start with 1 worker process per GPU
- Each worker can handle multiple concurrent jobs in I/O phases (download/upload)
- GPU inference is sequential bottleneck, I/O overlapped with async
- Queue group ensures each job processed once
- Workers pull jobs when ready (backpressure built-in)

**Rationale**:
- Proven pattern from thumbnailer adapted to Python
- Async I/O maximizes throughput during downloads/uploads
- Naturally handles GPU constraints (workers wait for inference capacity)
- Simple ops: scale by adding processes
- NATS handles distribution and retries
- Python asyncio provides concurrency without threading complexity

## Risks / Trade-offs

### Risk: GPU Resource Constraints
- **Impact**: Limited concurrency, potential queue buildup during traffic spikes
- **Mitigation**:
  - Monitor queue depth and processing latency
  - Implement job prioritization (tenant, urgency)
  - Document GPU scaling guidelines
  - Consider CPU fallback OCR engine for low-priority jobs

### Risk: Model Download Size
- **Impact**: 10GB+ model requires bandwidth, storage, deployment time
- **Mitigation**:
  - Pre-bake models into container images
  - Use model caching in shared volumes
  - Document cold-start times (~5-10 minutes)

### Risk: Python Dependency Management
- **Impact**: CUDA, PyTorch, transformers, vLLM versions tightly coupled
- **Mitigation**:
  - Pin exact versions in requirements.txt with hashes (pip-tools)
  - Use containerization (Docker) for reproducibility
  - Provide installation scripts and troubleshooting docs
  - Use Poetry or pip-tools for dependency resolution
  - Document Python 3.11+ requirement clearly

### Risk: Async Complexity
- **Impact**: Python async/await can be tricky, debugging harder than sync code
- **Mitigation**:
  - Use structured logging with correlation IDs
  - Comprehensive unit tests for async functions (pytest-asyncio)
  - Clear async boundaries (all I/O async, CPU work sync)
  - Leverage asyncio debugging tools (asyncio.create_task with names)

### Risk: Processing Latency
- **Impact**: OCR slower than thumbnails (1-5s vs 50-130ms)
- **Mitigation**:
  - Set realistic SLA expectations (async processing)
  - Implement timeouts (30s default, configurable)
  - Lifecycle events for progress tracking
  - Prioritize smaller documents when queue full

### Trade-off: Quality vs Speed
- **Choice**: Prioritize quality (LLM-based) over speed (traditional OCR)
- **Implication**: Slower but more accurate, better layout preservation
- **Escape hatch**: Pluggable engine interface allows CPU fallback if needed

### Trade-off: Markdown-Only Output
- **Choice**: Single output format (markdown) initially
- **Implication**: Simpler implementation, clear scope
- **Future**: Can add hOCR, JSON, searchable PDF via engine plugins

## Migration Plan

### Phase 1: Initial Deployment
1. Deploy vLLM service with DeepSeek-OCR model
2. Deploy worker service (1 instance)
3. Configure NATS subjects and queue groups
4. Validate with test documents (images, PDFs, office docs)

### Phase 2: Backfill Existing Content
1. Use backfill utility to enumerate content
2. Filter by content type (image/pdf/document MIME types)
3. Submit OCR jobs in batches (respect queue capacity)
4. Monitor progress via lifecycle events
5. Report failures for manual review

### Phase 3: Production Scaling
1. Monitor queue depth and processing latency
2. Add worker instances based on load (1 per GPU)
3. Scale vLLM horizontally if needed (GPU cluster)
4. Tune batch sizes and timeouts based on metrics

### Rollback Strategy
- Service is additive (no changes to existing systems)
- Can stop workers without data loss (jobs remain in queue)
- Re-processing safe (idempotent, derived content overwrites)
- No database migrations required (simple-content handles schema)

## Open Questions

1. **Multi-page PDF parallelization**: Process pages concurrently or sequentially?
   - Concurrent: Faster but higher GPU memory usage
   - Sequential: Slower but more stable, predictable memory
   - **Recommendation**: Sequential initially, add concurrency flag later

2. **Office doc format priority**: Which formats most critical?
   - DOCX, PPTX, XLSX likely most common
   - Need usage data to prioritize converter development
   - **Recommendation**: Implement all three via LibreOffice (consistent path)

3. **OCR confidence scores**: Should we expose model confidence?
   - DeepSeek-OCR provides token-level confidence
   - Could filter low-confidence output or flag for review
   - **Recommendation**: Store in metadata, defer UI integration

4. **Model versioning**: How to handle model updates?
   - New models may produce different output for same input
   - Need version tracking in derived content metadata
   - **Recommendation**: Include model version in derived_type (e.g., `ocr-markdown-v1.0`)

5. **Failure notifications**: How to alert on persistent failures?
   - NATS lifecycle events published but not monitored
   - Consider dead-letter queue or alerting integration
   - **Recommendation**: Document monitoring setup, defer automated alerts to Phase 2
