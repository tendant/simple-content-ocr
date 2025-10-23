"""OpenAI-compatible API schemas."""

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field


# Request models (OpenAI Chat Completions format)
class ImageURL(BaseModel):
    """Image URL content."""

    url: str = Field(..., description="URL or base64-encoded image data")


class TextContent(BaseModel):
    """Text content in message."""

    type: Literal["text"] = "text"
    text: str


class ImageContent(BaseModel):
    """Image content in message."""

    type: Literal["image_url"] = "image_url"
    image_url: ImageURL


ContentPart = Union[TextContent, ImageContent]


class ChatMessage(BaseModel):
    """Chat message."""

    role: Literal["system", "user", "assistant"]
    content: Union[str, list[ContentPart]]


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str = Field(..., description="Model name")
    messages: list[ChatMessage] = Field(..., description="List of messages")
    temperature: float = Field(default=0.7, ge=0, le=2, description="Sampling temperature")
    max_tokens: int = Field(default=1024, ge=1, le=4096, description="Maximum tokens to generate")
    stream: bool = Field(default=False, description="Whether to stream responses")


# Response models (OpenAI Chat Completions format)
class ChatChoice(BaseModel):
    """A single chat completion choice."""

    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class Usage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: Usage


# Model list response
class ModelInfo(BaseModel):
    """Model information."""

    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "paddleocr"


class ModelListResponse(BaseModel):
    """List of available models."""

    object: str = "list"
    data: list[ModelInfo]


# Health check
class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    model_loaded: bool
    device: str
    memory_used_mb: Optional[float] = None
