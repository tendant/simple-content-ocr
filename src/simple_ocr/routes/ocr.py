"""FastAPI routes for OCR processing."""

from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from simple_ocr.adapters.content_client import SimpleContentClient
from simple_ocr.adapters.factory import OCREngineFactory
from simple_ocr.config import Settings, get_settings
from simple_ocr.models.job import OCRJob, OCRResult
from simple_ocr.services.ocr_service import OCRService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])


class ProcessRequest(BaseModel):
    """Request model for synchronous OCR processing."""

    job_id: str = Field(..., description="Unique job identifier")
    content_id: str = Field(..., description="Content ID from simple-content")
    object_id: str = Field(..., description="Object ID from simple-content")
    source_url: str = Field(..., description="Presigned URL to source content")
    mime_type: str = Field(..., description="MIME type of source content")
    owner_id: Optional[str] = Field(None, description="Owner ID for multi-tenancy")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenancy")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional metadata")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    ocr_engine: str


class EngineInfo(BaseModel):
    """OCR engine information."""

    available_engines: list[str]
    current_engine: str
    engine_config: dict[str, Any]


def get_ocr_service(settings: Settings = Depends(get_settings)) -> OCRService:
    """
    Dependency for creating OCR service instance.

    Args:
        settings: Application settings.

    Returns:
        Configured OCR service instance.
    """
    ocr_engine = OCREngineFactory.create_from_settings(settings)
    content_client = SimpleContentClient(
        base_url=settings.content_api_url,
        timeout=settings.content_api_timeout,
        max_retries=settings.content_api_max_retries,
    )

    return OCRService(
        ocr_engine=ocr_engine,
        content_client=content_client,
        temp_dir=settings.temp_dir,
        cleanup_temp_files=settings.cleanup_temp_files,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """
    Health check endpoint.

    Returns service status and configuration info.
    """
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        ocr_engine=settings.ocr_engine,
    )


@router.get("/engines", response_model=EngineInfo)
async def get_engine_info(settings: Settings = Depends(get_settings)) -> EngineInfo:
    """
    Get information about available OCR engines.

    Returns:
        Engine information including available and current engines.
    """
    available_engines = OCREngineFactory.list_engines()

    engine_config = {
        "model_name": settings.model_name,
        "gpu_memory_utilization": settings.vllm_gpu_memory_utilization,
        "max_model_len": settings.vllm_max_model_len,
    }

    return EngineInfo(
        available_engines=available_engines,
        current_engine=settings.ocr_engine,
        engine_config=engine_config,
    )


@router.post("/process", response_model=OCRResult, status_code=status.HTTP_200_OK)
async def process_document(
    request: ProcessRequest,
    ocr_service: OCRService = Depends(get_ocr_service),
) -> OCRResult:
    """
    Process a document with OCR synchronously.

    This endpoint processes the document immediately and returns the result.
    For long-running jobs, consider using the NATS-based async worker instead.

    Args:
        request: OCR processing request.
        ocr_service: OCR service instance.

    Returns:
        OCR processing result.

    Raises:
        HTTPException: If processing fails.
    """
    logger.info(
        "processing_ocr_request",
        job_id=request.job_id,
        content_id=request.content_id,
        mime_type=request.mime_type,
    )

    try:
        # Convert request to OCR job
        job = OCRJob(
            job_id=request.job_id,
            content_id=request.content_id,
            object_id=request.object_id,
            owner_id=request.owner_id,
            tenant_id=request.tenant_id,
            source_url=request.source_url,
            mime_type=request.mime_type,
            metadata=request.metadata,
        )

        # Process the job
        result = await ocr_service.process_job(job)

        # Cleanup
        await ocr_service.cleanup()

        logger.info(
            "ocr_request_completed",
            job_id=request.job_id,
            status=result.status,
            processing_time_ms=result.processing_time_ms,
        )

        return result

    except Exception as e:
        logger.error(
            "ocr_request_failed",
            job_id=request.job_id,
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}",
        )
