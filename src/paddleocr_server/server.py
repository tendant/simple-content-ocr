"""FastAPI server with OpenAI-compatible API for PaddleOCR-VL."""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from paddleocr_server.model import PaddleOCRModel, load_image_from_url
from paddleocr_server.prompts import build_user_prompt
from paddleocr_server.schemas import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    HealthResponse,
    ModelInfo,
    ModelListResponse,
    Usage,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global model instance
model: Optional[PaddleOCRModel] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for model loading."""
    global model
    try:
        # Load model on startup
        logger.info("Loading PaddleOCR-VL model...")
        model = PaddleOCRModel()
        logger.info("Model loaded successfully")
        yield
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down server...")
        model = None


# Create FastAPI app
app = FastAPI(
    title="PaddleOCR-VL Server",
    description="OpenAI-compatible inference server for PaddleOCR-VL",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    return HealthResponse(
        status="healthy",
        model_loaded=True,
        device=model.device,
        memory_used_mb=model.get_memory_usage(),
    )


@app.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    """List available models (OpenAI-compatible)."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    return ModelListResponse(
        object="list",
        data=[
            ModelInfo(
                id=model.model_name,
                object="model",
                created=0,
                owned_by="paddleocr",
            )
        ],
    )


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: ChatCompletionRequest):
    """Create chat completion (OpenAI-compatible).

    This endpoint is compatible with OpenAI's Chat Completions API,
    allowing it to work with the existing VLLMRemoteEngine adapter.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Extract system prompt and image from messages
        system_prompt = None
        image_url = None
        extraction_mode = "markdown"

        for message in request.messages:
            if message.role == "system" and isinstance(message.content, str):
                system_prompt = message.content
            elif message.role == "user":
                if isinstance(message.content, list):
                    for part in message.content:
                        if part.type == "text":
                            # Check if text contains extraction mode hint
                            text_lower = part.text.lower()
                            if "json" in text_lower or "receipt" in text_lower:
                                extraction_mode = "receipt"
                            elif "invoice" in text_lower:
                                extraction_mode = "invoice"
                            elif "table" in text_lower:
                                extraction_mode = "table"
                            elif "form" in text_lower:
                                extraction_mode = "form"
                        elif part.type == "image_url":
                            image_url = part.image_url.url

        if not image_url:
            raise HTTPException(status_code=400, detail="No image provided in request")

        # Load image
        logger.info(f"Loading image from: {image_url[:100]}...")
        image = load_image_from_url(image_url)

        # Build prompt
        prompt = build_user_prompt(system_prompt, extraction_mode)

        # Generate response
        logger.info(f"Generating response with mode: {extraction_mode}")
        generated_text = model.generate(
            image=image,
            prompt=prompt,
            max_new_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        # Create response
        response_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created_at = int(time.time())

        # Estimate token counts (rough approximation)
        prompt_tokens = len(prompt.split()) + 100  # +100 for image tokens
        completion_tokens = len(generated_text.split())

        response = ChatCompletionResponse(
            id=response_id,
            object="chat.completion",
            created=created_at,
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=generated_text),
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "paddleocr_server.server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
