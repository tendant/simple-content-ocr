"""Configuration management for simple-ocr service."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Settings
    app_name: str = Field(default="simple-ocr", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment name")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")

    # OCR Engine Configuration
    ocr_engine: str = Field(default="deepseek", description="OCR engine to use")
    model_name: str = Field(
        default="deepseek-ai/deepseek-ocr",
        description="Model name or path",
    )
    model_path: str = Field(
        default="/models/deepseek-ocr",
        description="Local model path",
    )
    vllm_gpu_memory_utilization: float = Field(
        default=0.9,
        description="GPU memory utilization ratio",
    )
    vllm_max_model_len: int = Field(
        default=4096,
        description="Maximum model sequence length",
    )
    vllm_tensor_parallel_size: int = Field(
        default=1,
        description="Tensor parallel size for vLLM",
    )

    # NATS Configuration
    nats_url: str = Field(
        default="nats://localhost:4222",
        description="NATS server URL",
    )
    nats_subject: str = Field(default="ocr.jobs", description="NATS subject for jobs")
    nats_stream: str = Field(default="OCR_JOBS", description="NATS JetStream name")
    nats_consumer: str = Field(
        default="ocr-worker",
        description="NATS consumer name",
    )
    nats_max_concurrent: int = Field(
        default=5,
        description="Max concurrent NATS messages",
    )
    nats_ack_wait: int = Field(
        default=300,
        description="NATS ack wait time in seconds",
    )

    # Simple Content API Configuration
    content_api_url: str = Field(
        default="http://localhost:8080",
        description="Simple Content API base URL",
    )
    content_api_timeout: int = Field(
        default=30,
        description="Content API timeout in seconds",
    )
    content_api_max_retries: int = Field(
        default=3,
        description="Max retries for Content API calls",
    )

    # Processing Configuration
    max_image_size: int = Field(
        default=10485760,
        description="Maximum image size in bytes (10MB)",
    )
    max_pdf_pages: int = Field(
        default=100,
        description="Maximum PDF pages to process",
    )
    supported_image_formats: List[str] = Field(
        default=["jpg", "jpeg", "png", "tiff", "bmp", "webp"],
        description="Supported image formats",
    )
    supported_doc_formats: List[str] = Field(
        default=["pdf", "docx", "pptx", "xlsx"],
        description="Supported document formats",
    )

    # Temp Storage
    temp_dir: str = Field(
        default="/tmp/simple-ocr",
        description="Temporary directory for processing",
    )
    cleanup_temp_files: bool = Field(
        default=True,
        description="Clean up temp files after processing",
    )

    # Performance Tuning
    batch_size: int = Field(default=1, description="Processing batch size")
    processing_timeout: int = Field(
        default=300,
        description="Processing timeout in seconds",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
