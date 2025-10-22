"""Basic usage examples for the OCR engines."""

import asyncio
import io

from PIL import Image

from simple_ocr.adapters import OCREngineFactory
from simple_ocr.config import get_settings


async def example_mock_engine() -> None:
    """Example using the mock OCR engine."""
    print("=" * 60)
    print("Example 1: Mock OCR Engine")
    print("=" * 60)

    # Create a mock engine
    engine = OCREngineFactory.create("mock", {"delay_ms": 100, "fail_rate": 0.0})

    # Create a sample image
    img = Image.new("RGB", (800, 600), color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    # Process the image
    result = await engine.process_image(buffer, "image/png")

    print(f"Status: Success")
    print(f"Page Count: {result.page_count}")
    print(f"Metadata: {result.metadata}")
    print(f"\nMarkdown Preview (first 500 chars):")
    print(result.markdown[:500])
    print()


async def example_factory_from_settings() -> None:
    """Example using factory with settings."""
    print("=" * 60)
    print("Example 2: Factory with Settings")
    print("=" * 60)

    # Get settings (reads from .env or uses defaults)
    settings = get_settings()

    # Create engine from settings
    engine = OCREngineFactory.create_from_settings(settings)

    print(f"Created engine type: {type(engine).__name__}")
    print(f"OCR Engine: {settings.ocr_engine}")

    # Create a test document
    doc_data = io.BytesIO(b"x" * 60000)  # Simulated PDF

    # Process the document
    result = await engine.process_document(doc_data, "application/pdf")

    print(f"Page Count: {result.page_count}")
    print(f"Engine: {result.metadata.get('engine')}")
    print()


async def example_custom_engine() -> None:
    """Example registering and using a custom engine."""
    print("=" * 60)
    print("Example 3: Custom OCR Engine")
    print("=" * 60)

    from simple_ocr.adapters import BaseOCREngine, OCRResponse

    # Define a custom engine
    class SimpleOCREngine(BaseOCREngine):
        async def process_image(self, image_data, mime_type):
            return OCRResponse(
                markdown="# Custom Engine Result\n\nThis is from my custom engine!",
                page_count=1,
                metadata={"engine": "custom", "version": "1.0"},
            )

        async def process_document(self, document_data, mime_type):
            return await self.process_image(document_data, mime_type)

    # Register the custom engine
    OCREngineFactory.register_engine("custom", SimpleOCREngine)

    # List all available engines
    print(f"Available engines: {', '.join(OCREngineFactory.list_engines())}")

    # Create and use the custom engine
    engine = OCREngineFactory.create("custom", {})
    img_data = io.BytesIO(b"fake image")

    result = await engine.process_image(img_data, "image/png")

    print(f"Markdown: {result.markdown}")
    print(f"Metadata: {result.metadata}")
    print()


async def example_context_manager() -> None:
    """Example using async context manager for cleanup."""
    print("=" * 60)
    print("Example 4: Async Context Manager")
    print("=" * 60)

    async with OCREngineFactory.create("mock", {}) as engine:
        img = Image.new("RGB", (100, 100), color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        result = await engine.process_image(buffer, "image/png")
        print(f"Processed successfully: {result.page_count} page(s)")
        print("Engine will be cleaned up automatically on exit")

    print("Context exited, cleanup complete")
    print()


async def main() -> None:
    """Run all examples."""
    await example_mock_engine()
    await example_factory_from_settings()
    await example_custom_engine()
    await example_context_manager()


if __name__ == "__main__":
    asyncio.run(main())
