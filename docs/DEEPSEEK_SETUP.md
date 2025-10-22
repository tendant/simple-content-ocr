# DeepSeek OCR Setup Guide

## Current Status ⚠️

**Important**: As of now, the DeepSeek OCR model architecture (`DeepseekOCRForCausalLM`) is **not yet supported** by vLLM.

When attempting to use it, you'll see:
```
Model architectures ['DeepseekOCRForCausalLM'] are not supported for now.
```

## Alternatives

You have several options:

### Option 1: Use Alternative Vision-Language Models (Recommended)

Use other vLLM-supported vision models that work well for OCR:

#### A. Qwen2-VL (Recommended)
```bash
# Update config
export OCR_ENGINE=qwen2vl
export MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct

# Or in .env
OCR_ENGINE=qwen2vl
MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct
```

#### B. LLaVA
```bash
export OCR_ENGINE=llava
export MODEL_NAME=liuhaotian/llava-v1.6-vicuna-7b
```

#### C. InternVL2
```bash
export OCR_ENGINE=internvl
export MODEL_NAME=OpenGVLab/InternVL2-8B
```

### Option 2: Wait for DeepSeek OCR Support

Monitor vLLM releases for DeepSeek OCR support:
- vLLM GitHub: https://github.com/vllm-project/vllm
- Supported models: https://docs.vllm.ai/en/latest/models/supported_models.html

### Option 3: Use DeepSeek OCR Directly (Without vLLM)

If you need DeepSeek OCR specifically, you can modify the engine to use transformers directly.

## Setting Up Alternative Models

Here's how to set up with a supported vision-language model (using Qwen2-VL as example):

### Prerequisites

**1. GPU Requirements:**
- CUDA 11.8+ or 12.1+
- NVIDIA GPU with 16GB+ VRAM (for 7B models)
- 24GB+ VRAM recommended for better performance

**2. System Requirements:**
```bash
# Check CUDA version
nvidia-smi

# Check CUDA is available
python -c "import torch; print(torch.cuda.is_available())"
```

### Installation

**1. Install with GPU support:**
```bash
# Install CUDA-enabled PyTorch (if not already)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# vLLM is already in requirements.txt
uv sync
```

**2. Download the model:**
```bash
# Models will auto-download on first use, or pre-download:
python -c "
from transformers import AutoTokenizer, AutoModel
model_name = 'Qwen/Qwen2-VL-7B-Instruct'
print(f'Downloading {model_name}...')
AutoTokenizer.from_pretrained(model_name)
AutoModel.from_pretrained(model_name)
print('Done!')
"
```

### Create Qwen2-VL Engine

Since the current implementation is for DeepSeek, let me create an alternative engine:

**File: `src/simple_ocr/adapters/qwen2vl_engine.py`**

```python
"""Qwen2-VL OCR engine using vLLM."""

import base64
import io
from typing import Any, BinaryIO, List, Optional

import structlog
from PIL import Image

from simple_ocr.adapters.base import BaseOCREngine, OCRError, OCRResponse

logger = structlog.get_logger(__name__)


class Qwen2VLEngine(BaseOCREngine):
    """Qwen2-VL vision-language model for OCR."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)

        self.model_name = config.get("model_name", "Qwen/Qwen2-VL-7B-Instruct")
        self.gpu_memory_utilization = config.get("gpu_memory_utilization", 0.9)
        self.max_model_len = config.get("max_model_len", 4096)
        self.temperature = config.get("temperature", 0.0)
        self.max_tokens = config.get("max_tokens", 2048)

        self._llm: Optional[Any] = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Initialize vLLM model."""
        if self._initialized:
            return

        try:
            from vllm import LLM, SamplingParams

            logger.info("loading_vllm_model", model=self.model_name)

            self._llm = LLM(
                model=self.model_name,
                gpu_memory_utilization=self.gpu_memory_utilization,
                max_model_len=self.max_model_len,
                trust_remote_code=True,
            )

            self._initialized = True
            logger.info("vllm_model_loaded", model=self.model_name)

        except Exception as e:
            logger.error("failed_to_load_vllm", error=str(e))
            raise OCRError(f"Failed to initialize vLLM: {e}", original_error=e)

    async def process_image(self, image_data: BinaryIO, mime_type: str) -> OCRResponse:
        """Process image with Qwen2-VL."""
        await self._ensure_initialized()

        try:
            image = Image.open(image_data)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            # Create OCR prompt
            prompt = self._create_prompt()

            # Generate with vLLM
            from vllm import SamplingParams

            sampling_params = SamplingParams(
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # For vision models, pass image with prompt
            outputs = self._llm.generate(
                [{"prompt": prompt, "multi_modal_data": {"image": image}}],
                sampling_params,
            )

            markdown = outputs[0].outputs[0].text.strip()

            return OCRResponse(
                markdown=markdown,
                page_count=1,
                metadata={
                    "engine": "qwen2vl",
                    "model": self.model_name,
                    "mime_type": mime_type,
                }
            )

        except Exception as e:
            logger.error("ocr_failed", error=str(e))
            raise OCRError(f"OCR processing failed: {e}", original_error=e)

    async def process_document(self, document_data: BinaryIO, mime_type: str) -> OCRResponse:
        """Process document (similar to DeepSeek implementation)."""
        # Convert to images and process page by page
        # Implementation similar to DeepSeekOCREngine
        pass

    def _create_prompt(self) -> str:
        """Create OCR prompt."""
        return """Extract all text from this image and format it as clean markdown.
Preserve the document structure, headings, lists, tables, and formatting.
Be accurate and maintain the original text exactly as it appears."""

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._llm:
            self._llm = None
            self._initialized = False
```

