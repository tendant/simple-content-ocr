# PaddleOCR-VL Setup Guide

## ⚠️ CRITICAL: vLLM Incompatibility

**PaddleOCR-VL is NOT compatible with vLLM.** You will encounter this error:

```
ValueError: There is no module or parameter named 'mlp_AR' in TransformersForCausalLM
```

**Solution:** Use the **Custom PaddleOCR Server** (see Method 1 below) which uses regular HuggingFace `transformers` with `trust_remote_code=True`.

---

## Why PaddleOCR-VL?

PaddleOCR-VL is **the best model for OCR tasks** in this project:

- ✅ **Ultra-lightweight**: Only 0.9B parameters (vs 7B for Qwen2-VL)
- ✅ **Purpose-built for OCR**: Specifically designed for document parsing
- ✅ **109 languages**: Multilingual support out of the box
- ✅ **Complex elements**: Recognizes text, tables, formulas, and charts
- ✅ **SOTA accuracy**: State-of-the-art performance for document parsing
- ✅ **vLLM compatible**: Fast inference with OpenAI-compatible API
- ✅ **Low VRAM**: Runs on GPUs with 4-8GB VRAM

**Model**: `PaddlePaddle/PaddleOCR-VL`

## Quick Start

### Method 1: Custom PaddleOCR Server (RECOMMENDED - Only Option)

**❌ vLLM DOES NOT WORK with PaddleOCR-VL** - Use this custom server instead:

The custom server is a Python-based alternative that:
- ✅ **Actually works** with PaddleOCR-VL (uses HuggingFace transformers)
- ✅ Works with ALL GPUs (no FlashAttention required)
- ✅ OpenAI-compatible API (drop-in replacement)
- ✅ Easier to debug and troubleshoot
- ✅ Lower memory footprint (~1.8GB VRAM)

**Quick start with custom server:**

```bash
# Install dependencies (one-time setup)
uv venv --python 3.12 --seed
uv sync

# Start server (port 8000 by default)
uv run python scripts/run_paddleocr_server.py --host 0.0.0.0 --port 8000
```

**Verify server is running:**

```bash
# Test health
curl http://localhost:8000/health

# Test models API
curl http://localhost:8000/v1/models

# Check GPU usage
nvidia-smi
```

Expected output:
```json
{"status":"healthy","model_loaded":true,"device":"cuda","memory_used_mb":1839.5}
```

See `CUSTOM_SERVER_SETUP.md` for complete documentation.

**Configure OCR service:**

```bash
# In .env or export
export OCR_ENGINE=vllm  # Custom server uses OpenAI-compatible API
export VLLM_URL=http://localhost:8000
export MODEL_NAME=PaddlePaddle/PaddleOCR-VL

# Test it
uv run python examples/test_local_file.py test_document.png --engine vllm
```

**Note:** Even though we're using the custom server (not actual vLLM), we set `OCR_ENGINE=vllm` because the custom server provides an OpenAI-compatible API identical to vLLM's interface.

---

### ~~Method 2: vLLM Server~~ (DOES NOT WORK)

**❌ THIS METHOD DOES NOT WORK** - PaddleOCR-VL is incompatible with vLLM.

You will get this error:
```
ValueError: There is no module or parameter named 'mlp_AR' in TransformersForCausalLM
```

~~The commands below are kept for reference only - they will NOT work:~~

<details>
<summary>❌ Non-working vLLM commands (for reference only)</summary>

```bash
# These vLLM commands DO NOT WORK - they're here for reference only
# DO NOT RUN THESE - use the custom server above instead
```

</details>

### ~~Method 3: PaddlePaddle Official Docker Image~~ (Unknown Status)

PaddlePaddle provides a pre-built Docker image with vLLM server:

```bash
# Start PaddlePaddle's vLLM server (port 8080)
podman run -d \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -p 8080:8080 \
    --name paddleocr-vl-server \
    ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddlex-genai-vllm-server

# Or with Docker
docker run -d \
    --gpus all \
    -p 8080:8080 \
    --name paddleocr-vl-server \
    ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddlex-genai-vllm-server
```

