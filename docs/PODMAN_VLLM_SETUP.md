# Running vLLM with Podman

Podman handles GPU access differently from Docker. Here's how to run vLLM with Podman.

## Prerequisites

1. **NVIDIA GPU drivers installed**
2. **nvidia-container-toolkit** (NVIDIA Container Toolkit)
3. **Podman 4.0+**

## Setup NVIDIA Container Toolkit for Podman

### Install nvidia-container-toolkit

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# RHEL/CentOS/Fedora
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/nvidia-container-toolkit.repo | sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

sudo yum install -y nvidia-container-toolkit
```

### Configure CDI (Container Device Interface)

```bash
# Generate CDI specification
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

# Verify CDI devices
podman run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi
```

## Running vLLM with Podman

### Method 1: Using CDI (Recommended)

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

**Key differences from Docker:**
- Use `--device nvidia.com/gpu=all` instead of `--runtime nvidia --gpus all`
- Add `--security-opt=label=disable` for SELinux
- Add `:Z` to volume mounts for SELinux relabeling
- Remove `--ipc=host` (not needed with Podman)

### Method 2: Using Device Mapping

If CDI isn't set up, you can manually map GPU devices:

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

### Method 3: Rootless Podman with CDI

For rootless Podman (running as non-root user):

```bash
# First, configure CDI for rootless
nvidia-ctk cdi generate --output=$HOME/.config/cdi/nvidia.yaml

# Then run
podman run -d \
    --device nvidia.com/gpu=all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 8000:8000 \
    --name vllm-server \
    docker.io/vllm/vllm-openai:latest \
    --model Qwen/Qwen2-VL-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code
```

## Verify It's Working

```bash
# Check container is running
podman ps

# Check GPU is accessible
podman exec vllm-server nvidia-smi

# Test vLLM server
curl http://localhost:8000/v1/models

# View logs
podman logs vllm-server
```

## Using Podman Compose

Create `podman-compose.yml`:

```yaml
version: '3.8'

services:
  vllm:
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
      - Qwen/Qwen2-VL-7B-Instruct
      - --host
      - 0.0.0.0
      - --port
      - "8000"
      - --trust-remote-code
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  ocr-worker:
    build: .
    depends_on:
      - vllm
    environment:
      - OCR_ENGINE=vllm
      - VLLM_URL=http://vllm:8000
      - MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct
    command: python -m simple_ocr.workers.nats_worker
```

**Run with podman-compose:**

```bash
# Install podman-compose if needed
pip install podman-compose

# Start services
podman-compose up -d

# View logs
podman-compose logs -f

# Stop services
podman-compose down
```

## Using Podman Pod

For more advanced setups, use Podman pods:

```bash
# Create a pod
podman pod create --name ocr-pod -p 8000:8000

# Run vLLM in the pod
podman run -d \
    --pod ocr-pod \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    --name vllm-server \
    docker.io/vllm/vllm-openai:latest \
    --model Qwen/Qwen2-VL-7B-Instruct \
    --trust-remote-code

# Run OCR workers in the same pod
podman run -d \
    --pod ocr-pod \
    -e OCR_ENGINE=vllm \
    -e VLLM_URL=http://localhost:8000 \
    --name ocr-worker-1 \
    simple-ocr-worker

# Services can communicate via localhost within the pod
```

## Troubleshooting

### Error: "nvidia.com/gpu not found"

CDI not configured. Fix:

```bash
# Generate CDI config
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

# Verify
podman run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi
```

### Error: "permission denied" accessing GPU

```bash
# Add your user to video/render groups
sudo usermod -a -G video,render $USER

# For rootless, ensure CDI is in user's config
nvidia-ctk cdi generate --output=$HOME/.config/cdi/nvidia.yaml

# Re-login or run
newgrp video
```

### SELinux issues

```bash
# Option 1: Disable SELinux labels for container
podman run --security-opt=label=disable ...