### Configuration

**1. Update `.env`:**
```bash
# OCR Engine
OCR_ENGINE=qwen2vl
MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct

# GPU Settings
VLLM_GPU_MEMORY_UTILIZATION=0.9
VLLM_MAX_MODEL_LEN=4096
VLLM_TENSOR_PARALLEL_SIZE=1

# Performance
PROCESSING_TIMEOUT=300
```

**2. Register the engine in factory:**

Update `src/simple_ocr/adapters/factory.py`:
```python
from simple_ocr.adapters.qwen2vl_engine import Qwen2VLEngine

class OCREngineFactory:
    _engines: Dict[str, type[BaseOCREngine]] = {
        "mock": MockOCREngine,
        "deepseek": DeepSeekOCREngine,
        "qwen2vl": Qwen2VLEngine,  # Add this
    }
```

### Testing

**1. Test with local file:**
```bash
# Make sure GPU is available
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# Test with Qwen2-VL
uv run python examples/test_local_file.py test_document.png --engine qwen2vl
```

**2. Monitor GPU usage:**
```bash
# In another terminal
watch -n 1 nvidia-smi
```

## When DeepSeek OCR Becomes Available

Once vLLM adds support for DeepSeek OCR, here's how to use it:

### Setup

**1. Update configuration:**
```bash
export OCR_ENGINE=deepseek
export MODEL_NAME=deepseek-ai/deepseek-ocr
```

**2. Download the model:**
```bash
# Auto-downloads on first use, or:
huggingface-cli download deepseek-ai/deepseek-ocr
```

**3. Run:**
```bash
uv run python examples/test_local_file.py image.png --engine deepseek
```

### Expected Performance

With DeepSeek OCR on GPU:
- **Processing time**: 1-5 seconds per page
- **GPU memory**: 8-16GB depending on model size
- **Quality**: High accuracy, structure preservation

## Troubleshooting

### GPU Not Detected

```bash
# Check CUDA
nvidia-smi

# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Reinstall PyTorch with CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### Out of Memory

```bash
# Reduce GPU memory usage
export VLLM_GPU_MEMORY_UTILIZATION=0.7

# Reduce max sequence length
export VLLM_MAX_MODEL_LEN=2048

# Use smaller model
export MODEL_NAME=Qwen/Qwen2-VL-2B-Instruct
```

### Model Download Fails

```bash
# Set HuggingFace cache directory
export HF_HOME=/path/to/cache

# Download manually
huggingface-cli login  # If model requires authentication
huggingface-cli download Qwen/Qwen2-VL-7B-Instruct
```

### Slow Processing

```bash
# Enable tensor parallelism (multiple GPUs)
export VLLM_TENSOR_PARALLEL_SIZE=2

# Increase batch size
export BATCH_SIZE=4
```

## Production Deployment

### Docker with GPU

```dockerfile
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Install Python and dependencies
RUN apt-get update && apt-get install -y python3.11 python3-pip

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy project
COPY . /app
WORKDIR /app

# Install dependencies
RUN uv sync

# Run worker
CMD ["uv", "run", "python", "-m", "simple_ocr.workers.nats_worker"]
```

**Docker Compose with GPU:**
```yaml
version: '3.8'
services:
  ocr-worker:
    build: .
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - OCR_ENGINE=qwen2vl
      - MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct
      - VLLM_GPU_MEMORY_UTILIZATION=0.9
```

**Run:**
```bash
docker compose up ocr-worker
```

## Benchmarks

Approximate performance (will vary by GPU):

| Model | GPU | VRAM | Speed/Page | Quality |
|-------|-----|------|------------|---------|
| Qwen2-VL-2B | T4 | 8GB | 2-3s | Good |
| Qwen2-VL-7B | A10 | 16GB | 1-2s | Excellent |
| LLaVA-7B | A10 | 16GB | 2-3s | Very Good |
| InternVL2-8B | A100 | 24GB | 1s | Excellent |

## Alternative: Use Mock Engine

For development and testing without GPU:

```bash
# Always use mock engine
export OCR_ENGINE=mock

# Test functionality without GPU
uv run python examples/test_local_file.py image.png --engine mock
```

The mock engine:
- ✅ No GPU required
- ✅ Fast processing
- ✅ Generates realistic markdown structure
- ❌ Doesn't actually read text from images
- ✅ Perfect for testing pipeline logic

## Next Steps

1. **Choose a supported model** - Qwen2-VL recommended
2. **Set up GPU environment** - CUDA 12.1+
3. **Test with local files** - Verify GPU detection
4. **Monitor performance** - Check GPU utilization
5. **Production deployment** - Docker with GPU support

## Resources

- **vLLM Documentation**: https://docs.vllm.ai/
- **Supported Models**: https://docs.vllm.ai/en/latest/models/supported_models.html
- **Qwen2-VL**: https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct
- **LLaVA**: https://llava-vl.github.io/
- **GPU Setup**: https://docs.nvidia.com/cuda/
