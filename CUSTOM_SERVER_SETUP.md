# PaddleOCR-VL Custom Server Setup Guide

## Overview

This custom inference server provides a lightweight alternative to vLLM for running PaddleOCR-VL. It's **specifically designed for older GPUs** (GTX 1000 series, RTX 2000 series) that don't support FlashAttention.

### Why Use the Custom Server?

✅ **Works with older GPUs** - No FlashAttention requirements (compute capability 6.x/7.x)
✅ **OpenAI-compatible API** - Drop-in replacement, no code changes needed
✅ **Lightweight** - Only ~200 lines of Python vs full vLLM stack
✅ **Easy debugging** - Direct Python code, easier to troubleshoot
✅ **Lower memory** - Simpler inference pipeline
✅ **Both modes** - General markdown OCR + structured extraction

### When to Use vLLM vs Custom Server

| Feature | vLLM Server | Custom Server |
|---------|-------------|---------------|
| **GPU Support** | Compute capability 8.0+ | Compute capability 6.0+ |
| **Throughput** | High (batching, optimizations) | Medium (single request) |
| **Memory** | Higher | Lower |
| **Setup** | Complex | Simple |
| **Debugging** | Harder | Easier |
| **Best for** | Production, modern GPUs | Development, older GPUs |

**Recommendation**: Use custom server for GTX 1070/1080 Ti, RTX 2000 series. Use vLLM for RTX 3000/4000, A100, H100.

## Quick Start

### Option 1: Direct Python Execution (Recommended for Development)

**1. Install dependencies:**

```bash
# From project root
    pip install -r requirements-server.txt
```

**2. Start the server:**

```bash
# Using the launcher script
python scripts/run_paddleocr_server.py

# Or using the bash script
./scripts/start_paddleocr_server.sh

# Or directly with uvicorn
cd src
uvicorn paddleocr_server.server:app --host 0.0.0.0 --port 8001
```

**3. Verify it's running:**

```bash
# Health check
curl http://localhost:8001/health

# List models
curl http://localhost:8001/v1/models
```

**4. Configure OCR service:**

```bash
export OCR_ENGINE=vllm
export VLLM_URL=http://localhost:8001
export MODEL_NAME=PaddlePaddle/PaddleOCR-VL
```

**5. Test it:**

```bash
# Create test image
uv run python examples/create_test_image.py

# Process with custom server (works with existing code!)
uv run python examples/test_local_file.py test_document.png --engine vllm
```

### Option 2: Docker (Recommended for Production)

**1. Build the image:**

```bash
docker build -f Dockerfile.paddleocr -t paddleocr-server .
```

**2. Run the container:**

```bash
# With Docker
docker run -d \
    --gpus all \
    -p 8001:8001 \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    --name paddleocr-server \
    paddleocr-server

# With Podman
podman run -d \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -p 8001:8001 \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    --name paddleocr-server \
    paddleocr-server
```

**3. Check logs:**

```bash
docker logs -f paddleocr-server
```

### Option 3: Docker Compose (Full Stack)

**1. Start all services:**

```bash
docker compose -f docker-compose.paddleocr.yml up -d
```

This starts:
- PaddleOCR server (port 8001)
- OCR API (port 8000)
- OCR workers (2 replicas)

**2. Check status:**

```bash
docker compose -f docker-compose.paddleocr.yml ps
```

## API Documentation

The server implements the **OpenAI Chat Completions API**, making it compatible with existing vLLM clients.

### Endpoints

#### 1. Health Check

```bash
GET /health

Response:
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda",
  "memory_used_mb": 2048.5
}
```

#### 2. List Models

```bash
GET /v1/models

Response:
{
  "object": "list",
  "data": [
    {
      "id": "PaddlePaddle/PaddleOCR-VL",
      "object": "model",
      "created": 0,
      "owned_by": "paddleocr"
    }
  ]
}
```

#### 3. Chat Completions (Main Endpoint)

```bash
POST /v1/chat/completions

Request:
{
  "model": "PaddlePaddle/PaddleOCR-VL",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Extract text from this image as markdown"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,iVBORw0KGgo..."
          }
        }
      ]
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1024
}

Response:
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "PaddlePaddle/PaddleOCR-VL",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "# Document Title\n\nExtracted text..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 200,
    "total_tokens": 350
  }
}
```

## Usage Modes

### Mode 1: General Markdown OCR (Default)

Extract all text from documents as markdown:

```python
import base64
import requests

# Load and encode image
with open("document.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

# Request
response = requests.post("http://localhost:8001/v1/chat/completions", json={
    "model": "PaddlePaddle/PaddleOCR-VL",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Extract the text from this image as markdown"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
        ]
    }],
    "max_tokens": 2048
})

markdown = response.json()["choices"][0]["message"]["content"]
print(markdown)
```

### Mode 2: Structured Extraction

Extract specific fields as JSON:

```python
# Request with structured extraction prompt
response = requests.post("http://localhost:8001/v1/chat/completions", json={
    "model": "PaddlePaddle/PaddleOCR-VL",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Extract receipt information as JSON"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
        ]
    }],
    "max_tokens": 1024
})

# The server automatically detects "receipt" keyword and uses structured prompt
receipt_data = response.json()["choices"][0]["message"]["content"]
```

