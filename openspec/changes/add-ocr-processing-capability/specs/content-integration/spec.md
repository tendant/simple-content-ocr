# Specification: Content Integration

## ADDED Requirements

### Requirement: Source Content Download
The system SHALL download source content from simple-content using presigned URLs for OCR processing.

#### Scenario: Download by content_id
- **WHEN** a job specifies a content_id
- **THEN** the system retrieves content metadata from simple-content
- **AND** obtains a presigned download URL
- **AND** downloads the content to local temporary storage
- **AND** validates downloaded content matches expected size and checksum

#### Scenario: Download error handling
- **WHEN** content download fails (network error, 404, etc.)
- **THEN** the system classifies as transient error and retries
- **AND** logs error details with content_id for troubleshooting
- **AND** fails job permanently after max retries exceeded

#### Scenario: Large file streaming
- **WHEN** downloading large files (multi-page PDFs, high-res images)
- **THEN** the system streams content to disk instead of buffering in memory
- **AND** validates content during download (checksum verification)
- **AND** cleans up partial downloads on failure

### Requirement: Derived Content Upload
The system SHALL upload OCR markdown output as derived content linked to the source file.

#### Scenario: Upload OCR result
- **WHEN** OCR processing completes successfully
- **THEN** the system creates derived content with type "ocr-markdown"
- **AND** uploads markdown as a text file (.md extension)
- **AND** links derived content to source via parent content_id
- **AND** sets appropriate MIME type (text/markdown)

#### Scenario: Metadata attachment
- **WHEN** uploading OCR derived content
- **THEN** the system attaches metadata including:
  - derived_type: "ocr-markdown"
  - ocr_engine: engine name and version (e.g., "deepseek-ocr-v1")
  - source_format: original file format (pdf, image, docx, pptx, xlsx)
  - page_count: number of pages processed
  - processing_time_ms: total processing duration
  - model_config: OCR engine configuration (resolution, mode)
- **AND** metadata is queryable via simple-content API

#### Scenario: Upload error handling
- **WHEN** derived content upload fails
- **THEN** the system retries with exponential backoff
- **AND** preserves OCR output locally for manual recovery
- **AND** publishes failure event with error details

### Requirement: Storage Backend Compatibility
The system SHALL work with all simple-content storage backends without backend-specific code.

#### Scenario: Filesystem storage
- **WHEN** simple-content is configured with filesystem storage
- **THEN** the OCR service downloads and uploads via presigned file:// URLs
- **AND** operates without knowledge of filesystem paths

#### Scenario: S3-compatible storage
- **WHEN** simple-content is configured with S3 or MinIO
- **THEN** the OCR service downloads and uploads via presigned HTTPS URLs
- **AND** supports large files via multipart upload
- **AND** operates without AWS credentials (uses presigned URLs)

#### Scenario: Mixed storage backends
- **WHEN** simple-content uses different backends for source and derived content
- **THEN** the OCR service handles both transparently
- **AND** relies on simple-content for storage routing

### Requirement: Content Status Updates
The system SHALL update content processing status in simple-content throughout the OCR lifecycle.

#### Scenario: Processing status
- **WHEN** OCR processing begins
- **THEN** content status is updated to "processing"
- **AND** status includes job_id for tracking

#### Scenario: Completion status
- **WHEN** OCR processing completes successfully
- **THEN** content status is updated to "completed"
- **AND** status includes derived content reference (derived_content_id)
- **AND** timestamp reflects completion time

#### Scenario: Failure status
- **WHEN** OCR processing fails permanently
- **THEN** content status is updated to "failed"
- **AND** status includes error message and error_type
- **AND** enables querying failed content for troubleshooting

### Requirement: Multi-Tenant Isolation
The system SHALL respect tenant and owner isolation enforced by simple-content.

#### Scenario: Tenant-scoped access
- **WHEN** a job includes tenant_id metadata
- **THEN** the system passes tenant_id to simple-content API calls
- **AND** simple-content enforces tenant isolation for download and upload
- **AND** derived content inherits tenant_id from source content

#### Scenario: Owner-scoped access
- **WHEN** a job includes owner_id metadata
- **THEN** derived content is associated with the specified owner
- **AND** access control follows simple-content policies

