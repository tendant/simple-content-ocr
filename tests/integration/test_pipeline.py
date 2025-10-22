"""Integration tests for the OCR processing pipeline."""

import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from simple_ocr.adapters import MockOCREngine, SimpleContentClient
from simple_ocr.adapters.content_client import DerivedContentResponse
from simple_ocr.models.job import OCRJob, OCRJobStatus
from simple_ocr.services.ocr_service import OCRService


class TestOCRPipeline:
    """Integration tests for the complete OCR pipeline."""

    @pytest.fixture
    def mock_content_client(self) -> SimpleContentClient:
        """Create a mock content client."""
        client = SimpleContentClient(base_url="http://localhost:8080")
        return client

    @pytest.fixture
    def mock_ocr_engine(self) -> MockOCREngine:
        """Create a mock OCR engine."""
        return MockOCREngine(config={"delay_ms": 0, "fail_rate": 0.0})

    @pytest.fixture
    def ocr_service(
        self, mock_ocr_engine: MockOCREngine, mock_content_client: SimpleContentClient
    ) -> OCRService:
        """Create an OCR service instance."""
        return OCRService(
            ocr_engine=mock_ocr_engine,
            content_client=mock_content_client,
            cleanup_temp_files=True,
        )

    @pytest.fixture
    def sample_image_bytes(self) -> bytes:
        """Create sample image bytes."""
        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @pytest.fixture
    def sample_job(self) -> OCRJob:
        """Create a sample OCR job."""
        return OCRJob(
            job_id="test-job-123",
            content_id="content-456",
            object_id="object-789",
            source_url="http://example.com/test.png",
            mime_type="image/png",
            created_at=datetime.now(UTC),
            metadata={"test": "true"},
        )

    @pytest.mark.asyncio
    async def test_complete_pipeline_image_processing(
        self,
        ocr_service: OCRService,
        sample_job: OCRJob,
        sample_image_bytes: bytes,
    ) -> None:
        """Test the complete pipeline for image processing."""
        # Mock content client methods
        with patch.object(
            ocr_service.content_client,
            "download_content",
            return_value=io.BytesIO(sample_image_bytes),
        ), patch.object(
            ocr_service.content_client,
            "create_derived_content",
            return_value=DerivedContentResponse(
                derived_id="derived-123",
                content_id="content-456",
                object_id="object-789",
                upload_url="http://example.com/upload",
            ),
        ), patch.object(
            ocr_service.content_client,
            "upload_derived_content",
            return_value=None,
        ):
            # Process the job
            result = await ocr_service.process_job(sample_job)

            # Verify result
            assert result.job_id == sample_job.job_id
            assert result.status == OCRJobStatus.COMPLETED
            assert result.markdown_content is not None
            assert len(result.markdown_content) > 0
            assert result.page_count == 1
            assert result.processing_time_ms is not None
            assert result.processing_time_ms >= 0
            assert "derived_id" in result.metadata
            assert result.metadata["derived_id"] == "derived-123"

    @pytest.mark.asyncio
    async def test_pipeline_with_document(
        self,
        ocr_service: OCRService,
        sample_job: OCRJob,
    ) -> None:
        """Test pipeline with a PDF document."""
        # Create mock PDF data
        pdf_bytes = b"%PDF-1.4\n" + b"x" * 100000

        # Update job for PDF
        sample_job.mime_type = "application/pdf"

        with patch.object(
            ocr_service.content_client,
            "download_content",
            return_value=io.BytesIO(pdf_bytes),
        ), patch.object(
            ocr_service.content_client,
            "create_derived_content",
            return_value=DerivedContentResponse(
                derived_id="derived-456",
                content_id="content-456",
                object_id="object-789",
                upload_url="http://example.com/upload",
            ),
        ), patch.object(
            ocr_service.content_client,
            "upload_derived_content",
            return_value=None,
        ):
            result = await ocr_service.process_job(sample_job)

            assert result.status == OCRJobStatus.COMPLETED
            assert result.page_count > 0
            assert result.markdown_content is not None

    @pytest.mark.asyncio
    async def test_pipeline_handles_download_error(
        self,
        ocr_service: OCRService,
        sample_job: OCRJob,
    ) -> None:
        """Test that pipeline handles download errors gracefully."""
        with patch.object(
            ocr_service.content_client,
            "download_content",
            side_effect=Exception("Download failed"),
        ):
            result = await ocr_service.process_job(sample_job)

            assert result.status == OCRJobStatus.FAILED
            assert result.error_message is not None
            assert "Download failed" in result.error_message or "Unexpected error" in result.error_message
            assert result.processing_time_ms is not None

    @pytest.mark.asyncio
    async def test_pipeline_handles_ocr_error(
        self,
        mock_content_client: SimpleContentClient,
        sample_job: OCRJob,
        sample_image_bytes: bytes,
    ) -> None:
        """Test that pipeline handles OCR errors gracefully."""
        # Create a failing OCR engine
        failing_engine = MockOCREngine(config={"delay_ms": 0, "fail_rate": 1.0})
        ocr_service = OCRService(
            ocr_engine=failing_engine,
            content_client=mock_content_client,
        )

        with patch.object(
            ocr_service.content_client,
            "download_content",
            return_value=io.BytesIO(sample_image_bytes),
        ):
            result = await ocr_service.process_job(sample_job)

            assert result.status == OCRJobStatus.FAILED
            assert result.error_message is not None
            assert "OCR processing failed" in result.error_message

    @pytest.mark.asyncio
    async def test_pipeline_handles_upload_error(
        self,
        ocr_service: OCRService,
        sample_job: OCRJob,
        sample_image_bytes: bytes,
    ) -> None:
        """Test that pipeline handles upload errors gracefully."""
        with patch.object(
            ocr_service.content_client,
            "download_content",
            return_value=io.BytesIO(sample_image_bytes),
        ), patch.object(
            ocr_service.content_client,
            "create_derived_content",
            return_value=DerivedContentResponse(
                derived_id="derived-789",
                content_id="content-456",
                object_id="object-789",
                upload_url="http://example.com/upload",
            ),
        ), patch.object(
            ocr_service.content_client,
            "upload_derived_content",
            side_effect=Exception("Upload failed"),
        ):
            result = await ocr_service.process_job(sample_job)

            # Should fail due to upload error
            assert result.status == OCRJobStatus.FAILED
            assert "Upload failed" in result.error_message or "Unexpected error" in result.error_message

    @pytest.mark.asyncio
    async def test_pipeline_metadata_propagation(
        self,
        ocr_service: OCRService,
        sample_job: OCRJob,
        sample_image_bytes: bytes,
    ) -> None:
        """Test that metadata is properly propagated through the pipeline."""
        sample_job.metadata = {"custom_key": "custom_value", "user": "test_user"}

        with patch.object(
            ocr_service.content_client,
            "download_content",
            return_value=io.BytesIO(sample_image_bytes),
        ), patch.object(
            ocr_service.content_client,
            "create_derived_content",
            return_value=DerivedContentResponse(
                derived_id="derived-meta",
                content_id="content-456",
                object_id="object-789",
                upload_url="http://example.com/upload",
            ),
        ) as mock_create, patch.object(
            ocr_service.content_client,
            "upload_derived_content",
            return_value=None,
        ):
            result = await ocr_service.process_job(sample_job)

            # Verify metadata was included in derived content request
            call_args = mock_create.call_args
            derived_request = call_args[0][0]
            assert "custom_key" in derived_request.metadata
            assert derived_request.metadata["custom_key"] == "custom_value"

            # Verify metadata is in result
            assert result.status == OCRJobStatus.COMPLETED
            assert result.metadata["content_id"] == sample_job.content_id

    @pytest.mark.asyncio
    async def test_cleanup_called(
        self,
        mock_ocr_engine: MockOCREngine,
        mock_content_client: SimpleContentClient,
    ) -> None:
        """Test that cleanup is properly called."""
        ocr_service = OCRService(
            ocr_engine=mock_ocr_engine,
            content_client=mock_content_client,
        )

        # Mock cleanup methods
        engine_cleanup = AsyncMock()
        client_close = AsyncMock()
        mock_ocr_engine.cleanup = engine_cleanup
        mock_content_client.close = client_close

        # Use context manager
        async with ocr_service:
            pass

        # Verify cleanup was called
        engine_cleanup.assert_called_once()
        client_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_determines_image_vs_document(
        self, ocr_service: OCRService
    ) -> None:
        """Test that service correctly identifies images vs documents."""
        # Test image MIME types
        assert ocr_service._is_image_mime_type("image/jpeg") is True
        assert ocr_service._is_image_mime_type("image/png") is True
        assert ocr_service._is_image_mime_type("image/tiff") is True

        # Test document MIME types
        assert ocr_service._is_image_mime_type("application/pdf") is False
        assert ocr_service._is_image_mime_type("application/docx") is False
        assert ocr_service._is_image_mime_type("text/plain") is False