# Option 2: Relabel volumes
podman run -v ~/.cache:/cache:Z ...

# Option 3: Set SELinux to permissive (not recommended for production)
sudo setenforce 0
```

### Can't download model

```bash
# Volume permissions issue - use :Z flag
podman run -v ~/.cache/huggingface:/root/.cache/huggingface:Z ...

# Or run as your user
podman run --user $(id -u):$(id -g) \
    -v ~/.cache/huggingface:/.cache/huggingface:Z ...
```

### Container won't start

```bash
# Check logs
podman logs vllm-server

# Run interactively to debug
podman run -it --rm \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    docker.io/vllm/vllm-openai:latest \
    /bin/bash
```

## Resource Management

### Limit GPU memory

```bash
podman run -d \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    docker.io/vllm/vllm-openai:latest \
    --model Qwen/Qwen2-VL-7B-Instruct \
    --trust-remote-code \
    --gpu-memory-utilization 0.8  # Use 80% of GPU memory
```

### Use specific GPU

```bash
# For multi-GPU systems, select GPU 0
podman run -d \
    --device nvidia.com/gpu=0 \
    --security-opt=label=disable \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    docker.io/vllm/vllm-openai:latest \
    --model Qwen/Qwen2-VL-7B-Instruct \
    --trust-remote-code
```

### Limit CPU/RAM

```bash
podman run -d \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    --cpus=4 \
    --memory=16g \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    docker.io/vllm/vllm-openai:latest \
    --model Qwen/Qwen2-VL-7B-Instruct \
    --trust-remote-code
```

## Systemd Integration

Create a systemd service for vLLM:

**`/etc/systemd/system/vllm-server.service`:**

```ini
[Unit]
Description=vLLM OpenAI Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=10

ExecStartPre=/usr/bin/podman rm -f vllm-server
ExecStart=/usr/bin/podman run \
    --rm \
    --name vllm-server \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -v /home/user/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    docker.io/vllm/vllm-openai:latest \
    --model Qwen/Qwen2-VL-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code

ExecStop=/usr/bin/podman stop vllm-server

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable vllm-server
sudo systemctl start vllm-server

# Check status
sudo systemctl status vllm-server

# View logs
sudo journalctl -u vllm-server -f
```

## Quick Reference

### Start vLLM (Podman)

```bash
podman run -d \
    --device nvidia.com/gpu=all \
    --security-opt=label=disable \
    -v ~/.cache/huggingface:/root/.cache/huggingface:Z \
    -p 8000:8000 \
    --name vllm-server \
    docker.io/vllm/vllm-openai:latest \
    --model Qwen/Qwen2-VL-7B-Instruct \
    --trust-remote-code
```

### Common Commands

```bash
# Start
podman start vllm-server

# Stop
podman stop vllm-server

# Restart
podman restart vllm-server

# Logs
podman logs -f vllm-server

# Remove
podman rm -f vllm-server

# Shell access
podman exec -it vllm-server /bin/bash

# Check GPU
podman exec vllm-server nvidia-smi
```

## Differences from Docker

| Docker | Podman |
|--------|--------|
| `--runtime nvidia --gpus all` | `--device nvidia.com/gpu=all` |
| `--ipc=host` | Not needed |
| `-v /path:/path` | `-v /path:/path:Z` (SELinux) |
| `docker.io/` prefix optional | `docker.io/` prefix required |
| Root daemon | Rootless by default |

## Next Steps

1. ✅ Set up nvidia-container-toolkit
2. ✅ Generate CDI configuration
3. ✅ Start vLLM with Podman
4. ✅ Configure OCR service to use vLLM
5. ✅ Test with local files

## Resources

- **Podman GPU Guide**: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html
- **CDI Specification**: https://github.com/container-orchestrated-devices/container-device-interface
- **Podman Documentation**: https://docs.podman.io/
- **vLLM Documentation**: https://docs.vllm.ai/