#### Scenario: Cross-tenant protection
- **WHEN** attempting to access content from different tenant
- **THEN** simple-content rejects the request with 403 Forbidden
- **AND** OCR service logs authorization error and fails job

### Requirement: Derived Content Versioning
The system SHALL support versioning of OCR output for the same source content.

#### Scenario: Model upgrade reprocessing
- **WHEN** a new OCR model version is deployed
- **AND** reprocessing is triggered for existing content
- **THEN** new derived content is created with updated model version in metadata
- **AND** previous OCR output remains accessible (not overwritten)

#### Scenario: Query latest OCR version
- **WHEN** querying for OCR output of a source file
- **THEN** simple-content returns the most recent version by default
- **AND** older versions are retrievable via version-specific queries

### Requirement: Batch Content Enumeration
The system SHALL support enumerating content for batch OCR processing via backfill utility.

#### Scenario: Filter by MIME type
- **WHEN** enumerating content for OCR backfill
- **THEN** the system queries simple-content for specific MIME types
- **AND** MIME types include: image/*, application/pdf, application/vnd.openxmlformats-officedocument.*
- **AND** results are paginated for large datasets

#### Scenario: Filter by existing OCR
- **WHEN** enumerating content for backfill
- **THEN** the system can filter for content without existing OCR derived content
- **AND** queries by absence of derived_type="ocr-markdown"
- **AND** avoids reprocessing already OCR'd content

#### Scenario: Filter by tenant and date range
- **WHEN** backfill targets specific tenant or date range
- **THEN** the system applies filters to simple-content queries
- **AND** enables incremental backfill (process recent content first)

### Requirement: Content Lifecycle Events
The system SHALL subscribe to simple-content lifecycle events for trigger-based OCR processing.

#### Scenario: New content upload event
- **WHEN** new content is uploaded to simple-content
- **AND** content MIME type matches OCR-eligible formats
- **THEN** the system automatically submits OCR job (if auto-OCR is enabled)
- **AND** job references content_id and tenant_id from event

#### Scenario: Event filtering
- **WHEN** listening for content events
- **THEN** the system filters for relevant MIME types only
- **AND** ignores events for already-processed content (idempotency)
- **AND** respects tenant-specific OCR policies (some tenants may disable auto-OCR)

### Requirement: Content Validation
The system SHALL validate content properties before OCR processing.

#### Scenario: File size validation
- **WHEN** content exceeds maximum allowed size (e.g., 100MB)
- **THEN** the system rejects the job with validation error
- **AND** error message indicates size limit
- **AND** job is not retried (permanent error)

#### Scenario: Format validation
- **WHEN** content MIME type does not match supported formats
- **THEN** the system rejects the job with validation error
- **AND** error message lists supported formats
- **AND** job is not retried (permanent error)

#### Scenario: Corrupted file detection
- **WHEN** downloaded content is corrupted (checksum mismatch, invalid format)
- **THEN** the system fails the job with permanent error
- **AND** logs corruption details for investigation
- **AND** marks content status as "invalid" in simple-content

### Requirement: Temporary File Management
The system SHALL manage temporary files for preprocessing and cleanup after processing.

#### Scenario: Temporary file creation
- **WHEN** downloading content for OCR
- **THEN** the system stores in a unique temporary directory (per job_id)
- **AND** directory includes source file and intermediate conversions

#### Scenario: Cleanup on success
- **WHEN** OCR processing completes successfully
- **THEN** all temporary files are deleted
- **AND** only final markdown output is retained (uploaded to simple-content)

#### Scenario: Cleanup on failure
- **WHEN** OCR processing fails
- **THEN** temporary files are deleted after error logging
- **OR** preserved for troubleshooting if configured (debug mode)
- **AND** cleanup occurs even if worker crashes (background cleanup job)

#### Scenario: Disk space management
- **WHEN** temporary storage exceeds threshold (e.g., 80% disk usage)
- **THEN** the system rejects new jobs until space is freed
- **AND** logs warning about disk space exhaustion
- **AND** background cleanup removes orphaned temporary files