**Configure OCR service (note different port):**

```bash
export OCR_ENGINE=vllm
export VLLM_URL=http://localhost:8080
export MODEL_NAME=PaddlePaddle/PaddleOCR-VL
```

## Production Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  paddleocr-vl:
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
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    command:
      - --model
      - PaddlePaddle/PaddleOCR-VL
      - --host
      - 0.0.0.0
      - --port
      - "8000"
      - --trust-remote-code
      - --max-model-len
      - "4096"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  ocr-worker:
    build: .
    depends_on:
      - paddleocr-vl
    environment:
      - OCR_ENGINE=vllm
      - VLLM_URL=http://paddleocr-vl:8000
      - MODEL_NAME=PaddlePaddle/PaddleOCR-VL
    command: python -m simple_ocr.workers.nats_worker
    deploy:
      replicas: 3
```

**Start:**

```bash
docker compose up -d
```

### Podman Compose

```yaml
version: '3.8'

services:
  paddleocr-vl:
    image: docker.io/vllm/vllm-openai:latest
    devices:
      - nvidia.com/gpu=all
    security_opt:
      - label=disable
    ports:
      - "8000:8000"
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface:Z
    command:
      - --model
      - PaddlePaddle/PaddleOCR-VL
      - --host
      - 0.0.0.0
      - --port
      - "8000"
      - --trust-remote-code
      - --max-model-len
      - "4096"

  ocr-worker:
    build: .
    depends_on:
      - paddleocr-vl
    environment:
      - OCR_ENGINE=vllm
      - VLLM_URL=http://paddleocr-vl:8000
      - MODEL_NAME=PaddlePaddle/PaddleOCR-VL
    command: python -m simple_ocr.workers.nats_worker
```

**Start:**

```bash
podman-compose up -d
```

## Model Configuration

### GPU Memory Requirements

| GPU VRAM | Max Batch Size | Recommended Settings |
|----------|----------------|---------------------|
| 4-6GB    | 1-2            | `--gpu-memory-utilization 0.9` |
| 8GB      | 2-4            | Default settings |
| 12GB+    | 4-8            | `--max-num-seqs 8` |

### Performance Tuning

**Optimize for latency:**

```bash
podman run -d \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    --name paddleocr-vl \
    docker.io/vllm/vllm-openai:latest \
    --model PaddlePaddle/PaddleOCR-VL \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.9
```

**Optimize for throughput:**

```bash
podman run -d \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    --name paddleocr-vl \
    docker.io/vllm/vllm-openai:latest \
    --model PaddlePaddle/PaddleOCR-VL \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code \
    --max-model-len 4096 \
    --max-num-seqs 8 \
    --gpu-memory-utilization 0.95
```

## Multi-GPU Setup

For multi-GPU systems:

```bash
podman run -d \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    --name paddleocr-vl \
    docker.io/vllm/vllm-openai:latest \
    --model PaddlePaddle/PaddleOCR-VL \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code \
    --tensor-parallel-size 2  # Use 2 GPUs
```

## Usage Examples

### Python API

```python
from simple_ocr.adapters import OCREngineFactory

# Create vLLM engine with PaddleOCR-VL
engine = OCREngineFactory.create("vllm", {
    "vllm_url": "http://localhost:8000",
    "model_name": "PaddlePaddle/PaddleOCR-VL",
    "timeout": 120
})

# Process image
with open("document.png", "rb") as f:
    result = await engine.process_image(f, "image/png")
    print(result.markdown)
```

### Command Line

```bash
# Process single image
uv run python examples/test_local_file.py invoice.png --engine vllm

# Process PDF
uv run python examples/test_local_file.py document.pdf --engine vllm

# Process with custom output
uv run python examples/test_local_file.py scan.jpg --engine vllm --output custom_output.md
```

### HTTP API

```bash
# Start API server
uv run uvicorn simple_ocr.main:app --host 0.0.0.0 --port 8080