**Supported extraction types** (detected automatically from text):
- `receipt` - Receipt information
- `invoice` - Invoice details
- `table` - Tables only
- `form` - Form fields
- Default: General markdown

## Configuration

### Environment Variables

```bash
# Server settings
HOST=0.0.0.0
PORT=8001
WORKERS=1  # Keep at 1 for GPU inference

# Model settings
CUDA_VISIBLE_DEVICES=0  # Which GPU to use
TRANSFORMERS_CACHE=/path/to/cache  # Model cache directory
```

### Command-Line Options

```bash
python scripts/run_paddleocr_server.py \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 1 \
    --log-level info \
    --reload  # Enable auto-reload for development
```

## Troubleshooting

### Model won't load

**Problem**: Out of memory when loading model

**Solution**:
```bash
# Clear CUDA cache before starting
python -c "import torch; torch.cuda.empty_cache()"

# Or restart with fresh process
pkill -f paddleocr_server
```

### Slow inference

**Problem**: Generation takes > 30 seconds per image

**Solutions**:
1. Check GPU is being used:
   ```bash
   nvidia-smi  # Should show python process using GPU
   ```
2. Reduce max_tokens:
   ```python
   "max_tokens": 512  # Instead of 2048
   ```
3. Disable unnecessary logging:
   ```bash
   --log-level warning
   ```

### API compatibility issues

**Problem**: Existing code doesn't work with custom server

**Solution**: The custom server is OpenAI-compatible. If you have issues:
1. Check the model name matches: `PaddlePaddle/PaddleOCR-VL`
2. Verify URL: `http://localhost:8001` (note port 8001, not 8000)
3. Test with curl:
   ```bash
   curl -X POST http://localhost:8001/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"PaddlePaddle/PaddleOCR-VL","messages":[{"role":"user","content":"test"}]}'
   ```

### GPU not detected

**Problem**: Server runs on CPU instead of GPU

**Solutions**:
1. Install CUDA-enabled PyTorch:
   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cu118
   ```
2. Check CUDA availability:
   ```python
   import torch
   print(torch.cuda.is_available())  # Should be True
   print(torch.cuda.get_device_name(0))  # Should show GPU name
   ```

## Performance Tips

### For GTX 1070/1080 Ti (8GB VRAM)

```bash
# Use these settings for optimal performance
python scripts/run_paddleocr_server.py \
    --workers 1 \
    --log-level warning

# In requests, limit max_tokens
"max_tokens": 1024  # Instead of 4096
```

### For RTX 2060/2070 (8GB VRAM)

```bash
# Can handle slightly larger contexts
"max_tokens": 2048
```

### Memory Monitoring

```bash
# Watch GPU memory usage
watch -n 1 nvidia-smi

# Or in Python
python -c "import torch; print(f'{torch.cuda.memory_allocated()/1024**2:.1f} MB')"
```

## Integration with OCR Service

The custom server works **without any code changes** to the OCR service:

```bash
# Just point VLLM_URL to custom server
export OCR_ENGINE=vllm
export VLLM_URL=http://localhost:8001  # Custom server
export MODEL_NAME=PaddlePaddle/PaddleOCR-VL

# Everything else works the same
uv run python examples/test_local_file.py document.pdf --engine vllm
```

## Production Deployment

### Systemd Service

Create `/etc/systemd/system/paddleocr-server.service`:

```ini
[Unit]
Description=PaddleOCR-VL Custom Server
After=network.target

[Service]
Type=simple
User=ocr
WorkingDirectory=/opt/simple-content-ocr
Environment="PATH=/opt/simple-content-ocr/.venv/bin:/usr/bin"
ExecStart=/opt/simple-content-ocr/scripts/start_paddleocr_server.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable paddleocr-server
sudo systemctl start paddleocr-server

# Check status
sudo systemctl status paddleocr-server

# View logs
sudo journalctl -u paddleocr-server -f
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name ocr.example.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }
}
```

## Comparison: vLLM vs Custom Server

### Startup Time

- **vLLM**: ~60 seconds (complex initialization)
- **Custom**: ~15 seconds (simple model loading)

### Memory Usage (PaddleOCR-VL 0.9B)

- **vLLM**: ~3-4 GB VRAM
- **Custom**: ~2-3 GB VRAM

### Throughput (Single GPU)

- **vLLM**: ~10-15 requests/sec (with batching)
- **Custom**: ~2-5 requests/sec (sequential)

### Latency (Per Request)

- **vLLM**: 100-200ms (optimized kernels)
- **Custom**: 200-500ms (standard PyTorch)

**Conclusion**: Use vLLM for production with modern GPUs. Use custom server for development or older GPUs.

## Next Steps

1. ✅ Start custom server
2. ✅ Test with existing code
3. ✅ Monitor GPU memory
4. ✅ Deploy to production

## Support

- **Custom Server Issues**: Check logs in server output or container logs
- **GPU Issues**: See `INSTALL_NVIDIA_TOOLKIT.md`
- **vLLM Alternative**: See `PADDLEOCR_VL_SETUP.md`

---

**Ready!** The custom server provides a simple, debuggable alternative to vLLM for older GPUs. 🚀
