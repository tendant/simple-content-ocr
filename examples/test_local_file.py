"""Test OCR pipeline with local files."""

import asyncio
import io
import sys
from pathlib import Path
from typing import BinaryIO
from unittest.mock import AsyncMock, MagicMock

from simple_ocr.adapters import OCREngineFactory, SimpleContentClient
from simple_ocr.adapters.content_client import DerivedContentResponse
from simple_ocr.config import get_settings
from simple_ocr.models.job import OCRJob
from simple_ocr.services.ocr_service import OCRService


class LocalContentClient(SimpleContentClient):
    """Mock content client that works with local files."""

    def __init__(self, output_dir: str = "./output") -> None:
        """
        Initialize local content client.

        Args:
            output_dir: Directory to save output files.
        """
        # Don't call super().__init__ since we don't need HTTP client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self._saved_files: list[Path] = []

    async def download_content(self, presigned_url: str) -> BinaryIO:
        """
        'Download' content from local file path.

        Args:
            presigned_url: Actually a local file path for testing.

        Returns:
            Binary content stream.
        """
        file_path = Path(presigned_url)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        print(f"📂 Reading local file: {file_path}")
        with open(file_path, "rb") as f:
            content = f.read()

        return io.BytesIO(content)

    async def create_derived_content(self, request: any) -> DerivedContentResponse:
        """
        Create a mock derived content response.

        Args:
            request: Derived content request.

        Returns:
            Mock response with local file path.
        """
        # Generate output filename
        output_file = self.output_dir / f"{request.content_id}_ocr.md"

        print(f"📝 Will save output to: {output_file}")

        return DerivedContentResponse(
            derived_id=f"derived-{request.content_id}",
            content_id=request.content_id,
            object_id=request.object_id,
            upload_url=str(output_file),  # Use local path as upload URL
        )

    async def upload_derived_content(
        self, upload_url: str, content: bytes, mime_type: str
    ) -> None:
        """
        'Upload' content by saving to local file.

        Args:
            upload_url: Local file path (from create_derived_content).
            content: Content bytes to save.
            mime_type: MIME type of content.
        """
        output_path = Path(upload_url)
        output_path.write_bytes(content)
        self._saved_files.append(output_path)

        print(f"✅ Saved markdown to: {output_path}")
        print(f"📊 Size: {len(content)} bytes")

    async def close(self) -> None:
        """Close (no-op for local client)."""
        pass


async def process_local_file(
    file_path: str,
    engine_type: str = "mock",
    output_dir: str = "./output",
) -> None:
    """
    Process a local file with OCR.

    Args:
        file_path: Path to local file to process.
        engine_type: OCR engine to use (mock, deepseek, or vllm).
        output_dir: Directory to save output files.
    """
    print("=" * 60)
    print("🔍 Simple OCR - Local File Test")
    print("=" * 60)

    # Validate file exists
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Error: File not found: {file_path}")
        return

    # Get file info
    file_size = path.stat().st_size
    mime_type = _guess_mime_type(path)

    print(f"\n📄 File Information:")
    print(f"   Path: {path.absolute()}")
    print(f"   Size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
    print(f"   MIME Type: {mime_type}")
    print(f"   Engine: {engine_type}")
    print()

    # Create OCR engine
    print(f"🔧 Initializing {engine_type} OCR engine...")
    settings = get_settings()
    settings.ocr_engine = engine_type

    ocr_engine = OCREngineFactory.create_from_settings(settings)

    # Create local content client
    content_client = LocalContentClient(output_dir=output_dir)

    # Create OCR service
    ocr_service = OCRService(
        ocr_engine=ocr_engine,
        content_client=content_client,
        cleanup_temp_files=True,
    )

    # Create job
    job = OCRJob(
        job_id=f"local-{path.stem}",
        content_id=path.stem,
        object_id=f"obj-{path.stem}",
        source_url=str(path.absolute()),  # Use local path
        mime_type=mime_type,
        metadata={
            "source": "local_test",
            "filename": path.name,
        },
    )

    print("🚀 Starting OCR processing...")
    print()

    # Process the job
    try:
        result = await ocr_service.process_job(job)

        print("=" * 60)
        print("📊 Processing Results")
        print("=" * 60)
        print(f"Status: {result.status.value}")
        print(f"Pages: {result.page_count}")
        print(f"Processing Time: {result.processing_time_ms}ms")

        if result.error_message:
            print(f"❌ Error: {result.error_message}")
        else:
            print()
            print("📝 Markdown Preview (first 500 chars):")
            print("-" * 60)
            preview = result.markdown_content[:500] if result.markdown_content else ""
            print(preview)
            if len(result.markdown_content) > 500:
                print(f"\n... ({len(result.markdown_content) - 500} more characters)")
            print("-" * 60)

        print()
        print("✅ Processing complete!")
        print(f"📁 Output directory: {Path(output_dir).absolute()}")

    except Exception as e:
        print(f"❌ Processing failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await ocr_service.cleanup()


def _guess_mime_type(path: Path) -> str:
    """
    Guess MIME type from file extension.

    Args:
        path: File path.

    Returns:
        MIME type string.
    """
    ext = path.suffix.lower()

    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    return mime_types.get(ext, "application/octet-stream")


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test OCR pipeline with local files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process an image with mock engine
  python examples/test_local_file.py image.png

  # Process a PDF with mock engine
  python examples/test_local_file.py document.pdf

  # Use DeepSeek engine (requires GPU)
  python examples/test_local_file.py document.pdf --engine deepseek

  # Use vLLM engine (requires GPU)
  python examples/test_local_file.py document.pdf --engine vllm

  # Save output to custom directory
  python examples/test_local_file.py image.jpg --output ./my_output
        """,
    )

    parser.add_argument(
        "file",
        help="Path to file to process (image or PDF)",
    )

    parser.add_argument(
        "--engine",
        "-e",
        choices=["mock", "deepseek", "vllm"],
        default="mock",
        help="OCR engine to use (default: mock)",
    )

    parser.add_argument(
        "--output",
        "-o",
        default="./output",
        help="Output directory for markdown files (default: ./output)",
    )

    args = parser.parse_args()

    await process_local_file(
        file_path=args.file,
        engine_type=args.engine,
        output_dir=args.output,
    )


if __name__ == "__main__":
    asyncio.run(main())
