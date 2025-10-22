# Remote vLLM Setup Guide

This guide shows how to use a remote vLLM inference server with simple-content-ocr.

## Overview

Instead of running vLLM locally (which requires GPU), you can connect to a remote vLLM server. This is the **recommended approach** for production deployments.

```
┌─────────────────┐         HTTP          ┌──────────────────┐
│  OCR Service    │ ─────────────────────>│  vLLM Server     │
│  (No GPU)       │   OpenAI API          │  (With GPU)      │
└─────────────────┘                        └──────────────────┘
```

## Benefits

✅ **No local GPU required** - Run OCR service on any machine
✅ **Scalable** - Multiple OCR workers can share one vLLM server
✅ **Simple deployment** - Separate concerns (compute vs inference)
✅ **Cost effective** - Share expensive GPU resources
✅ **Easy updates** - Update models without redeploying OCR service

## Quick Start

### Step 1: Start vLLM Server (On GPU Machine)

**Using Docker (Recommended):**

```bash
docker run --runtime nvidia --gpus all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 8000:8000 \
    --ipc=host \
    vllm/vllm-openai:latest \
    --model Qwen/Qwen2-VL-7B-Instruct \
    --trust-remote-code
```

**Using vLLM directly:**

```bash
# Install vLLM
pip install vllm

# Start server
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2-VL-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code
```

**Verify it's running:**

```bash
curl http://localhost:8000/v1/models
```

### Step 2: Configure OCR Service

**Update `.env`:**

```bash
# Use remote vLLM engine
OCR_ENGINE=vllm

# vLLM server URL
VLLM_URL=http://your-vllm-server:8000

# Model name (should match what's running on vLLM server)
MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct

# Optional: API key if your vLLM server requires it
VLLM_API_KEY=your-api-key-here

# Timeout (in seconds)
VLLM_TIMEOUT=120
```

### Step 3: Test

```bash
# Test with local file
uv run python examples/test_local_file.py test_document.png --engine vllm

# Or start the API
uv run uvicorn simple_ocr.main:app --reload
```

## Supported Vision Models

The remote vLLM engine works with any vision-language model supported by vLLM:

### Recommended Models

| Model | Size | VRAM | Quality | Speed |
|-------|------|------|---------|-------|
| **Qwen2-VL-7B-Instruct** | 7B | 16GB | ⭐⭐⭐⭐⭐ | Fast |
| Qwen2-VL-2B-Instruct | 2B | 8GB | ⭐⭐⭐⭐ | Very Fast |
| LLaVA-v1.6-34B | 34B | 40GB | ⭐⭐⭐⭐⭐ | Slow |
| InternVL2-8B | 8B | 20GB | ⭐⭐⭐⭐⭐ | Fast |

### Start vLLM with Different Models

**Qwen2-VL-2B (Smaller, faster):**
```bash
docker run --runtime nvidia --gpus all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 8000:8000 \
    vllm/vllm-openai:latest \
    --model Qwen/Qwen2-VL-2B-Instruct \
    --trust-remote-code \
    --max-model-len 4096
```

**LLaVA:**
```bash
docker run --runtime nvidia --gpus all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 8000:8000 \
    vllm/vllm-openai:latest \
    --model liuhaotian/llava-v1.6-vicuna-7b \
    --trust-remote-code
```

**InternVL2:**
```bash
docker run --runtime nvidia --gpus all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 8000:8000 \
    vllm/vllm-openai:latest \
    --model OpenGVLab/InternVL2-8B \
    --trust-remote-code
```

## Production Deployment

### Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  NATS Worker │─────>│ NATS Server  │      │              │
│  (No GPU)    │      └──────────────┘      │              │
└──────────────┘                             │   vLLM       │
                                            │   Server     │
┌──────────────┐      ┌──────────────┐      │   (GPU)      │
│  HTTP API    │─────>│ Load         │─────>│              │
│  (No GPU)    │      │ Balancer     │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
```

### Docker Compose Example

**`docker-compose.yml`:**

```yaml
version: '3.8'

services:
  # vLLM inference server (on GPU machine)
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
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    command: [
      "--model", "Qwen/Qwen2-VL-7B-Instruct",
      "--host", "0.0.0.0",
      "--port", "8000",
      "--trust-remote-code",
      "--gpu-memory-utilization", "0.9"
    ]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # NATS message broker
  nats:
    image: nats:latest
    ports:
      - "4222:4222"

  # OCR Worker (no GPU needed)
  ocr-worker:
    build: .
    depends_on:
      - vllm
      - nats
    environment:
      - OCR_ENGINE=vllm
      - VLLM_URL=http://vllm:8000
      - MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct
      - NATS_URL=nats://nats:4222
    command: python -m simple_ocr.workers.nats_worker
    deploy:
      replicas: 3  # Scale workers as needed

  # HTTP API (no GPU needed)
  ocr-api:
    build: .
    depends_on:
      - vllm
    ports:
      - "8080:8000"
    environment:
      - OCR_ENGINE=vllm
      - VLLM_URL=http://vllm:8000
      - MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct
    command: uvicorn simple_ocr.main:app --host 0.0.0.0 --port 8000
```

**Start everything:**

```bash
docker compose up -d
```

### Kubernetes Deployment

**vLLM Deployment:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
          - "--model"
          - "Qwen/Qwen2-VL-7B-Instruct"
          - "--trust-remote-code"
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 1
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
spec:
  selector:
    app: vllm
  ports:
  - port: 8000
    targetPort: 8000
```

