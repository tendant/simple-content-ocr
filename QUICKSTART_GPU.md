# Quick Start: GPU-Accelerated OCR

## TL;DR - Current Situation

**DeepSeek OCR is not yet supported by vLLM** ⚠️

**Workaround Options:**

1. **Use alternative vision model (Qwen2-VL)** - Recommended, works great
2. **Wait for vLLM support** - Monitor vLLM releases
3. **Use transformers directly** - Slower but works with DeepSeek

## Option 1: Use Qwen2-VL (Recommended)

### Quick Setup

```bash
# 1. Ensure you have GPU
nvidia-smi

# 2. Set environment
export OCR_ENGINE=qwen2vl
export MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct
export VLLM_GPU_MEMORY_UTILIZATION=0.9

# 3. Test
uv run python examples/test_local_file.py test_document.png --engine qwen2vl
```

### Implementation Needed

You'll need to create `src/simple_ocr/adapters/qwen2vl_engine.py` (see `docs/DEEPSEEK_SETUP.md`)

## Option 2: Use Transformers Directly (DeepSeek)

If you must use DeepSeek OCR now, bypass vLLM:

### Create Alternative DeepSeek Engine

**File: `src/simple_ocr/adapters/deepseek_transformers.py`**

```python
"""DeepSeek OCR using transformers (without vLLM)."""

import io
from typing import Any, BinaryIO

from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor
import torch

from simple_ocr.adapters.base import BaseOCREngine, OCRError, OCRResponse


class DeepSeekTransformersEngine(BaseOCREngine):
    """DeepSeek OCR using transformers library directly."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)

        self.model_name = config.get("model_name", "deepseek-ai/deepseek-vl-7b-chat")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = None
        self._processor = None

    async def _ensure_initialized(self) -> None:
        """Load model and processor."""
        if self._model is not None:
            return

        print(f"Loading {self.model_name} on {self.device}...")

        self._processor = AutoProcessor.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )

        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        ).to(self.device)

        print("Model loaded!")

    async def process_image(self, image_data: BinaryIO, mime_type: str) -> OCRResponse:
        """Process image with DeepSeek."""
        await self._ensure_initialized()

        # Load image
        image_data.seek(0)
        image = Image.open(image_data).convert("RGB")

        # Prepare prompt
        prompt = "Extract all text from this image and format as markdown:"

        # Process
        inputs = self._processor(
            text=prompt,
            images=image,
            return_tensors="pt"
        ).to(self.device)

        # Generate
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=2048,
                temperature=0.0,
            )

        # Decode
        markdown = self._processor.decode(outputs[0], skip_special_tokens=True)

        return OCRResponse(
            markdown=markdown,
            page_count=1,
            metadata={
                "engine": "deepseek-transformers",
                "model": self.model_name,
                "device": self.device,
            }
        )

    async def process_document(self, document_data: BinaryIO, mime_type: str) -> OCRResponse:
        # For PDFs, convert to images first then process
        return await self.process_image(document_data, mime_type)
```

### Use It

```bash
# Register in factory.py first, then:
export OCR_ENGINE=deepseek_transformers
uv run python examples/test_local_file.py image.png --engine deepseek_transformers
```

## Option 3: Keep Using Mock Engine

Perfect for development:

```bash
uv run python examples/test_local_file.py image.png --engine mock
```

## Comparison

| Approach | Speed | GPU Needed | Accuracy | Works Now |
|----------|-------|------------|----------|-----------|
| Mock | ⚡⚡⚡ | ❌ | N/A | ✅ |
| Qwen2-VL + vLLM | ⚡⚡ | ✅ | ⭐⭐⭐⭐⭐ | ✅ |
| DeepSeek + Transformers | ⚡ | ✅ | ⭐⭐⭐⭐ | ✅ |
| DeepSeek + vLLM | ⚡⚡⚡ | ✅ | ⭐⭐⭐⭐⭐ | ❌ (Not supported yet) |

## Recommended Path

**For Production:**
1. Start with **mock engine** for development
2. Switch to **Qwen2-VL** when ready for GPU
3. Monitor vLLM for DeepSeek OCR support

**For Testing:**
```bash
# Development (no GPU)
OCR_ENGINE=mock

# Staging (with GPU)
OCR_ENGINE=qwen2vl
MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct

# Production (when available)
OCR_ENGINE=deepseek
MODEL_NAME=deepseek-ai/deepseek-ocr
```

## Check GPU

```bash
# Check if CUDA is available
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# Check GPU
nvidia-smi
```

## Full Documentation

See `docs/DEEPSEEK_SETUP.md` for complete setup guide.
