# OCR Processing Pipeline

## Overview

The OCR processing pipeline orchestrates the complete workflow of converting documents (images, PDFs, office documents) to markdown format using AI-powered OCR models.

## Architecture

```
┌─────────────┐        ┌──────────────┐       ┌───────────────┐
│  HTTP API   │        │ NATS Worker  │       │  OCR Service  │
│  (FastAPI)  │───────>│ (Async Jobs) │──────>│  (Pipeline)   │
└─────────────┘        └──────────────┘       └───────────────┘
                                                       │
                            ┌──────────────────────────┼──────────────────────────┐
                            │                          │                          │
                       ┌────▼────┐              ┌─────▼─────┐           ┌────────▼────────┐
                       │   OCR   │              │  Content  │           │   Temp File     │
                       │ Engine  │              │  Client   │           │   Management    │
                       └─────────┘              └───────────┘           └─────────────────┘
```

## Components

### 1. OCR Service (`src/simple_ocr/services/ocr_service.py`)

The main pipeline orchestrator that coordinates all processing steps.

**Responsibilities:**
- Downloads source content from presigned URLs
- Determines processing method (image vs document)
- Invokes OCR engine for text extraction
- Creates derived content records
- Uploads markdown results
- Handles errors and cleanup

**Pipeline Steps:**

```python
async def process_job(job: OCRJob) -> OCRResult:
    1. Download source content from presigned URL
    2. Determine content type (image vs document)
    3. Process with OCR engine
    4. Create derived content record
    5. Upload markdown result
    6. Return processing result
```

### 2. Content Client (`src/simple_ocr/adapters/content_client.py`)

HTTP client for interacting with the simple-content API.

**Features:**
- Download content via presigned URLs
- Create derived content records
- Upload processed markdown
- Get content metadata

**Example Usage:**

```python
client = SimpleContentClient(
    base_url="http://localhost:8080",
    timeout=30,
    max_retries=3
)

# Download source
content = await client.download_content(presigned_url)

# Create derived record
derived = await client.create_derived_content(request)

# Upload result
await client.upload_derived_content(
    upload_url, markdown_bytes, "text/markdown"
)
```

### 3. NATS Worker (`src/simple_ocr/workers/nats_worker.py`)

Asynchronous worker for processing OCR jobs from NATS JetStream.

**Features:**
- Connects to NATS server
- Sets up JetStream stream and consumer
- Processes jobs concurrently
- Publishes results as CloudEvents
- Handles graceful shutdown

**Example Usage:**

```bash
# Run the worker
python -m simple_ocr.workers.nats_worker

# Or via uv
uv run python -m simple_ocr.workers.nats_worker
```

**Configuration:**

```bash
NATS_URL=nats://localhost:4222
NATS_SUBJECT=ocr.jobs
NATS_STREAM=OCR_JOBS
NATS_CONSUMER=ocr-worker
NATS_MAX_CONCURRENT=5
```

### 4. FastAPI Routes (`src/simple_ocr/routes/ocr.py`)

HTTP API endpoints for synchronous OCR processing.

**Endpoints:**

- `GET /api/v1/ocr/health` - Health check
- `GET /api/v1/ocr/engines` - List available OCR engines
- `POST /api/v1/ocr/process` - Process document synchronously

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/ocr/process \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-123",
    "content_id": "content-456",
    "object_id": "object-789",
    "source_url": "https://example.com/document.pdf",
    "mime_type": "application/pdf"
  }'
```

## Processing Flow

### 1. Job Submission

**Via HTTP API (Synchronous):**
```
Client → POST /api/v1/ocr/process → OCR Service → Response
```

**Via NATS (Asynchronous):**
```
Publisher → NATS JetStream → Worker → OCR Service → Result Event
```

### 2. Content Download

```python
# Download from presigned URL
content_data = await content_client.download_content(job.source_url)
```

**Supported Formats:**
- Images: JPEG, PNG, TIFF, BMP, WebP
- Documents: PDF, DOCX (planned), PPTX (planned), XLSX (planned)

### 3. OCR Processing

**For Images:**
```python
ocr_response = await ocr_engine.process_image(
    content_data, mime_type
)
```

**For Documents:**
```python
ocr_response = await ocr_engine.process_document(
    content_data, mime_type
)
```

The engine automatically:
- Converts PDFs to images (page by page)
- Processes each page with OCR
- Combines results into single markdown document

### 4. Result Storage

**Create Derived Content:**
```python
derived_request = DerivedContentRequest(
    content_id=job.content_id,
    object_id=job.object_id,
    derived_type="ocr_markdown",
    mime_type="text/markdown",
    metadata={
        "job_id": job.job_id,
        "page_count": str(page_count),
        ...
    }
)

derived_response = await content_client.create_derived_content(
    derived_request
)
```

**Upload Markdown:**
```python
markdown_bytes = markdown_text.encode("utf-8")
await content_client.upload_derived_content(
    derived_response.upload_url,
    markdown_bytes,
    "text/markdown"
)
```

### 5. Result Publishing

**OCR Result Model:**
```python
OCRResult(
    job_id="job-123",
    status=OCRJobStatus.COMPLETED,
    markdown_content="# Document Title\n\n...",
    processing_time_ms=1500,
    page_count=3,
    metadata={
        "derived_id": "derived-456",
        "content_id": "content-123",
        "engine": "mock",
        ...
    }
)
```

## Error Handling

The pipeline handles errors at multiple levels:

### 1. Download Errors
```python
try:
    content = await content_client.download_content(url)
