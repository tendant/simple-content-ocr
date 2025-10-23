# Podman Quick Start for vLLM

## The Error You Got

```
Error: default OCI runtime "nvidia" not found: invalid argument
```

**Cause**: Podman doesn't use `--runtime nvidia` and `--gpus all` like Docker.

## Quick Fix (3 Steps)

### Step 1: Setup NVIDIA Container Toolkit for Podman

```bash
# Generate CDI (Container Device Interface) config
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

# Verify it works
podman run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi
```

### Step 2: Run vLLM with Podman (Correct Command)

**Recommended: Use PaddleOCR-VL (optimized for OCR, only 4-8GB VRAM)**

#### For Modern GPUs (RTX 3000/4000 series, A100, H100)

```bash
mkdir -p ~/.cache/huggingface

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
    --trust-remote-code
```

#### For Older GPUs (GTX 1000 series, RTX 2000 series)

If you have a GTX 1070/1080 Ti or RTX 2000 series, use xformers backend:

```bash
mkdir -p ~/.cache/huggingface

podman run -d \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    --name paddleocr-vl \
    -e VLLM_ATTENTION_BACKEND=XFORMERS \
    docker.io/vllm/vllm-openai:latest \
    --model PaddlePaddle/PaddleOCR-VL \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code \
    --dtype float16 \
    --max-model-len 4096
```

See `PADDLEOCR_VL_SETUP.md` for detailed configuration and other model options.

**Key changes from Docker:**
- ✅ `--device nvidia.com/gpu=all` (instead of `--runtime nvidia --gpus all`)
- ✅ `--security-opt=label=disable` (for SELinux)
- ✅ `-v path:path:Z` (`:Z` for SELinux relabeling)
- ✅ `docker.io/` prefix (explicit registry)
- ❌ Remove `--ipc=host` (not needed)

### Step 3: Verify It's Running

```bash
# Check container
podman ps

# Test GPU access
podman exec vllm-server nvidia-smi

# Test vLLM API
curl http://localhost:8000/v1/models

# View logs
podman logs -f vllm-server
```

## Then Configure Your OCR Service

```bash
# In .env or export
export OCR_ENGINE=vllm
export VLLM_URL=http://localhost:8000
export MODEL_NAME=PaddlePaddle/PaddleOCR-VL

# Test it
uv run python examples/test_local_file.py test_document.png --engine vllm
```

## If CDI Setup Fails

Try manual device mapping:

```bash
podman run -d \
    --device /dev/nvidia0 \
    --device /dev/nvidiactl \
    --device /dev/nvidia-uvm \
    --device /dev/nvidia-uvm-tools \
    --security-opt=label=disable \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    --name paddleocr-vl \
    docker.io/vllm/vllm-openai:latest \
    --model PaddlePaddle/PaddleOCR-VL \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code
```

## Troubleshooting

### "nvidia.com/gpu not found"

```bash
# Generate CDI config
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

# Restart podman service (if using system)
sudo systemctl restart podman
```

### "permission denied"

```bash
# Add user to video group
sudo usermod -a -G video $USER
newgrp video

# For rootless Podman
nvidia-ctk cdi generate --output=$HOME/.config/cdi/nvidia.yaml
```

### SELinux blocking

```bash
# Temporary: Disable SELinux for container
podman run --security-opt=label=disable ...

# Permanent: Use :Z on volumes
podman run -v ~/.cache:/cache:Z ...
```

## Docker vs Podman Cheat Sheet

| Docker | Podman |
|--------|--------|
| `--runtime nvidia` | Remove this |
| `--gpus all` | `--device nvidia.com/gpu=all` |
| `-v /path:/path` | `-v /path:/path:Z` |
| `--ipc=host` | Remove this |
| `vllm/vllm-openai:latest` | `docker.io/vllm/vllm-openai:latest` |

## Useful Commands

```bash
# Start
podman start paddleocr-vl

# Stop
podman stop paddleocr-vl

# Logs
podman logs -f paddleocr-vl

# Shell
podman exec -it paddleocr-vl /bin/bash

# GPU check
podman exec paddleocr-vl nvidia-smi

# Remove
podman rm -f paddleocr-vl
```

## Full Documentation

See `docs/PODMAN_VLLM_SETUP.md` for complete guide including:
- Systemd integration
- Podman Compose
- Multiple GPU setup
- Resource limits
- And more!

## That's It!

The main difference is GPU access:
- **Docker**: `--runtime nvidia --gpus all`
- **Podman**: `--device nvidia.com/gpu=all`

Everything else in the OCR setup guide works the same! 🚀
