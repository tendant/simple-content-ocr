"""Pytest configuration and shared fixtures."""

import io
import os
from typing import Generator

import pytest
from PIL import Image


@pytest.fixture
def sample_image() -> Image.Image:
    """Create a sample PIL Image for testing."""
    return Image.new("RGB", (800, 600), color="white")


@pytest.fixture
def sample_image_bytes() -> io.BytesIO:
    """Create sample image bytes for testing."""
    img = Image.new("RGB", (800, 600), color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


@pytest.fixture
def temp_dir(tmp_path: any) -> Generator[str, None, None]:
    """Create a temporary directory for testing."""
    test_dir = tmp_path / "ocr_test"
    test_dir.mkdir()
    yield str(test_dir)
    # Cleanup is handled by pytest's tmp_path


@pytest.fixture
def mock_pdf_bytes() -> io.BytesIO:
    """Create mock PDF bytes for testing."""
    # This is not a real PDF, just mock data
    return io.BytesIO(b"%PDF-1.4\n" + b"x" * 10000)


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up test environment variables."""
    # Set test environment
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OCR_ENGINE", "mock")


@pytest.fixture
def mock_ocr_config() -> dict[str, any]:
    """Provide mock OCR engine configuration."""
    return {
        "delay_ms": 0,
        "fail_rate": 0.0,
    }


@pytest.fixture
def deepseek_ocr_config() -> dict[str, any]:
    """Provide DeepSeek OCR engine configuration."""
    return {
        "model_name": "test-model",
        "gpu_memory_utilization": 0.5,
        "max_model_len": 2048,
        "tensor_parallel_size": 1,
        "temperature": 0.0,
        "max_tokens": 1024,
    }
