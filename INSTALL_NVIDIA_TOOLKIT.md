# Install NVIDIA Container Toolkit for Podman

> **Note for Ubuntu 24.04 users**: Use the **Recommended Method** in the Ubuntu/Debian section below. The dynamic repository detection may not work on newer Ubuntu versions.

## Quick Install (Choose Your OS)

### Ubuntu/Debian

**Recommended Method (Works on all versions including Ubuntu 24.04):**

```bash
# 1. Add NVIDIA GPG key
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# 2. Add repository manually
echo "deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://nvidia.github.io/libnvidia-container/stable/deb/amd64 /" | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 3. Update and install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# 4. Verify installation
nvidia-ctk --version
```

**Alternative Method (Dynamic repository detection):**

```bash
# 1. Add NVIDIA repository (may not work on newer Ubuntu versions)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 2. Update and install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# 3. Verify installation
nvidia-ctk --version
```

### RHEL/CentOS/Fedora/Rocky Linux

```bash
# 1. Add NVIDIA repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/nvidia-container-toolkit.repo | \
    sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

# 2. Install
sudo yum install -y nvidia-container-toolkit

# 3. Verify installation
nvidia-ctk --version
```

### Arch Linux

```bash
# Install from AUR
yay -S nvidia-container-toolkit

# Or with paru
paru -S nvidia-container-toolkit

# Verify
nvidia-ctk --version
```

## Configure for Podman

After installation:

```bash
# 1. Generate CDI configuration
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

# 2. Verify CDI setup
podman run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi
```

If step 2 works, you're done! ✅

## Alternative: Install from Binary

If package manager install fails:

```bash
# Download and install
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/x86_64/nvidia-container-toolkit-1.14.3-1.x86_64.rpm -o nvidia-container-toolkit.rpm
sudo rpm -ivh nvidia-container-toolkit.rpm

# Or for Debian/Ubuntu
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/amd64/nvidia-container-toolkit_1.14.3-1_amd64.deb -o nvidia-container-toolkit.deb
sudo dpkg -i nvidia-container-toolkit.deb
```

## Troubleshooting

### Repository not found

If you used the dynamic method and got an error, use the **Recommended Method** above (manual repository setup). This works on all Ubuntu/Debian versions including Ubuntu 24.04.

For **RHEL/Fedora**, try manual repo setup:

```bash
sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo <<EOF
[nvidia-container-toolkit]
name=NVIDIA Container Toolkit
baseurl=https://nvidia.github.io/libnvidia-container/stable/rpm/x86_64
enabled=1
gpgcheck=1
gpgkey=https://nvidia.github.io/libnvidia-container/gpgkey
EOF

sudo yum install -y nvidia-container-toolkit
```

### GPG key errors

```bash
# Import GPG key manually
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
```

### CDI generation fails

```bash
# Create CDI directory first
sudo mkdir -p /etc/cdi

# Generate CDI config
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

# Check the file was created
ls -la /etc/cdi/nvidia.yaml
```

## Verify Everything Works

### 1. Check NVIDIA drivers

```bash
nvidia-smi
```

Should show your GPU(s).

### 2. Check nvidia-ctk

```bash
nvidia-ctk --version
```

Should show version (e.g., 1.14.3).

### 3. Check CDI file

```bash
cat /etc/cdi/nvidia.yaml
```

Should show NVIDIA GPU device specifications.

### 4. Test with Podman

```bash
podman run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi
```

Should show the same GPU info as step 1.

## Now Run vLLM

Once everything above works:

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

## Still Not Working?

### Check Prerequisites

```bash
# 1. NVIDIA driver installed?
nvidia-smi

# 2. Podman installed?
podman --version

# 3. Podman 4.0+? (CDI requires 4.0+)
podman --version
```

### Alternative: Use nvidia-docker Hook (Older Method)

If CDI doesn't work, try the OCI hook method:

```bash
# Configure nvidia-container-runtime
sudo nvidia-ctk runtime configure --runtime=podman

# Restart Podman
sudo systemctl restart podman

# Try running with hook
podman run --rm \
    --hooks-dir=/usr/share/containers/oci/hooks.d \
    ubuntu nvidia-smi
```

### Last Resort: Manual Device Mapping

If nothing else works, manually map GPU devices:

```bash
podman run -d \
    --device /dev/nvidia0:/dev/nvidia0 \
    --device /dev/nvidiactl:/dev/nvidiactl \
    --device /dev/nvidia-uvm:/dev/nvidia-uvm \
    --device /dev/nvidia-uvm-tools:/dev/nvidia-uvm-tools \
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

Find your GPU devices:
```bash
ls -la /dev/nvidia*
```

## Getting Help

If you're still stuck, provide this info:

```bash
# System info
cat /etc/os-release
podman --version
nvidia-smi

# Check if nvidia-ctk exists
which nvidia-ctk
nvidia-ctk --version

# Check CDI
ls -la /etc/cdi/
cat /etc/cdi/nvidia.yaml 2>&1 | head -20

# Test GPU access
podman run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi 2>&1
```

## Quick Links

- **NVIDIA Container Toolkit Docs**: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
- **Podman GPU Guide**: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html
- **GitHub Issues**: https://github.com/NVIDIA/nvidia-container-toolkit/issues
