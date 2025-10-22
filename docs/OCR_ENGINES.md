# OCR Engines Documentation

This document describes the OCR engine architecture and available implementations.

## Overview

The OCR engine architecture provides a pluggable interface for different OCR implementations. All engines implement the `BaseOCREngine` abstract class, providing consistent APIs for image and document processing.

## Architecture

### Base Components

#### `BaseOCREngine`
Abstract base class that defines the OCR engine interface.

**Methods:**
- `process_image(image_data, mime_type)` - Process a single image
- `process_document(document_data, mime_type)` - Process a document (PDF, DOCX, etc.)
- `cleanup()` - Clean up resources
- Async context manager support (`async with`)

#### `OCRResponse`
Data model for OCR results containing:
- `markdown: str` - Extracted markdown content
- `page_count: int` - Number of pages processed
- `metadata: dict` - Additional metadata

#### `OCRError`
Exception class for OCR-related errors.

### Available Engines

## 1. Mock OCR Engine

**Purpose**: Testing and development without requiring actual OCR models.

**Configuration:**
```python
config = {
    "delay_ms": 100,      # Simulated processing delay
    "fail_rate": 0.0,     # Probability of simulated failure (0.0-1.0)
}
```

**Features:**
- Generates realistic mock markdown output
- Simulates processing delays
- Estimates page counts based on file size
- Supports failure simulation for error testing
- No GPU or external dependencies required

**Usage:**
```python
from simple_ocr.adapters import OCREngineFactory

engine = OCREngineFactory.create("mock", {
    "delay_ms": 50,
    "fail_rate": 0.0
})

result = await engine.process_image(image_data, "image/png")
print(result.markdown)
```

## 2. DeepSeek OCR Engine

**Purpose**: Production OCR using DeepSeek's vision-language model via vLLM.

**Requirements:**
- CUDA-capable GPU
- vLLM library
- Compatible DeepSeek OCR model

**Configuration:**
```python
config = {
    "model_name": "deepseek-ai/deepseek-ocr",
    "gpu_memory_utilization": 0.9,
    "max_model_len": 4096,
    "tensor_parallel_size": 1,
    "temperature": 0.0,
    "max_tokens": 2048,
}
```

**Features:**
- High-quality OCR using AI models
- GPU-accelerated inference with vLLM
- Multi-page document support
- Automatic PDF to image conversion
- Preserves document structure in markdown

**Usage:**
```python
from simple_ocr.adapters import OCREngineFactory

engine = OCREngineFactory.create("deepseek", {
    "model_name": "deepseek-ai/deepseek-ocr",
    "gpu_memory_utilization": 0.8
})

result = await engine.process_document(pdf_data, "application/pdf")
print(f"Processed {result.page_count} pages")
```

**Note**: Requires a vLLM-compatible DeepSeek OCR model. The default model may need to be updated based on vLLM's supported architectures.

## OCR Engine Factory

The factory pattern simplifies engine creation and management.

### Creating Engines

**Direct creation:**
```python
from simple_ocr.adapters import OCREngineFactory

# Create with explicit config
engine = OCREngineFactory.create("mock", {"delay_ms": 0})
```

**From settings:**
```python
from simple_ocr.adapters import OCREngineFactory
from simple_ocr.config import get_settings

settings = get_settings()
engine = OCREngineFactory.create_from_settings(settings)
```

**List available engines:**
```python
engines = OCREngineFactory.list_engines()
# Returns: ["mock", "deepseek"]
```

### Registering Custom Engines

You can extend the system with custom OCR engines:

```python
from simple_ocr.adapters import BaseOCREngine, OCREngineFactory, OCRResponse

class MyCustomEngine(BaseOCREngine):
    async def process_image(self, image_data, mime_type):
        # Your OCR logic here
        return OCRResponse(
            markdown="# Extracted Text",
            page_count=1,
            metadata={"engine": "custom"}
        )

    async def process_document(self, document_data, mime_type):
        return await self.process_image(document_data, mime_type)

# Register the custom engine
OCREngineFactory.register_engine("custom", MyCustomEngine)

# Use it
engine = OCREngineFactory.create("custom", {})
```

## Configuration via Environment Variables

Configure OCR engines through environment variables:

```bash
# Engine selection
OCR_ENGINE=mock  # or "deepseek"

# DeepSeek-specific settings
MODEL_NAME=deepseek-ai/deepseek-ocr
MODEL_PATH=/models/deepseek-ocr
VLLM_GPU_MEMORY_UTILIZATION=0.9
VLLM_MAX_MODEL_LEN=4096
VLLM_TENSOR_PARALLEL_SIZE=1
```

## Best Practices

### 1. Use Context Managers

Always use async context managers for proper resource cleanup:

```python
async with OCREngineFactory.create("mock", {}) as engine:
    result = await engine.process_image(image_data, "image/png")
    # Engine resources are automatically cleaned up
```

### 2. Error Handling

Handle OCR errors gracefully:

```python
from simple_ocr.adapters import OCRError

try:
    result = await engine.process_image(image_data, "image/png")
except OCRError as e:
    print(f"OCR failed: {e}")
    if e.original_error:
        print(f"Original error: {e.original_error}")
```

### 3. Testing

Use the mock engine for testing:

```python
@pytest.fixture
def ocr_engine():
    return OCREngineFactory.create("mock", {
        "delay_ms": 0,  # No delay for tests
        "fail_rate": 0.0
    })

async def test_my_feature(ocr_engine):
    result = await ocr_engine.process_image(test_image, "image/png")
    assert result.page_count == 1
```

### 4. Production Deployment

For production:
- Use DeepSeek engine with GPU acceleration
- Configure appropriate GPU memory allocation
- Monitor processing times and errors
- Implement retry logic for transient failures
- Use NATS for distributed processing

## Supported Formats

### Images
- JPEG (.jpg, .jpeg)
- PNG (.png)
- TIFF (.tiff, .tif)
- BMP (.bmp)
- WebP (.webp)

### Documents
- PDF (.pdf) - Full support with page-by-page processing
- DOCX (.docx) - Planned
- PPTX (.pptx) - Planned
- XLSX (.xlsx) - Planned

## Performance Considerations

### Mock Engine
- Very fast (configurable delay)
- No resource constraints
- Ideal for development and testing

### DeepSeek Engine
- GPU memory: Depends on model size and batch size
- Processing time: ~1-5 seconds per page (varies by GPU)
- Throughput: Use vLLM batching for higher throughput
- Memory: Configure `gpu_memory_utilization` based on available VRAM

## Troubleshooting

### DeepSeek Engine Issues

**Model not supported by vLLM:**
- Check vLLM's supported architectures
- Verify model compatibility
- Consider using a different vision-language model

**GPU memory errors:**
- Reduce `gpu_memory_utilization`
- Decrease `max_model_len`
- Use smaller images (resize before processing)

**Slow processing:**
- Increase `gpu_memory_utilization` if VRAM available
- Use tensor parallelism (`tensor_parallel_size > 1`)
- Enable vLLM batching for multiple documents

## Future Enhancements

Planned improvements:
- Additional OCR engines (Tesseract, PaddleOCR, etc.)
- Batch processing support
- Table extraction and formatting
- Form field detection
- Handwriting recognition
- Multi-language support enhancements
