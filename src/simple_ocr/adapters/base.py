"""Base OCR engine interface."""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

from pydantic import BaseModel


class OCRResponse(BaseModel):
    """OCR engine response model."""

    markdown: str
    """Extracted markdown content."""

    page_count: int = 1
    """Number of pages processed."""

    metadata: dict[str, str] = {}
    """Additional metadata from the OCR process."""


class BaseOCREngine(ABC):
    """Abstract base class for OCR engines."""

    def __init__(self, config: dict[str, any]) -> None:
        """
        Initialize the OCR engine.

        Args:
            config: Configuration dictionary for the engine.
        """
        self.config = config

    @abstractmethod
    async def process_image(self, image_data: BinaryIO, mime_type: str) -> OCRResponse:
        """
        Process a single image and extract text as markdown.

        Args:
            image_data: Binary image data stream.
            mime_type: MIME type of the image.

        Returns:
            OCRResponse with extracted markdown and metadata.

        Raises:
            OCRError: If processing fails.
        """
        pass

    @abstractmethod
    async def process_document(
        self, document_data: BinaryIO, mime_type: str
    ) -> OCRResponse:
        """
        Process a document (PDF, DOCX, etc.) and extract text as markdown.

        Args:
            document_data: Binary document data stream.
            mime_type: MIME type of the document.

        Returns:
            OCRResponse with extracted markdown and metadata.

        Raises:
            OCRError: If processing fails.
        """
        pass

    async def cleanup(self) -> None:
        """
        Clean up resources used by the engine.

        Override this method if your engine needs cleanup (e.g., closing connections).
        """
        pass

    def __enter__(self) -> "BaseOCREngine":
        """Context manager entry."""
        return self

    async def __aenter__(self) -> "BaseOCREngine":
        """Async context manager entry."""
        return self

    def __exit__(self, exc_type: any, exc_val: any, exc_tb: any) -> None:
        """Context manager exit."""
        pass

    async def __aexit__(self, exc_type: any, exc_val: any, exc_tb: any) -> None:
        """Async context manager exit."""
        await self.cleanup()


class OCRError(Exception):
    """Base exception for OCR-related errors."""

    def __init__(
        self, message: str, original_error: Optional[Exception] = None
    ) -> None:
        """
        Initialize OCR error.

        Args:
            message: Error message.
            original_error: Original exception that caused this error.
        """
        super().__init__(message)
        self.original_error = original_error
