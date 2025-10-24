"""Remote vLLM OCR engine using OpenAI-compatible API."""

import base64
import io
from typing import Any, BinaryIO, List, Optional

import httpx
import structlog
from PIL import Image

from simple_ocr.adapters.base import BaseOCREngine, OCRError, OCRResponse

logger = structlog.get_logger(__name__)


class VLLMRemoteEngine(BaseOCREngine):
    """OCR engine that connects to a remote vLLM inference server."""

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize remote vLLM engine.

        Args:
            config: Configuration with:
                - vllm_url: URL of vLLM server (e.g., http://vllm-server:8000)
                - model_name: Model name (for logging)
                - api_key: Optional API key for authentication
                - temperature: Sampling temperature (default: 0.0)
                - max_tokens: Maximum tokens to generate (default: 2048)
                - timeout: Request timeout in seconds (default: 120)
        """
        super().__init__(config)

        self.vllm_url = config.get("vllm_url", "http://localhost:8000")
        self.model_name = config.get("model_name", "unknown")
        self.api_key = config.get("api_key")
        self.temperature = config.get("temperature", 0.0)
        self.max_tokens = config.get("max_tokens", 2048)
        self.timeout = config.get("timeout", 120)

        # OpenAI-compatible endpoints
        self.chat_url = f"{self.vllm_url}/v1/chat/completions"
        self.completions_url = f"{self.vllm_url}/v1/completions"

        self._client: Optional[httpx.AsyncClient] = None

        logger.info(
            "vllm_remote_engine_initialized",
            vllm_url=self.vllm_url,
            model=self.model_name,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def process_image(self, image_data: BinaryIO, mime_type: str) -> OCRResponse:
        """
        Process image with remote vLLM server.

        Args:
            image_data: Binary image data.
            mime_type: MIME type of image.

        Returns:
            OCR response with extracted markdown.
        """
        logger.info("processing_image_with_remote_vllm", mime_type=mime_type)

        try:
            # Load and prepare image
            image = self._load_image(image_data)
            image_base64 = self._image_to_base64(image)

            # Create OCR prompt
            markdown = await self._call_vllm_api(image_base64)

            return OCRResponse(
                markdown=markdown,
                page_count=1,
                metadata={
                    "engine": "vllm-remote",
                    "model": self.model_name,
                    "vllm_url": self.vllm_url,
                    "mime_type": mime_type,
                },
            )

        except Exception as e:
            logger.error("vllm_api_call_failed", error=str(e))
            raise OCRError(f"vLLM API call failed: {str(e)}", original_error=e)

    async def process_document(
        self, document_data: BinaryIO, mime_type: str
    ) -> OCRResponse:
        """
        Process document with remote vLLM server.

        For PDFs, converts to images and processes page by page.

        Args:
            document_data: Binary document data.
            mime_type: MIME type of document.

        Returns:
            OCR response with extracted markdown.
        """
        logger.info("processing_document_with_remote_vllm", mime_type=mime_type)

        try:
            # Convert document to images
            images = self._document_to_images(document_data, mime_type)

            if not images:
                raise OCRError("No pages found in document")

            logger.info("processing_document_pages", page_count=len(images))

            # Process each page
            page_markdowns: List[str] = []
            for idx, image in enumerate(images):
                logger.debug("processing_page", page=idx + 1, total=len(images))

                image_base64 = self._image_to_base64(image)
                markdown = await self._call_vllm_api(image_base64)
                page_markdowns.append(markdown)

            # Combine pages
            combined_markdown = self._combine_pages(page_markdowns)

            return OCRResponse(
                markdown=combined_markdown,
                page_count=len(images),
                metadata={
                    "engine": "vllm-remote",
                    "model": self.model_name,
                    "vllm_url": self.vllm_url,
                    "mime_type": mime_type,
                    "page_count": str(len(images)),
                },
            )

        except Exception as e:
            logger.error("document_processing_failed", error=str(e))
            raise OCRError(f"Document processing failed: {str(e)}", original_error=e)

    async def _call_vllm_api(self, image_base64: str) -> str:
        """
        Call vLLM API with image.

        Args:
            image_base64: Base64-encoded image.

        Returns:
            Extracted markdown text.
        """
        client = await self._get_client()

        # Prepare request for OpenAI-compatible chat API
        # This works with vision models in vLLM
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self._create_ocr_prompt(),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            },
                        },
                    ],
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        logger.debug("calling_vllm_api", url=self.chat_url)

        try:
            response = await client.post(self.chat_url, json=payload)
            response.raise_for_status()

            result = response.json()

            # Extract markdown from response
            if "choices" in result and len(result["choices"]) > 0:
                markdown = result["choices"][0]["message"]["content"]
                return markdown.strip()
            else:
                raise OCRError("Unexpected response format from vLLM API")

        except httpx.HTTPError as e:
            response = getattr(e, "response", None)
            status_code = getattr(response, "status_code", None) if response else None
            logger.error("http_error", error=str(e), status=status_code)
            raise OCRError(f"HTTP error calling vLLM: {str(e)}", original_error=e)

    def _load_image(self, image_data: BinaryIO) -> Image.Image:
        """Load image from binary data."""
        try:
            image_data.seek(0)
            image = Image.open(image_data)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            return image
        except Exception as e:
            raise OCRError(f"Failed to load image: {str(e)}", original_error=e)

    def _document_to_images(
        self, document_data: BinaryIO, mime_type: str
    ) -> List[Image.Image]:
        """Convert document to list of images."""
        document_data.seek(0)

        if "pdf" in mime_type.lower():
            return self._pdf_to_images(document_data)
        else:
            # Treat as image
            return [self._load_image(document_data)]

    def _pdf_to_images(self, pdf_data: BinaryIO) -> List[Image.Image]:
        """Convert PDF to images."""
        try:
            import pypdfium2 as pdfium

            pdf_data.seek(0)
            pdf_bytes = pdf_data.read()

            pdf = pdfium.PdfDocument(pdf_bytes)
            images = []

            for page_num in range(len(pdf)):
                page = pdf[page_num]
                # Render at 2x for better quality
                bitmap = page.render(scale=2.0)
                pil_image = bitmap.to_pil()
                images.append(pil_image)

            return images

        except Exception as e:
            raise OCRError(f"Failed to convert PDF: {str(e)}", original_error=e)

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")

    def _create_ocr_prompt(self) -> str:
        """Create OCR prompt for the model."""
        return """Extract all text from this image and format it as clean markdown.

Instructions:
- Preserve the document structure (headings, paragraphs, lists, tables)
- Maintain the original text exactly as it appears
- Use proper markdown formatting
- Do not add any commentary or explanation
- Only output the extracted markdown text

Begin extraction:"""

    def _combine_pages(self, page_markdowns: List[str]) -> str:
        """Combine multiple page markdowns."""
        if len(page_markdowns) == 1:
            return page_markdowns[0]

        result = []
        for idx, page_md in enumerate(page_markdowns):
            if idx > 0:
                result.append("\n\n---\n\n")
                result.append(f"<!-- Page {idx + 1} -->\n\n")

            result.append(page_md)

        return "".join(result)

    async def cleanup(self) -> None:
        """Clean up HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("vllm_remote_client_closed")