# Submit OCR job
curl -X POST http://localhost:8080/api/v1/ocr/process \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "ocr-001",
    "content_id": "doc-123",
    "object_id": "obj-456",
    "source_url": "https://example.com/invoice.pdf",
    "mime_type": "application/pdf"
  }'
```

## Troubleshooting

### Error: "forward compatibility was attempted on non supported HW" or "compute capability 6.1 doesn't support FlashAttention"

**Cause**: Your GPU is older (compute capability < 8.0) and doesn't support FlashAttention.

**Solution**: Use the xformers backend (see "For Older GPUs" section above):

```bash
# Add these to your podman/docker run command:
-e VLLM_ATTENTION_BACKEND=XFORMERS \
--dtype float16 \
--max-model-len 4096
```

### Model download is slow

```bash
# Pre-download model
podman run --rm \
    --device nvidia.com/gpu=all \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    docker.io/vllm/vllm-openai:latest \
    python -c "from huggingface_hub import snapshot_download; snapshot_download('PaddlePaddle/PaddleOCR-VL')"
```

### Out of memory errors

```bash
# Reduce GPU memory utilization
podman run -d \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    docker.io/vllm/vllm-openai:latest \
    --model PaddlePaddle/PaddleOCR-VL \
    --trust-remote-code \
    --gpu-memory-utilization 0.7 \
    --max-model-len 2048
```

### Container won't start

```bash
# Check logs
podman logs paddleocr-vl

# Run interactively to debug
podman run -it --rm \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    docker.io/vllm/vllm-openai:latest \
    /bin/bash

# Inside container, test manually
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

### API connection errors

```bash
# Check if server is running
podman ps

# Test network connectivity
curl http://localhost:8000/health

# Check API endpoint
curl http://localhost:8000/v1/models

# View real-time logs
podman logs -f paddleocr-vl
```

## Model Comparison

| Model | Parameters | VRAM | Speed | OCR Quality | Best For |
|-------|-----------|------|-------|-------------|----------|
| **PaddleOCR-VL** | 0.9B | 4-8GB | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | **OCR, documents, production** |
| Qwen2-VL-2B | 2B | 8GB | ⚡⚡ | ⭐⭐⭐⭐⭐ | General vision tasks |
| Qwen2-VL-7B | 7B | 16GB | ⚡ | ⭐⭐⭐⭐⭐ | High accuracy needs |
| InternVL2-8B | 8B | 20GB | ⚡ | ⭐⭐⭐⭐⭐ | Research, complex docs |

**Recommendation**: Use PaddleOCR-VL for this OCR service - it's optimized for the task!

## Systemd Service

Create `/etc/systemd/system/paddleocr-vl.service`:

```ini
[Unit]
Description=PaddleOCR-VL vLLM Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=10

ExecStartPre=/usr/bin/podman rm -f paddleocr-vl
ExecStart=/usr/bin/podman run \
    --rm \
    --name paddleocr-vl \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -v /home/user/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    docker.io/vllm/vllm-openai:latest \
    --model PaddlePaddle/PaddleOCR-VL \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code

ExecStop=/usr/bin/podman stop paddleocr-vl

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable paddleocr-vl
sudo systemctl start paddleocr-vl

# Check status
sudo systemctl status paddleocr-vl

# View logs
sudo journalctl -u paddleocr-vl -f
```

## Next Steps

1. ✅ Install NVIDIA Container Toolkit (see `INSTALL_NVIDIA_TOOLKIT.md`)
2. ✅ Start PaddleOCR-VL server
3. ✅ Configure OCR service
4. ✅ Test with local files
5. ✅ Deploy to production

## Resources

- **Model Card**: https://huggingface.co/PaddlePaddle/PaddleOCR-VL
- **PaddleOCR Docs**: https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL.html
- **vLLM Docs**: https://docs.vllm.ai/
- **GitHub**: https://github.com/PaddlePaddle/PaddleOCR

---

**Ready to go!** PaddleOCR-VL is the recommended model for OCR tasks in this project. 🚀
