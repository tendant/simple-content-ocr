# Remote vLLM Quick Start

## TL;DR - Use Remote vLLM Server 🚀

The **recommended way** to use vision models for OCR is with a remote vLLM server.

## Why Remote vLLM?

✅ **No GPU needed on OCR service** - Run anywhere
✅ **Better scalability** - Multiple workers share one GPU server
✅ **Easier deployment** - Separate compute from inference
✅ **Works with any vLLM-supported vision model**

## Quick Setup (3 Steps)

### Step 1: Start vLLM Server (on GPU machine)

```bash
docker run --runtime nvidia --gpus all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 8000:8000 \
    --ipc=host \
    vllm/vllm-openai:latest \
    --model Qwen/Qwen2-VL-7B-Instruct \
    --trust-remote-code
```

**Verify it's running:**
```bash
curl http://localhost:8000/v1/models
```

### Step 2: Configure OCR Service

**Create/update `.env`:**

```bash
# Use remote vLLM
OCR_ENGINE=vllm

# Point to your vLLM server
VLLM_URL=http://your-vllm-server:8000

# Model name (must match what vLLM is serving)
MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct

# Optional: timeout
VLLM_TIMEOUT=120
```

### Step 3: Test It!

```bash
# Create test image
uv run python examples/create_test_image.py

# Process with remote vLLM
uv run python examples/test_local_file.py test_document.png --engine vllm
```

## Example Output

```
============================================================
🔍 Simple OCR - Local File Test
============================================================

📄 File Information:
   Path: /path/to/test_document.png
   Size: 14,851 bytes (14.5 KB)
   MIME Type: image/png
   Engine: vllm

🔧 Initializing vllm OCR engine...
🚀 Starting OCR processing...

📂 Reading local file: test_document.png
📝 Will save output to: output/test_document_ocr.md
✅ Saved markdown to: output/test_document_ocr.md

Status: completed
Pages: 1
Processing Time: 2500ms

✅ Processing complete!
```

## Production Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  # vLLM server (GPU machine)
  vllm:
    image: vllm/vllm-openai:latest
    runtime: nvidia
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    ports:
      - "8000:8000"
    command: [
      "--model", "Qwen/Qwen2-VL-7B-Instruct",
      "--trust-remote-code"
    ]

  # OCR workers (no GPU needed)
  ocr-worker:
    build: .
    environment:
      - OCR_ENGINE=vllm
      - VLLM_URL=http://vllm:8000
      - MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct
    command: python -m simple_ocr.workers.nats_worker
    deploy:
      replicas: 3
```

**Start:**
```bash
docker compose up -d
```

## Recommended Vision Models

| Model | VRAM | Quality | Speed | Command |
|-------|------|---------|-------|---------|
| **Qwen2-VL-7B** | 16GB | ⭐⭐⭐⭐⭐ | Fast | `--model Qwen/Qwen2-VL-7B-Instruct` |
| Qwen2-VL-2B | 8GB | ⭐⭐⭐⭐ | Very Fast | `--model Qwen/Qwen2-VL-2B-Instruct` |
| InternVL2-8B | 20GB | ⭐⭐⭐⭐⭐ | Fast | `--model OpenGVLab/InternVL2-8B` |
| LLaVA-v1.6-7B | 16GB | ⭐⭐⭐⭐ | Fast | `--model liuhaotian/llava-v1.6-vicuna-7b` |

## Common Scenarios

### Local Development

```bash
# Terminal 1: Start vLLM locally
docker run --runtime nvidia --gpus all -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2-VL-2B-Instruct \
  --trust-remote-code

# Terminal 2: Configure OCR
export OCR_ENGINE=vllm
export VLLM_URL=http://localhost:8000
export MODEL_NAME=Qwen/Qwen2-VL-2B-Instruct

# Terminal 2: Test
uv run python examples/test_local_file.py image.png --engine vllm
```

### Remote vLLM Server

```bash
# Configure OCR to point to remote server
export VLLM_URL=http://gpu-server.example.com:8000
export OCR_ENGINE=vllm

# Test
uv run python examples/test_local_file.py image.png --engine vllm
```

### Multiple Workers

```bash
# Start multiple OCR workers pointing to same vLLM server
for i in {1..5}; do
  docker run -d \
    -e OCR_ENGINE=vllm \
    -e VLLM_URL=http://vllm-server:8000 \
    simple-ocr-worker
done
```

## Troubleshooting

### Can't connect to vLLM

```bash
# Check vLLM is running
curl http://vllm-server:8000/health

# Check network
ping vllm-server

# Check firewall
telnet vllm-server 8000
```

### Timeout errors

```bash
# Increase timeout
export VLLM_TIMEOUT=300  # 5 minutes
```

### Wrong model error

```bash
# Make sure MODEL_NAME matches what vLLM is serving
curl http://vllm-server:8000/v1/models

# Update MODEL_NAME to match
export MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct
```

## Available Engines

The OCR service now supports 3 engines:

| Engine | Description | GPU Required | Use Case |
|--------|-------------|--------------|----------|
| `mock` | Fake OCR for testing | ❌ | Development, testing pipeline |
| `vllm` | **Remote vLLM server** | ✅ (on vLLM server) | **Production (recommended)** |
| `deepseek` | Local vLLM (not supported yet) | ✅ (local) | When vLLM adds support |

## Complete Documentation

- **Detailed Setup**: `docs/REMOTE_VLLM_SETUP.md`
- **Testing Guide**: `docs/TESTING_GUIDE.md`
- **Pipeline Docs**: `docs/PIPELINE.md`
- **OCR Engines**: `docs/OCR_ENGINES.md`

## Example Usage

### Python API

```python
from simple_ocr.adapters import OCREngineFactory

# Create remote vLLM engine
engine = OCREngineFactory.create("vllm", {
    "vllm_url": "http://vllm-server:8000",
    "model_name": "Qwen/Qwen2-VL-7B-Instruct",
    "timeout": 120
})

# Process image
with open("image.png", "rb") as f:
    result = await engine.process_image(f, "image/png")
    print(result.markdown)
```

### Command Line

```bash
# Process any image or PDF
uv run python examples/test_local_file.py document.pdf --engine vllm
```

### HTTP API

```bash
# Start API server
uv run uvicorn simple_ocr.main:app

# Submit job
curl -X POST http://localhost:8000/api/v1/ocr/process \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-123",
    "content_id": "content-456",
    "object_id": "object-789",
    "source_url": "https://example.com/document.pdf",
    "mime_type": "application/pdf"
  }'
```

## Next Steps

1. ✅ Set up vLLM server on GPU machine
2. ✅ Configure VLLM_URL in OCR service
3. ✅ Test with local files
4. ✅ Deploy workers
5. ✅ Monitor and scale

That's it! You're ready to run production OCR with remote vLLM. 🎉
