"""Unit tests for OCR adapters."""

import io
from unittest.mock import MagicMock

import pytest
from PIL import Image

from simple_ocr.adapters import (
    BaseOCREngine,
    DeepSeekOCREngine,
    MockOCREngine,
    OCREngineFactory,
    OCRError,
    OCRResponse,
)
from simple_ocr.config import Settings


class TestMockOCREngine:
    """Tests for MockOCREngine."""

    @pytest.fixture
    def mock_engine(self) -> MockOCREngine:
        """Create a mock OCR engine instance."""
        return MockOCREngine(config={"delay_ms": 0, "fail_rate": 0.0})

    @pytest.fixture
    def sample_image_data(self) -> io.BytesIO:
        """Create sample image data."""
        # Create a simple test image
        img = Image.new("RGB", (100, 100), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    @pytest.mark.asyncio
    async def test_process_image_success(
        self, mock_engine: MockOCREngine, sample_image_data: io.BytesIO
    ) -> None:
        """Test successful image processing."""
        result = await mock_engine.process_image(sample_image_data, "image/png")

        assert isinstance(result, OCRResponse)
        assert isinstance(result.markdown, str)
        assert len(result.markdown) > 0
        assert result.page_count == 1
        assert result.metadata["engine"] == "mock"
        assert result.metadata["mime_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_process_image_contains_expected_content(
        self, mock_engine: MockOCREngine, sample_image_data: io.BytesIO
    ) -> None:
        """Test that mock content contains expected sections."""
        result = await mock_engine.process_image(sample_image_data, "image/jpeg")

        assert "# Mock OCR Result" in result.markdown
        assert "Document Information" in result.markdown
        assert "Lorem ipsum" in result.markdown

    @pytest.mark.asyncio
    async def test_process_document_pdf(self, mock_engine: MockOCREngine) -> None:
        """Test PDF document processing."""
        # Create mock PDF data (100KB to simulate multiple pages, >50KB per page threshold)
        pdf_data = io.BytesIO(b"x" * 102400)

        result = await mock_engine.process_document(pdf_data, "application/pdf")

        assert isinstance(result, OCRResponse)
        assert result.page_count > 1  # Should estimate multiple pages
        assert result.metadata["engine"] == "mock"

    @pytest.mark.asyncio
    async def test_process_with_simulated_failure(self) -> None:
        """Test simulated failure."""
        failing_engine = MockOCREngine(config={"delay_ms": 0, "fail_rate": 1.0})
        img_data = io.BytesIO(b"fake image data")

        with pytest.raises(OCRError) as exc_info:
            await failing_engine.process_image(img_data, "image/png")

        assert "simulated failure" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_process_count_increments(
        self, mock_engine: MockOCREngine, sample_image_data: io.BytesIO
    ) -> None:
        """Test that process count increments."""
        assert mock_engine.process_count == 0

        await mock_engine.process_image(sample_image_data, "image/png")
        assert mock_engine.process_count == 1

        sample_image_data.seek(0)
        await mock_engine.process_image(sample_image_data, "image/png")
        assert mock_engine.process_count == 2

    @pytest.mark.asyncio
    async def test_page_count_estimation(self, mock_engine: MockOCREngine) -> None:
        """Test page count estimation for different document types."""
        # Small PDF (should be 1 page)
        small_pdf = io.BytesIO(b"x" * 1024)
        result = await mock_engine.process_document(small_pdf, "application/pdf")
        assert result.page_count == 1

        # Large PDF (should be multiple pages)
        large_pdf = io.BytesIO(b"x" * 200000)
        result = await mock_engine.process_document(large_pdf, "application/pdf")
        assert result.page_count > 1

    def test_format_size(self, mock_engine: MockOCREngine) -> None:
        """Test size formatting."""
        assert "B" in mock_engine._format_size(100)
        assert "KB" in mock_engine._format_size(2048)
        assert "MB" in mock_engine._format_size(2097152)


class TestOCREngineFactory:
    """Tests for OCREngineFactory."""

    def test_create_mock_engine(self) -> None:
        """Test creating a mock engine."""
        engine = OCREngineFactory.create("mock", {"delay_ms": 0})

        assert isinstance(engine, MockOCREngine)
        assert isinstance(engine, BaseOCREngine)

    def test_create_deepseek_engine(self) -> None:
        """Test creating a DeepSeek engine."""
        config = {
            "model_name": "test-model",
            "gpu_memory_utilization": 0.5,
        }
        engine = OCREngineFactory.create("deepseek", config)

        assert isinstance(engine, DeepSeekOCREngine)
        assert isinstance(engine, BaseOCREngine)

    def test_create_unknown_engine_raises_error(self) -> None:
        """Test that creating an unknown engine raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            OCREngineFactory.create("nonexistent", {})

        assert "Unknown OCR engine type" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_create_from_settings_mock(self) -> None:
        """Test creating engine from settings with mock engine."""
        settings = Settings(ocr_engine="mock")
        engine = OCREngineFactory.create_from_settings(settings)

        assert isinstance(engine, MockOCREngine)

    def test_create_from_settings_deepseek(self) -> None:
        """Test creating engine from settings with DeepSeek engine."""
        settings = Settings(
            ocr_engine="deepseek",
            model_name="test-model",
            vllm_gpu_memory_utilization=0.8,
        )
        engine = OCREngineFactory.create_from_settings(settings)

        assert isinstance(engine, DeepSeekOCREngine)
        assert engine.model_name == "test-model"
        assert engine.gpu_memory_utilization == 0.8

    def test_list_engines(self) -> None:
        """Test listing available engines."""
        engines = OCREngineFactory.list_engines()

        assert "mock" in engines
        assert "deepseek" in engines
        assert isinstance(engines, list)

    def test_register_custom_engine(self) -> None:
        """Test registering a custom engine."""

        class CustomEngine(BaseOCREngine):
            async def process_image(self, image_data, mime_type):
                return OCRResponse(markdown="custom", page_count=1)

            async def process_document(self, document_data, mime_type):
                return OCRResponse(markdown="custom", page_count=1)

        OCREngineFactory.register_engine("custom", CustomEngine)

        assert "custom" in OCREngineFactory.list_engines()

        engine = OCREngineFactory.create("custom", {})
        assert isinstance(engine, CustomEngine)

    def test_register_invalid_engine_raises_error(self) -> None:
        """Test that registering non-OCR engine class raises TypeError."""

        class NotAnEngine:
            pass

        with pytest.raises(TypeError) as exc_info:
            OCREngineFactory.register_engine("invalid", NotAnEngine)

        assert "must inherit from BaseOCREngine" in str(exc_info.value)


class TestOCRResponse:
    """Tests for OCRResponse model."""

    def test_ocr_response_creation(self) -> None:
        """Test creating an OCRResponse."""
        response = OCRResponse(
            markdown="# Test",
            page_count=2,
            metadata={"key": "value"},
        )

        assert response.markdown == "# Test"
        assert response.page_count == 2
        assert response.metadata["key"] == "value"

    def test_ocr_response_defaults(self) -> None:
        """Test OCRResponse default values."""
        response = OCRResponse(markdown="content")

        assert response.markdown == "content"
        assert response.page_count == 1
        assert response.metadata == {}


class TestOCRError:
    """Tests for OCRError exception."""

    def test_ocr_error_creation(self) -> None:
        """Test creating an OCRError."""
        error = OCRError("Test error")

        assert str(error) == "Test error"
        assert error.original_error is None

    def test_ocr_error_with_original(self) -> None:
        """Test OCRError with original exception."""
        original = ValueError("original error")
        error = OCRError("Wrapped error", original_error=original)

        assert str(error) == "Wrapped error"
        assert error.original_error is original
        assert isinstance(error.original_error, ValueError)


class TestBaseOCREngine:
    """Tests for BaseOCREngine abstract class."""

    def test_cannot_instantiate_base_engine(self) -> None:
        """Test that BaseOCREngine cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseOCREngine({})  # type: ignore

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test async context manager support."""
        mock_engine = MockOCREngine(config={})

        async with mock_engine as engine:
            assert engine is mock_engine

    @pytest.mark.asyncio
    async def test_cleanup_called_on_exit(self) -> None:
        """Test that cleanup is called on async context manager exit."""
        mock_engine = MockOCREngine(config={})
        cleanup_called = False

        async def mock_cleanup() -> None:
            nonlocal cleanup_called
            cleanup_called = True

        mock_engine.cleanup = mock_cleanup

        async with mock_engine:
            pass

        assert cleanup_called


class TestDeepSeekOCREngine:
    """Tests for DeepSeekOCREngine (without actual vLLM)."""

    @pytest.fixture
    def deepseek_engine(self) -> DeepSeekOCREngine:
        """Create a DeepSeek engine instance."""
        return DeepSeekOCREngine(
            config={
                "model_name": "test-model",
                "gpu_memory_utilization": 0.5,
                "max_model_len": 2048,
            }
        )

    def test_engine_initialization(self, deepseek_engine: DeepSeekOCREngine) -> None:
        """Test DeepSeek engine initialization."""
        assert deepseek_engine.model_name == "test-model"
        assert deepseek_engine.gpu_memory_utilization == 0.5
        assert deepseek_engine.max_model_len == 2048
        assert not deepseek_engine._initialized

    def test_image_to_base64(self, deepseek_engine: DeepSeekOCREngine) -> None:
        """Test image to base64 conversion."""
        img = Image.new("RGB", (10, 10), color="red")
        base64_str = deepseek_engine._image_to_base64(img)

        assert isinstance(base64_str, str)
        assert len(base64_str) > 0

    def test_create_ocr_prompt(self, deepseek_engine: DeepSeekOCREngine) -> None:
        """Test OCR prompt creation."""
        prompt = deepseek_engine._create_ocr_prompt("base64imagedata")

        assert "markdown" in prompt.lower()
        assert "base64imagedata" in prompt

    def test_combine_pages_single(self, deepseek_engine: DeepSeekOCREngine) -> None:
        """Test combining a single page."""
        result = deepseek_engine._combine_pages(["# Page 1"])

        assert result == "# Page 1"

    def test_combine_pages_multiple(self, deepseek_engine: DeepSeekOCREngine) -> None:
        """Test combining multiple pages."""
        pages = ["# Page 1", "# Page 2", "# Page 3"]
        result = deepseek_engine._combine_pages(pages)

        assert "# Page 1" in result
        assert "# Page 2" in result
        assert "# Page 3" in result
        assert "---" in result  # Page separator
        assert "<!-- Page 2 -->" in result

    def test_load_image_success(self, deepseek_engine: DeepSeekOCREngine) -> None:
        """Test successful image loading."""
        img = Image.new("RGB", (50, 50), color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        loaded_img = deepseek_engine._load_image(buffer)

        assert isinstance(loaded_img, Image.Image)
        assert loaded_img.mode in ("RGB", "L")

    def test_load_image_converts_rgba(
        self, deepseek_engine: DeepSeekOCREngine
    ) -> None:
        """Test that RGBA images are converted to RGB."""
        img = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        loaded_img = deepseek_engine._load_image(buffer)

        assert loaded_img.mode == "RGB"

    def test_load_image_invalid_data_raises_error(
        self, deepseek_engine: DeepSeekOCREngine
    ) -> None:
        """Test that invalid image data raises OCRError."""
        invalid_data = io.BytesIO(b"not an image")

        with pytest.raises(OCRError) as exc_info:
            deepseek_engine._load_image(invalid_data)

        assert "Failed to load image" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cleanup(self, deepseek_engine: DeepSeekOCREngine) -> None:
        """Test cleanup method."""
        # Set up a mock LLM
        deepseek_engine._llm = MagicMock()
        deepseek_engine._initialized = True

        await deepseek_engine.cleanup()

        assert deepseek_engine._llm is None
        assert not deepseek_engine._initialized
