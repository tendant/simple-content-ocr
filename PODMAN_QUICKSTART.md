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

```bash
podman run -d \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    --name vllm-server \
    docker.io/vllm/vllm-openai:latest \
    --model Qwen/Qwen2-VL-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code
```

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
export MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct

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
    --name vllm-server \
    docker.io/vllm/vllm-openai:latest \
    --model Qwen/Qwen2-VL-7B-Instruct \
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
podman start vllm-server

# Stop
podman stop vllm-server

# Logs
podman logs -f vllm-server

# Shell
podman exec -it vllm-server /bin/bash

# GPU check
podman exec vllm-server nvidia-smi

# Remove
podman rm -f vllm-server
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