except Exception as e:
    return OCRResult(
        status=OCRJobStatus.FAILED,
        error_message=f"Download failed: {e}"
    )
```

### 2. OCR Errors
```python
try:
    result = await ocr_engine.process_image(data, mime_type)
except OCRError as e:
    return OCRResult(
        status=OCRJobStatus.FAILED,
        error_message=f"OCR failed: {e}"
    )
```

### 3. Upload Errors
```python
try:
    await content_client.upload_derived_content(...)
except Exception as e:
    return OCRResult(
        status=OCRJobStatus.FAILED,
        error_message=f"Upload failed: {e}"
    )
```

### 4. NATS Worker Error Handling

```python
try:
    result = await ocr_service.process_job(job)
    await msg.ack()  # Success
except Exception as e:
    await msg.nak()  # Redelivery
    logger.error("processing_failed", error=e)
```

## Performance Optimization

### 1. Concurrent Processing

**NATS Worker:**
```python
# Process multiple jobs concurrently
msgs = await psub.fetch(batch=5, timeout=5.0)
tasks = [process_message(msg) for msg in msgs]
await asyncio.gather(*tasks)
```

### 2. Resource Management

**Cleanup:**
```python
async with OCRService(...) as service:
    result = await service.process_job(job)
    # Automatic cleanup
```

**Temp File Management:**
```python
OCRService(
    cleanup_temp_files=True,  # Auto-delete temp files
    temp_dir="/tmp/simple-ocr"
)
```

### 3. Timeouts and Retries

```python
# Content client with retries
SimpleContentClient(
    timeout=30,
    max_retries=3
)

# NATS acknowledgment timeout
NATS_ACK_WAIT=300  # 5 minutes
```

## Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  nats:
    image: nats:latest
    ports:
      - "4222:4222"

  ocr-worker:
    build: .
    command: python -m simple_ocr.workers.nats_worker
    environment:
      - OCR_ENGINE=mock
      - NATS_URL=nats://nats:4222
      - CONTENT_API_URL=http://simple-content:8080

  ocr-api:
    build: .
    command: uvicorn simple_ocr.main:app --host 0.0.0.0
    ports:
      - "8000:8000"
```

### Environment Variables

```bash
# Application
APP_NAME=simple-ocr
LOG_LEVEL=INFO
ENVIRONMENT=production

# OCR Engine
OCR_ENGINE=mock  # or deepseek
MODEL_NAME=deepseek-ai/deepseek-ocr

# NATS
NATS_URL=nats://localhost:4222
NATS_SUBJECT=ocr.jobs
NATS_MAX_CONCURRENT=5

# Content API
CONTENT_API_URL=http://localhost:8080
CONTENT_API_TIMEOUT=30

# Performance
PROCESSING_TIMEOUT=300
TEMP_DIR=/tmp/simple-ocr
CLEANUP_TEMP_FILES=true
```

## Monitoring and Logging

All components use structured logging with contextual information:

```json
{
  "timestamp": "2025-10-22T23:25:18.123Z",
  "level": "info",
  "event": "processing_ocr_job",
  "job_id": "job-123",
  "content_id": "content-456",
  "mime_type": "application/pdf"
}
```

**Key Metrics:**
- `processing_time_ms` - Time to process each job
- `page_count` - Number of pages processed
- `error_rate` - Failed jobs / total jobs
- `queue_depth` - NATS pending messages

## Testing

### Unit Tests
```bash
uv run pytest tests/unit/ -v
```

### Integration Tests
```bash
uv run pytest tests/integration/ -v
```

### Full Test Suite
```bash
uv run pytest tests/ -v --cov=simple_ocr
```

**Test Coverage:**
- OCR Adapters: 87-100%
- Pipeline Service: 88%
- Overall: 47% (routes/workers not covered in unit tests)

## Future Enhancements

1. **Batch Processing** - Process multiple documents in single job
2. **Retry Logic** - Automatic retry with exponential backoff
3. **Priority Queues** - Different queues for different priority levels
4. **Streaming Results** - Stream partial results for large documents
5. **Caching** - Cache OCR results for identical documents
6. **Metrics API** - Prometheus metrics endpoint
7. **Health Checks** - Detailed health checks for all dependencies

## Troubleshooting

### Common Issues

**1. NATS Connection Failed**
```bash
# Check NATS is running
docker ps | grep nats

# Test connection
nats-cli server check
```

**2. Content Download Failed**
```
# Verify presigned URL is valid and not expired
curl -I <presigned_url>
```

**3. OCR Processing Slow**
```
# Check GPU utilization
nvidia-smi

# Adjust GPU memory
VLLM_GPU_MEMORY_UTILIZATION=0.8
```

**4. Worker Not Processing Jobs**
```bash
# Check worker logs
docker logs ocr-worker

# Check NATS stream
nats stream info OCR_JOBS
```

## References

- [OCR Engines Documentation](OCR_ENGINES.md)
- [Configuration Guide](../README.md#configuration)
- [API Documentation](http://localhost:8000/docs)
