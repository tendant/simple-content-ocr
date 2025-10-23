## PaddleOCR-VL Custom Server API Reference

OpenAI-compatible inference server for PaddleOCR-VL.

**Base URL**: `http://localhost:8001`

---

## Endpoints

### GET /health

Health check endpoint.

**Response** (200):
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda",
  "memory_used_mb": 2048.5
}
```

---

### GET /v1/models

List available models (OpenAI-compatible).

**Response** (200):
```json
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

---

### POST /v1/chat/completions

Create chat completion with vision (OpenAI-compatible).

**Request Body**:
```json
{
  "model": "PaddlePaddle/PaddleOCR-VL",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Extract text as markdown"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,..."
          }
        }
      ]
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1024
}
```

**Parameters**:
- `model` (string, required): Model ID
- `messages` (array, required): List of messages
  - `role` (string): "system", "user", or "assistant"
  - `content` (string | array): Message content
    - Text: `{"type": "text", "text": "..."}`
    - Image: `{"type": "image_url", "image_url": {"url": "..."}}`
- `temperature` (float, optional): 0.0 to 2.0, default 0.7
- `max_tokens` (int, optional): 1 to 4096, default 1024
- `stream` (bool, optional): Not yet supported, must be false

**Response** (200):
```json
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
        "content": "# Extracted Text\n\n..."
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

---

## Usage Examples

### Python with requests

```python
import requests
import base64

# Load image
with open("image.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

# Make request
response = requests.post(
    "http://localhost:8001/v1/chat/completions",
    json={
        "model": "PaddlePaddle/PaddleOCR-VL",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract text as markdown"},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{image_b64}"
                }}
            ]
        }],
        "max_tokens": 2048
    }
)

print(response.json()["choices"][0]["message"]["content"])
```

### curl

```bash
# Health check
curl http://localhost:8001/health

# List models
curl http://localhost:8001/v1/models

# Chat completion (with base64 image)
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "PaddlePaddle/PaddleOCR-VL",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "Extract text"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
      ]
    }],
    "max_tokens": 1024
  }'
```

### With OpenAI Python client

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8001/v1",
    api_key="not-used"  # API key not required
)

response = client.chat.completions.create(
    model="PaddlePaddle/PaddleOCR-VL",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Extract text as markdown"},
            {"type": "image_url", "image_url": {
                "url": "data:image/png;base64,..."
            }}
        ]
    }],
    max_tokens=2048
)

print(response.choices[0].message.content)
```

---

## Extraction Modes

The server automatically detects extraction mode from the text prompt:

| Keyword in Text | Mode | Output Format |
|----------------|------|---------------|
| (default) | markdown | Markdown document |
| "receipt" | receipt | JSON with receipt fields |
| "invoice" | invoice | JSON with invoice fields |
| "table" | table | Markdown tables only |
| "form" | form | JSON with form fields |

**Example** (Receipt extraction):
```json
{
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Extract receipt information as JSON"},
      {"type": "image_url", "image_url": {"url": "..."}}
    ]
  }]
}
```

Response will contain JSON:
```json
{
  "merchant": "Store Name",
  "date": "2024-01-15",
  "total": 42.50,
  ...
}
```

---

## Error Responses

### 400 Bad Request

Missing image in request:
```json
{
  "detail": "No image provided in request"
}
```

### 503 Service Unavailable

Model not loaded:
```json
{
  "detail": "Model not loaded"
}
```

### 500 Internal Server Error

Processing error:
```json
{
  "error": "Error message",
  "type": "RuntimeError"
}
```

---

## Performance

- **Startup time**: ~15 seconds
- **First request**: ~3-5 seconds (model warmup)
- **Subsequent requests**: ~0.5-2 seconds per image
- **Memory**: ~2-3 GB VRAM
- **Concurrency**: Sequential (1 worker recommended)

---

## Compatibility

✅ **OpenAI Python SDK**
✅ **LangChain** (via OpenAI integration)
✅ **Existing vLLM clients**
✅ **VLLMRemoteEngine adapter** (no changes needed)

---

See `CUSTOM_SERVER_SETUP.md` for complete setup guide.
