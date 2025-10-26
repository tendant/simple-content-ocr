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

### Step 2: Run PaddleOCR-VL Server

**⚠️ IMPORTANT: PaddleOCR-VL is NOT compatible with vLLM**

PaddleOCR-VL has a custom architecture that vLLM doesn't support. You'll get this error with vLLM:
```
ValueError: There is no module or parameter named 'mlp_AR' in TransformersForCausalLM
```

**Solution: Use the Custom PaddleOCR Server (Uses HuggingFace Transformers)**

```bash
# Install dependencies (one-time setup)
uv venv --python 3.12 --seed
uv sync

# Start the custom server (runs on port 8000)
uv run python scripts/run_paddleocr_server.py --host 0.0.0.0 --port 8000
```

This custom server:
- ✅ Uses regular HuggingFace `transformers` with `trust_remote_code=True`
- ✅ Provides OpenAI-compatible API (same as vLLM)
- ✅ Works with all GPUs (no FlashAttention requirement)
- ✅ Only ~1.8GB VRAM for PaddleOCR-VL

See `CUSTOM_SERVER_SETUP.md` for detailed configuration.

**Key changes from Docker:**
- ✅ `--device nvidia.com/gpu=all` (instead of `--runtime nvidia --gpus all`)
- ✅ `--security-opt=label=disable` (for SELinux)
- ✅ `-v path:path:Z` (`:Z` for SELinux relabeling)
- ✅ `docker.io/` prefix (explicit registry)
- ❌ Remove `--ipc=host` (not needed)

### Step 3: Verify It's Running

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test models API
curl http://localhost:8000/v1/models

# Check GPU usage
nvidia-smi
```

Expected output:
```json
{"status":"healthy","model_loaded":true,"device":"cuda","memory_used_mb":1839.5}
{"object":"list","data":[{"id":"PaddlePaddle/PaddleOCR-VL","object":"model","created":0,"owned_by":"paddleocr"}]}
```

## Then Configure Your OCR Service

```bash
# In .env or export
export OCR_ENGINE=vllm  # Custom server uses OpenAI-compatible API
export VLLM_URL=http://localhost:8000
export MODEL_NAME=PaddlePaddle/PaddleOCR-VL

# Test it
uv run python examples/test_local_file.py test_document.png --engine vllm
```

**Note:** Even though we're using the custom server (not vLLM), we still use `OCR_ENGINE=vllm` because the custom server provides an OpenAI-compatible API that's identical to vLLM's interface.

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
