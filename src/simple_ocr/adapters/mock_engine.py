"""Mock OCR engine for testing and development."""

import asyncio
from datetime import UTC, datetime
from typing import Any, BinaryIO

from simple_ocr.adapters.base import BaseOCREngine, OCRError, OCRResponse


class MockOCREngine(BaseOCREngine):
    """Mock OCR engine that returns simulated results without actual processing."""

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize the mock OCR engine.

        Args:
            config: Configuration dictionary. Supports:
                - delay_ms: Simulated processing delay in milliseconds (default: 100)
                - fail_rate: Probability of simulated failure 0.0-1.0 (default: 0.0)
        """
        super().__init__(config)
        self.delay_ms = config.get("delay_ms", 100)
        self.fail_rate = config.get("fail_rate", 0.0)
        self.process_count = 0

    async def process_image(self, image_data: BinaryIO, mime_type: str) -> OCRResponse:
        """
        Process a single image with mock OCR.

        Args:
            image_data: Binary image data stream.
            mime_type: MIME type of the image.

        Returns:
            OCRResponse with mock markdown content.

        Raises:
            OCRError: If simulated failure occurs.
        """
        await self._simulate_processing()
        self.process_count += 1

        # Read image size for metadata
        image_data.seek(0, 2)  # Seek to end
        size_bytes = image_data.tell()
        image_data.seek(0)  # Reset to beginning

        markdown = self._generate_mock_markdown(
            content_type="image", mime_type=mime_type, size_bytes=size_bytes
        )

        return OCRResponse(
            markdown=markdown,
            page_count=1,
            metadata={
                "engine": "mock",
                "mime_type": mime_type,
                "size_bytes": str(size_bytes),
                "processed_at": datetime.now(UTC).isoformat(),
            },
        )

    async def process_document(
        self, document_data: BinaryIO, mime_type: str
    ) -> OCRResponse:
        """
        Process a document with mock OCR.

        Args:
            document_data: Binary document data stream.
            mime_type: MIME type of the document.

        Returns:
            OCRResponse with mock markdown content.

        Raises:
            OCRError: If simulated failure occurs.
        """
        await self._simulate_processing()
        self.process_count += 1

        # Read document size for metadata
        document_data.seek(0, 2)  # Seek to end
        size_bytes = document_data.tell()
        document_data.seek(0)  # Reset to beginning

        # Simulate multi-page documents
        page_count = self._estimate_page_count(mime_type, size_bytes)

        markdown = self._generate_mock_markdown(
            content_type="document",
            mime_type=mime_type,
            size_bytes=size_bytes,
            page_count=page_count,
        )

        return OCRResponse(
            markdown=markdown,
            page_count=page_count,
            metadata={
                "engine": "mock",
                "mime_type": mime_type,
                "size_bytes": str(size_bytes),
                "page_count": str(page_count),
                "processed_at": datetime.now(UTC).isoformat(),
            },
        )

    async def _simulate_processing(self) -> None:
        """Simulate processing delay and potential failures."""
        # Simulate processing time
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000.0)

        # Simulate random failures
        if self.fail_rate > 0:
            import random

            if random.random() < self.fail_rate:
                raise OCRError(f"Mock OCR simulated failure (fail_rate={self.fail_rate})")

    def _estimate_page_count(self, mime_type: str, size_bytes: int) -> int:
        """
        Estimate page count based on file size.

        Args:
            mime_type: MIME type of the document.
            size_bytes: Size of the document in bytes.

        Returns:
            Estimated page count.
        """
        if "pdf" in mime_type:
            # Rough estimate: 50KB per page for PDFs
            return max(1, size_bytes // 51200)
        elif "docx" in mime_type or "pptx" in mime_type:
            # Rough estimate: 30KB per page for Office docs
            return max(1, size_bytes // 30720)
        else:
            return 1

    def _generate_mock_markdown(
        self,
        content_type: str,
        mime_type: str,
        size_bytes: int,
        page_count: int = 1,
    ) -> str:
        """
        Generate mock markdown content.

        Args:
            content_type: Type of content (image or document).
            mime_type: MIME type.
            size_bytes: Size in bytes.
            page_count: Number of pages.

        Returns:
            Mock markdown string.
        """
        lines = [
            f"# Mock OCR Result",
            f"",
            f"This is a mock OCR result generated by MockOCREngine.",
            f"",
            f"## Document Information",
            f"",
            f"- **Type**: {content_type}",
            f"- **MIME Type**: {mime_type}",
            f"- **Size**: {self._format_size(size_bytes)}",
            f"- **Pages**: {page_count}",
            f"- **Processed**: {datetime.now(UTC).isoformat()}",
            f"",
        ]

        # Add mock content for each page
        for page_num in range(1, page_count + 1):
            if page_count > 1:
                lines.extend(
                    [
                        f"## Page {page_num}",
                        f"",
                    ]
                )

            lines.extend(
                [
                    f"Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                    f"Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                    f"",
                    f"### Section {page_num}.1",
                    f"",
                    f"Ut enim ad minim veniam, quis nostrud exercitation ullamco "
                    f"laboris nisi ut aliquip ex ea commodo consequat.",
                    f"",
                    f"### Section {page_num}.2",
                    f"",
                    f"Duis aute irure dolor in reprehenderit in voluptate velit "
                    f"esse cillum dolore eu fugiat nulla pariatur.",
                    f"",
                ]
            )

            if page_num < page_count:
                lines.append("---\n")  # Page separator

        return "\n".join(lines)

    def _format_size(self, size_bytes: int) -> str:
        """
        Format byte size as human-readable string.

        Args:
            size_bytes: Size in bytes.

        Returns:
            Formatted size string.
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
