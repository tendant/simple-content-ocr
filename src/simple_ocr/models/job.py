"""OCR job data models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OCRJobStatus(str, Enum):
    """OCR job status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OCRJob(BaseModel):
    """OCR job request model."""

    job_id: str = Field(..., description="Unique job identifier")
    content_id: str = Field(..., description="Content ID from simple-content")
    object_id: str = Field(..., description="Object ID from simple-content")
    owner_id: Optional[str] = Field(None, description="Owner ID for multi-tenancy")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenancy")
    source_url: str = Field(..., description="Presigned URL to source content")
    mime_type: str = Field(..., description="MIME type of source content")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, str] = Field(default_factory=dict)


class OCRResult(BaseModel):
    """OCR processing result model."""

    job_id: str = Field(..., description="Job identifier")
    status: OCRJobStatus = Field(..., description="Processing status")
    markdown_content: Optional[str] = Field(None, description="Extracted markdown content")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    page_count: Optional[int] = Field(None, description="Number of pages processed")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    metadata: dict[str, str] = Field(default_factory=dict)
