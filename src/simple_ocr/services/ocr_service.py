"""OCR processing service that orchestrates the complete pipeline."""

import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import structlog

from simple_ocr.adapters.base import BaseOCREngine, OCRError
from simple_ocr.adapters.content_client import (
    DerivedContentRequest,
    SimpleContentClient,
)
from simple_ocr.models.job import OCRJob, OCRJobStatus, OCRResult

logger = structlog.get_logger(__name__)


class OCRService:
    """Service for orchestrating the OCR processing pipeline."""

    def __init__(
        self,
        ocr_engine: BaseOCREngine,
        content_client: SimpleContentClient,
        temp_dir: Optional[str] = None,
        cleanup_temp_files: bool = True,
    ) -> None:
        """
        Initialize the OCR service.

        Args:
            ocr_engine: OCR engine for processing.
            content_client: Client for simple-content API.
            temp_dir: Temporary directory for file processing.
            cleanup_temp_files: Whether to clean up temp files after processing.
        """
        self.ocr_engine = ocr_engine
        self.content_client = content_client
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.cleanup_temp_files = cleanup_temp_files

        logger.info(
            "ocr_service_initialized",
            engine=type(ocr_engine).__name__,
            temp_dir=self.temp_dir,
        )

    async def process_job(self, job: OCRJob) -> OCRResult:
        """
        Process an OCR job through the complete pipeline.

        Pipeline steps:
        1. Download source content from presigned URL
        2. Determine content type and preprocessing
        3. Process with OCR engine
        4. Create derived content record
        5. Upload markdown result
        6. Return result with metadata

        Args:
            job: OCR job to process.

        Returns:
            OCRResult with processing status and output.
        """
        start_time = time.time()
        temp_files: list[Path] = []

        logger.info(
            "processing_ocr_job",
            job_id=job.job_id,
            content_id=job.content_id,
            mime_type=job.mime_type,
        )

        try:
            # Step 1: Download source content
            logger.info("step_1_downloading_content", job_id=job.job_id)
            content_data = await self.content_client.download_content(job.source_url)

            # Step 2: Determine processing method based on MIME type
            logger.info("step_2_determining_processing_method", mime_type=job.mime_type)
            is_image = self._is_image_mime_type(job.mime_type)

            # Step 3: Process with OCR engine
            logger.info(
                "step_3_processing_with_ocr",
                job_id=job.job_id,
                is_image=is_image,
            )

            if is_image:
                ocr_response = await self.ocr_engine.process_image(
                    content_data, job.mime_type
                )
            else:
                ocr_response = await self.ocr_engine.process_document(
                    content_data, job.mime_type
                )

            logger.info(
                "ocr_processing_completed",
                job_id=job.job_id,
                page_count=ocr_response.page_count,
                markdown_length=len(ocr_response.markdown),
            )

            # Step 4: Create derived content record
            logger.info("step_4_creating_derived_content", job_id=job.job_id)
            derived_request = DerivedContentRequest(
                content_id=job.content_id,
                object_id=job.object_id,
                derived_type="ocr_markdown",
                mime_type="text/markdown",
                metadata={
                    "job_id": job.job_id,
                    "page_count": str(ocr_response.page_count),
                    "source_mime_type": job.mime_type,
                    **ocr_response.metadata,
                    **job.metadata,
                },
            )

            derived_response = await self.content_client.create_derived_content(
                derived_request
            )

            # Step 5: Upload markdown result
            if derived_response.upload_url:
                logger.info("step_5_uploading_markdown", job_id=job.job_id)
                markdown_bytes = ocr_response.markdown.encode("utf-8")
                await self.content_client.upload_derived_content(
                    derived_response.upload_url,
                    markdown_bytes,
                    "text/markdown",
                )
            else:
                logger.warning(
                    "no_upload_url_provided",
                    job_id=job.job_id,
                    derived_id=derived_response.derived_id,
                )

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Step 6: Build result
            result = OCRResult(
                job_id=job.job_id,
                status=OCRJobStatus.COMPLETED,
                markdown_content=ocr_response.markdown,
                processing_time_ms=processing_time_ms,
                page_count=ocr_response.page_count,
                metadata={
                    "derived_id": derived_response.derived_id,
                    "content_id": job.content_id,
                    "object_id": job.object_id,
                    **ocr_response.metadata,
                },
            )

            logger.info(
                "ocr_job_completed",
                job_id=job.job_id,
                processing_time_ms=processing_time_ms,
                page_count=ocr_response.page_count,
            )

            return result

        except OCRError as e:
            logger.error(
                "ocr_processing_failed",
                job_id=job.job_id,
                error=str(e),
                error_type="OCRError",
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            return OCRResult(
                job_id=job.job_id,
                status=OCRJobStatus.FAILED,
                error_message=f"OCR processing failed: {str(e)}",
                processing_time_ms=processing_time_ms,
                metadata={"error_type": "OCRError"},
            )

        except Exception as e:
            logger.error(
                "unexpected_error_processing_job",
                job_id=job.job_id,
                error=str(e),
                error_type=type(e).__name__,
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            return OCRResult(
                job_id=job.job_id,
                status=OCRJobStatus.FAILED,
                error_message=f"Unexpected error: {str(e)}",
                processing_time_ms=processing_time_ms,
                metadata={"error_type": type(e).__name__},
            )

        finally:
            # Cleanup temporary files
            if self.cleanup_temp_files and temp_files:
                logger.debug("cleaning_up_temp_files", count=len(temp_files))
                for temp_file in temp_files:
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                    except Exception as e:
                        logger.warning(
                            "temp_file_cleanup_failed",
                            file=str(temp_file),
                            error=str(e),
                        )

    def _is_image_mime_type(self, mime_type: str) -> bool:
        """
        Check if MIME type represents an image.

        Args:
            mime_type: MIME type string.

        Returns:
            True if image, False otherwise.
        """
        image_types = [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/tiff",
            "image/bmp",
            "image/webp",
            "image/gif",
        ]

        return mime_type.lower() in image_types

    async def cleanup(self) -> None:
        """Clean up service resources."""
        logger.info("cleaning_up_ocr_service")
        await self.ocr_engine.cleanup()
        await self.content_client.close()

    async def __aenter__(self) -> "OCRService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: any, exc_val: any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.cleanup()