**OCR Worker Deployment:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ocr-worker
spec:
  replicas: 5
  selector:
    matchLabels:
      app: ocr-worker
  template:
    metadata:
      labels:
        app: ocr-worker
    spec:
      containers:
      - name: worker
        image: your-registry/simple-ocr:latest
        env:
        - name: OCR_ENGINE
          value: "vllm"
        - name: VLLM_URL
          value: "http://vllm-service:8000"
        - name: MODEL_NAME
          value: "Qwen/Qwen2-VL-7B-Instruct"
        command: ["python", "-m", "simple_ocr.workers.nats_worker"]
```

## Configuration Options

### Environment Variables

```bash
# Required
OCR_ENGINE=vllm
VLLM_URL=http://vllm-server:8000
MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct

# Optional
VLLM_API_KEY=sk-xxxxx  # If vLLM server requires auth
VLLM_TIMEOUT=120  # Request timeout in seconds (default: 120)
```

### vLLM Server Options

Common vLLM server arguments:

```bash
--model MODEL_NAME                    # Required: Model to load
--host 0.0.0.0                       # Bind address
--port 8000                          # Port number
--trust-remote-code                  # Allow remote code execution
--gpu-memory-utilization 0.9         # GPU memory fraction
--max-model-len 4096                 # Max context length
--tensor-parallel-size 2             # Multi-GPU parallelism
--dtype float16                      # Data type
--api-key YOUR_API_KEY               # Require API key
```

## Testing

### Test vLLM Server

```bash
# Check server is running
curl http://localhost:8000/health

# List models
curl http://localhost:8000/v1/models

# Test vision endpoint
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2-VL-7B-Instruct",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What is in this image?"},
        {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
      ]
    }]
  }'
```

### Test OCR Service

```bash
# Test with local file
uv run python examples/test_local_file.py test_document.png --engine vllm

# Test via HTTP API
curl -X POST http://localhost:8000/api/v1/ocr/process \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-123",
    "content_id": "content-456",
    "object_id": "object-789",
    "source_url": "file:///path/to/image.png",
    "mime_type": "image/png"
  }'
```

## Monitoring

### vLLM Metrics

vLLM exposes Prometheus metrics at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

Key metrics:
- `vllm:num_requests_running` - Active requests
- `vllm:gpu_cache_usage_perc` - GPU cache utilization
- `vllm:avg_generation_throughput_toks_per_s` - Tokens/second

### OCR Service Metrics

Monitor OCR service logs for:
- Processing time per job
- Success/failure rates
- Queue depth (NATS)

## Troubleshooting

### vLLM Server Not Starting

```bash
# Check GPU availability
nvidia-smi

# Check Docker GPU runtime
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Check vLLM logs
docker logs vllm-container
```

### Connection Refused

```bash
# Check vLLM is listening
netstat -tlnp | grep 8000

# Check firewall
sudo ufw status

# Test from OCR service container
docker exec ocr-worker curl http://vllm:8000/health
```

### Slow Processing

```bash
# Increase GPU memory
--gpu-memory-utilization 0.95

# Use tensor parallelism (multiple GPUs)
--tensor-parallel-size 2

# Reduce max length
--max-model-len 2048
```

### Out of Memory

```bash
# Use smaller model
--model Qwen/Qwen2-VL-2B-Instruct

# Reduce memory usage
--gpu-memory-utilization 0.7

# Reduce context length
--max-model-len 2048
```

## Performance Optimization

### Batch Processing

Enable batching on vLLM server:

```bash
--max-num-batched-tokens 8192
--max-num-seqs 256
```

### Connection Pooling

OCR service automatically pools connections to vLLM.

### Load Balancing

Use multiple vLLM servers behind a load balancer:

```yaml
# nginx.conf
upstream vllm_backend {
    server vllm-1:8000;
    server vllm-2:8000;
    server vllm-3:8000;
}

server {
    listen 8000;
    location / {
        proxy_pass http://vllm_backend;
    }
}
```

Then point OCR service to nginx:
```bash
VLLM_URL=http://nginx:8000
```

## Cost Optimization

### Use Spot Instances

For cloud deployment:
- Run vLLM on GPU spot instances (60-90% cheaper)
- Run OCR workers on regular instances
- vLLM restarts are OK (stateless)

### Auto-scaling

Scale workers based on queue depth:

```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ocr-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ocr-worker
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: nats_pending_messages
      target:
        type: AverageValue
        averageValue: "10"
```

## Security

### API Key Authentication

**Start vLLM with API key:**

```bash
vllm serve MODEL_NAME --api-key sk-your-secret-key
```

**Configure OCR service:**

```bash
VLLM_API_KEY=sk-your-secret-key
```

### Network Isolation

Use internal networks:

```yaml
services:
  vllm:
    networks:
      - internal

  ocr-worker:
    networks:
      - internal

networks:
  internal:
    driver: bridge
```

## Next Steps

1. ✅ Set up vLLM server on GPU machine
2. ✅ Configure OCR service to use remote vLLM
3. ✅ Test with sample files
4. ✅ Deploy to production
5. ✅ Monitor and optimize

## Resources

- **vLLM Documentation**: https://docs.vllm.ai/
- **OpenAI API Compatibility**: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html
- **Supported Models**: https://docs.vllm.ai/en/latest/models/supported_models.html
- **vLLM Docker Images**: https://hub.docker.com/r/vllm/vllm-openai
