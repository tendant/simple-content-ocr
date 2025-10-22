"""Simple Content API client for content storage and retrieval."""

import io
from typing import Any, BinaryIO, Optional

import httpx
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class DerivedContentRequest(BaseModel):
    """Request model for creating derived content."""

    content_id: str
    object_id: str
    derived_type: str = "ocr_markdown"
    mime_type: str = "text/markdown"
    metadata: dict[str, str] = {}


class DerivedContentResponse(BaseModel):
    """Response model for derived content creation."""

    derived_id: str
    content_id: str
    object_id: str
    upload_url: Optional[str] = None
    download_url: Optional[str] = None


class SimpleContentClient:
    """Client for interacting with simple-content API."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the simple-content API client.

        Args:
            base_url: Base URL of the simple-content API.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        self._client: Optional[httpx.AsyncClient] = None

        logger.info(
            "simple_content_client_initialized",
            base_url=self.base_url,
            timeout=timeout,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    async def download_content(self, presigned_url: str) -> BinaryIO:
        """
        Download content from a presigned URL.

        Args:
            presigned_url: Presigned URL to download from.

        Returns:
            Binary content stream.

        Raises:
            httpx.HTTPError: If download fails.
        """
        client = await self._get_client()

        logger.info("downloading_content", url=presigned_url[:100])

        try:
            response = await client.get(presigned_url)
            response.raise_for_status()

            content_length = len(response.content)
            logger.info(
                "content_downloaded",
                size_bytes=content_length,
                content_type=response.headers.get("content-type"),
            )

            return io.BytesIO(response.content)

        except httpx.HTTPError as e:
            logger.error("content_download_failed", error=str(e), url=presigned_url[:100])
            raise

    async def create_derived_content(
        self, request: DerivedContentRequest
    ) -> DerivedContentResponse:
        """
        Create a derived content record.

        Args:
            request: Derived content creation request.

        Returns:
            Derived content response with upload URL.

        Raises:
            httpx.HTTPError: If API request fails.
        """
        client = await self._get_client()

        url = f"{self.base_url}/api/v1/derived-content"

        logger.info(
            "creating_derived_content",
            content_id=request.content_id,
            derived_type=request.derived_type,
        )

        try:
            response = await client.post(
                url,
                json=request.model_dump(),
            )
            response.raise_for_status()

            data = response.json()
            derived_response = DerivedContentResponse(**data)

            logger.info(
                "derived_content_created",
                derived_id=derived_response.derived_id,
                content_id=request.content_id,
            )

            return derived_response

        except httpx.HTTPError as e:
            logger.error(
                "derived_content_creation_failed",
                error=str(e),
                content_id=request.content_id,
            )
            raise

    async def upload_derived_content(
        self, upload_url: str, content: bytes, mime_type: str
    ) -> None:
        """
        Upload derived content to a presigned URL.

        Args:
            upload_url: Presigned upload URL.
            content: Content bytes to upload.
            mime_type: MIME type of the content.

        Raises:
            httpx.HTTPError: If upload fails.
        """
        client = await self._get_client()

        logger.info(
            "uploading_derived_content",
            size_bytes=len(content),
            mime_type=mime_type,
        )

        try:
            response = await client.put(
                upload_url,
                content=content,
                headers={"Content-Type": mime_type},
            )
            response.raise_for_status()

            logger.info("derived_content_uploaded", size_bytes=len(content))

        except httpx.HTTPError as e:
            logger.error(
                "derived_content_upload_failed",
                error=str(e),
                size_bytes=len(content),
            )
            raise

    async def get_content_metadata(
        self, content_id: str, object_id: str
    ) -> dict[str, Any]:
        """
        Get metadata for a content item.

        Args:
            content_id: Content identifier.
            object_id: Object identifier.

        Returns:
            Content metadata dictionary.

        Raises:
            httpx.HTTPError: If API request fails.
        """
        client = await self._get_client()

        url = f"{self.base_url}/api/v1/content/{content_id}/objects/{object_id}"

        logger.info("fetching_content_metadata", content_id=content_id, object_id=object_id)

        try:
            response = await client.get(url)
            response.raise_for_status()

            return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "content_metadata_fetch_failed",
                error=str(e),
                content_id=content_id,
            )
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("simple_content_client_closed")

    async def __aenter__(self) -> "SimpleContentClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: any, exc_val: any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
