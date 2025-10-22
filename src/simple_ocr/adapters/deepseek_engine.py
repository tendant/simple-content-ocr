"""DeepSeek OCR engine using vLLM for inference."""

import base64
import io
from typing import Any, BinaryIO, List, Optional

import structlog
from PIL import Image

from simple_ocr.adapters.base import BaseOCREngine, OCRError, OCRResponse

logger = structlog.get_logger(__name__)


class DeepSeekOCREngine(BaseOCREngine):
    """DeepSeek OCR engine using vLLM for high-performance inference."""

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize the DeepSeek OCR engine.

        Args:
            config: Configuration dictionary. Supports:
                - model_name: Model name or path
                - gpu_memory_utilization: GPU memory usage (0.0-1.0)
                - max_model_len: Maximum sequence length
                - tensor_parallel_size: Number of GPUs for tensor parallelism
                - temperature: Sampling temperature (default: 0.0 for deterministic)
                - max_tokens: Maximum tokens to generate (default: 2048)
        """
        super().__init__(config)

        self.model_name = config.get("model_name", "deepseek-ai/deepseek-ocr")
        self.gpu_memory_utilization = config.get("gpu_memory_utilization", 0.9)
        self.max_model_len = config.get("max_model_len", 4096)
        self.tensor_parallel_size = config.get("tensor_parallel_size", 1)
        self.temperature = config.get("temperature", 0.0)
        self.max_tokens = config.get("max_tokens", 2048)

        self._llm: Optional[any] = None
        self._initialized = False

        logger.info(
            "deepseek_ocr_engine_initialized",
            model_name=self.model_name,
            gpu_memory_utilization=self.gpu_memory_utilization,
        )

    async def _ensure_initialized(self) -> None:
        """Lazy initialization of vLLM model."""
        if self._initialized:
            return

        try:
            from vllm import LLM

            logger.info("loading_vllm_model", model=self.model_name)

            self._llm = LLM(
                model=self.model_name,
                gpu_memory_utilization=self.gpu_memory_utilization,
                max_model_len=self.max_model_len,
                tensor_parallel_size=self.tensor_parallel_size,
                trust_remote_code=True,  # DeepSeek models may require this
            )

            self._initialized = True
            logger.info("vllm_model_loaded", model=self.model_name)

        except Exception as e:
            logger.error("failed_to_load_vllm_model", error=str(e), model=self.model_name)
            raise OCRError(
                f"Failed to initialize vLLM with model {self.model_name}", original_error=e
            )

    async def process_image(self, image_data: BinaryIO, mime_type: str) -> OCRResponse:
        """
        Process a single image with DeepSeek OCR.

        Args:
            image_data: Binary image data stream.
            mime_type: MIME type of the image.

        Returns:
            OCRResponse with extracted markdown content.

        Raises:
            OCRError: If processing fails.
        """
        await self._ensure_initialized()

        try:
            # Load and validate image
            image = self._load_image(image_data)

            # Perform OCR
            markdown = await self._perform_ocr(image)

            return OCRResponse(
                markdown=markdown,
                page_count=1,
                metadata={
                    "engine": "deepseek",
                    "model": self.model_name,
                    "mime_type": mime_type,
                    "image_size": f"{image.width}x{image.height}",
                },
            )

        except Exception as e:
            logger.error("image_processing_failed", error=str(e), mime_type=mime_type)
            raise OCRError(f"Failed to process image: {str(e)}", original_error=e)

    async def process_document(
        self, document_data: BinaryIO, mime_type: str
    ) -> OCRResponse:
        """
        Process a document with DeepSeek OCR.

        For PDFs and multi-page documents, this processes each page separately
        and combines the results.

        Args:
            document_data: Binary document data stream.
            mime_type: MIME type of the document.

        Returns:
            OCRResponse with extracted markdown content.

        Raises:
            OCRError: If processing fails.
        """
        await self._ensure_initialized()

        try:
            # Convert document to images
            images = self._document_to_images(document_data, mime_type)

            if not images:
                raise OCRError("No pages found in document")

            logger.info("processing_document_pages", page_count=len(images))

            # Process each page
            page_markdowns: List[str] = []
            for idx, image in enumerate(images):
                logger.debug("processing_page", page_num=idx + 1, total_pages=len(images))
                markdown = await self._perform_ocr(image)
                page_markdowns.append(markdown)

            # Combine pages with separators
            combined_markdown = self._combine_pages(page_markdowns)

            return OCRResponse(
                markdown=combined_markdown,
                page_count=len(images),
                metadata={
                    "engine": "deepseek",
                    "model": self.model_name,
                    "mime_type": mime_type,
                    "page_count": str(len(images)),
                },
            )

        except Exception as e:
            logger.error("document_processing_failed", error=str(e), mime_type=mime_type)
            raise OCRError(f"Failed to process document: {str(e)}", original_error=e)

    async def _perform_ocr(self, image: Image.Image) -> str:
        """
        Perform OCR on a single image using vLLM.

        Args:
            image: PIL Image to process.

        Returns:
            Extracted markdown text.
        """
        if not self._llm:
            raise OCRError("vLLM model not initialized")

        try:
            from vllm import SamplingParams

            # Convert image to base64 for the model
            image_base64 = self._image_to_base64(image)

            # Prepare the prompt for DeepSeek OCR
            prompt = self._create_ocr_prompt(image_base64)

            # Configure sampling parameters
            sampling_params = SamplingParams(
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=0.9 if self.temperature > 0 else 1.0,
            )

            # Generate with vLLM
            outputs = self._llm.generate([prompt], sampling_params)

            if not outputs or len(outputs) == 0:
                raise OCRError("No output from vLLM")

            # Extract the generated text
            output_text = outputs[0].outputs[0].text.strip()

            return output_text

        except Exception as e:
            logger.error("ocr_inference_failed", error=str(e))
            raise OCRError(f"OCR inference failed: {str(e)}", original_error=e)

    def _load_image(self, image_data: BinaryIO) -> Image.Image:
        """
        Load and validate an image from binary data.

        Args:
            image_data: Binary image data stream.

        Returns:
            PIL Image object.

        Raises:
            OCRError: If image loading fails.
        """
        try:
            image_data.seek(0)
            image = Image.open(image_data)
            # Convert to RGB if necessary
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            return image
        except Exception as e:
            raise OCRError(f"Failed to load image: {str(e)}", original_error=e)

    def _document_to_images(
        self, document_data: BinaryIO, mime_type: str
    ) -> List[Image.Image]:
        """
        Convert a document to a list of images (one per page).

        Args:
            document_data: Binary document data stream.
            mime_type: MIME type of the document.

        Returns:
            List of PIL Image objects.

        Raises:
            OCRError: If conversion fails.
        """
        document_data.seek(0)

        if "pdf" in mime_type.lower():
            return self._pdf_to_images(document_data)
        elif "docx" in mime_type.lower():
            # For DOCX, we'd need to convert to PDF first or use a different approach
            # This is a simplified version
            raise OCRError("DOCX processing not yet implemented")
        elif "pptx" in mime_type.lower():
            raise OCRError("PPTX processing not yet implemented")
        elif "xlsx" in mime_type.lower():
            raise OCRError("XLSX processing not yet implemented")
        else:
            # Treat as image
            return [self._load_image(document_data)]

    def _pdf_to_images(self, pdf_data: BinaryIO) -> List[Image.Image]:
        """
        Convert PDF to list of images.

        Args:
            pdf_data: Binary PDF data stream.

        Returns:
            List of PIL Image objects.

        Raises:
            OCRError: If conversion fails.
        """
        try:
            import pypdfium2 as pdfium

            pdf_data.seek(0)
            pdf_bytes = pdf_data.read()

            pdf = pdfium.PdfDocument(pdf_bytes)
            images = []

            for page_num in range(len(pdf)):
                page = pdf[page_num]
                # Render at 2x scale for better OCR quality
                bitmap = page.render(scale=2.0)
                pil_image = bitmap.to_pil()
                images.append(pil_image)

            return images

        except Exception as e:
            raise OCRError(f"Failed to convert PDF to images: {str(e)}", original_error=e)

    def _image_to_base64(self, image: Image.Image) -> str:
        """
        Convert PIL Image to base64 string.

        Args:
            image: PIL Image object.

        Returns:
            Base64-encoded image string.
        """
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")

    def _create_ocr_prompt(self, image_base64: str) -> str:
        """
        Create the OCR prompt for DeepSeek model.

        Args:
            image_base64: Base64-encoded image.

        Returns:
            Formatted prompt string.
        """
        # DeepSeek OCR expects a specific prompt format
        # Adjust this based on the actual model's expected format
        return f"""Extract all text from this image and format it as clean markdown.
Preserve the document structure, headings, lists, and formatting.

<image>{image_base64}</image>

Extracted markdown:"""

    def _combine_pages(self, page_markdowns: List[str]) -> str:
        """
        Combine multiple page markdowns into a single document.

        Args:
            page_markdowns: List of markdown strings, one per page.

        Returns:
            Combined markdown string.
        """
        if len(page_markdowns) == 1:
            return page_markdowns[0]

        # Add page separators
        result = []
        for idx, page_md in enumerate(page_markdowns):
            if idx > 0:
                result.append("\n\n---\n\n")  # Page separator
                result.append(f"<!-- Page {idx + 1} -->\n\n")

            result.append(page_md)

        return "".join(result)

    async def cleanup(self) -> None:
        """Clean up vLLM resources."""
        if self._llm:
            logger.info("cleaning_up_vllm_resources")
            # vLLM cleanup if needed
            self._llm = None
            self._initialized = False
