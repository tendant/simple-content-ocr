# Specification: OCR Service

## ADDED Requirements

### Requirement: Document-to-Markdown Conversion
The system SHALL convert visual documents (images, PDFs, office documents) to markdown format preserving layout, structure, and formatting.

#### Scenario: Image OCR conversion
- **WHEN** an image file (PNG, JPEG, TIFF, GIF, BMP, WebP) is submitted for OCR
- **THEN** the system returns markdown text with preserved structure
- **AND** the markdown includes headings, lists, tables, and formatting as detected in the image

#### Scenario: Multi-page PDF conversion
- **WHEN** a multi-page PDF is submitted for OCR
- **THEN** the system processes each page sequentially
- **AND** concatenates page markdown with page separators
- **AND** preserves layout and structure across pages

#### Scenario: Office document conversion
- **WHEN** an office document (DOCX, PPTX, XLSX) is submitted for OCR
- **THEN** the system extracts embedded images and text content
- **AND** converts to markdown preserving document structure
- **AND** includes text from slides, cells, and document body

### Requirement: Automatic Language Detection
The system SHALL automatically detect document language without explicit configuration.

#### Scenario: Multi-language document
- **WHEN** a document contains text in multiple languages
- **THEN** the OCR engine automatically detects and processes all languages
- **AND** produces correct markdown output regardless of language mix

#### Scenario: Non-Latin scripts
- **WHEN** a document contains non-Latin scripts (Chinese, Arabic, Cyrillic, etc.)
- **THEN** the system correctly identifies and transcribes the text
- **AND** outputs UTF-8 encoded markdown with proper character representation

### Requirement: Pluggable OCR Engine
The system SHALL support pluggable OCR engine implementations via a defined interface.

#### Scenario: DeepSeek-OCR engine
- **WHEN** DeepSeek-OCR engine is configured
- **THEN** the system uses vLLM HTTP API for inference
- **AND** passes images with configurable resolution modes (512, 640, 1024, 1280, dynamic)
- **AND** receives markdown output with layout preservation

#### Scenario: Engine fallback
- **WHEN** the primary OCR engine fails or is unavailable
- **THEN** the system can attempt an alternate engine if configured
- **AND** logs engine selection for observability

#### Scenario: Mock engine for testing
- **WHEN** running in test mode
- **THEN** a mock OCR engine returns predefined markdown without GPU requirements
- **AND** enables testing without infrastructure dependencies

### Requirement: Format Validation and Preprocessing
The system SHALL validate input formats and preprocess documents before OCR processing.

#### Scenario: Unsupported format rejection
- **WHEN** an unsupported file format is submitted
- **THEN** the system rejects the job with a validation error
- **AND** provides clear error message indicating supported formats
- **AND** does not retry the job (permanent error)

#### Scenario: Image preprocessing
- **WHEN** an image file is submitted
- **THEN** the system validates image dimensions and format
- **AND** normalizes to supported format if needed (convert to JPEG/PNG)
- **AND** passes directly to OCR engine

#### Scenario: PDF preprocessing
- **WHEN** a PDF file is submitted
- **THEN** the system converts each page to an image using pdftoppm
- **AND** stores temporary images for OCR processing
- **AND** cleans up temporary files after processing

#### Scenario: Office document preprocessing
- **WHEN** an office document is submitted (DOCX, PPTX, XLSX)
- **THEN** the system converts to PDF using LibreOffice headless mode
- **AND** processes the resulting PDF through the PDF pipeline
- **AND** cleans up intermediate files

### Requirement: Processing Status Tracking
The system SHALL track OCR job status throughout the processing lifecycle.

#### Scenario: Job status progression
- **WHEN** a job is received
- **THEN** status is set to "pending"
- **WHEN** processing begins
- **THEN** status updates to "processing"
- **WHEN** OCR completes successfully
- **THEN** status updates to "completed"
- **WHEN** processing fails
- **THEN** status updates to "failed" with error details

#### Scenario: Status queryability
- **WHEN** a client queries job status by job_id
- **THEN** the system returns current status, progress percentage, and timestamps
- **AND** includes error messages if status is "failed"

### Requirement: Error Handling and Classification
The system SHALL classify errors as validation, transient, or permanent and handle appropriately.

#### Scenario: Validation error
- **WHEN** input validation fails (unsupported format, missing content_id, etc.)
- **THEN** the system marks the job as permanently failed
- **AND** does not retry the job
- **AND** publishes failure event with error category "validation"

#### Scenario: Transient error
- **WHEN** a transient failure occurs (network timeout, temporary OCR service unavailability)
- **THEN** the system marks the job for retry
- **AND** uses exponential backoff for retry attempts
- **AND** limits maximum retry attempts (e.g., 3 retries)

#### Scenario: Permanent error
- **WHEN** a permanent failure occurs (corrupted file, OCR engine crash)
- **THEN** the system marks the job as permanently failed
- **AND** does not retry the job
- **AND** logs detailed error for troubleshooting

### Requirement: Timeout Configuration
The system SHALL enforce configurable timeouts for OCR processing to prevent resource exhaustion.

#### Scenario: Default timeout
- **WHEN** no timeout is specified in job configuration
- **THEN** the system applies a 30-second default timeout per OCR request
- **AND** fails the job if timeout is exceeded

#### Scenario: Custom timeout
- **WHEN** a job specifies a custom timeout value
- **THEN** the system uses the provided timeout (within allowed bounds)
- **AND** rejects timeouts exceeding maximum allowed value (e.g., 300 seconds)

#### Scenario: Multi-page timeout calculation
- **WHEN** processing a multi-page PDF
- **THEN** timeout applies per page, not to total document
- **AND** total processing time may exceed single timeout for large documents

### Requirement: Metadata Enrichment
The system SHALL capture and store metadata about OCR processing for observability and analytics.

#### Scenario: Processing metadata
- **WHEN** OCR processing completes successfully
- **THEN** metadata includes: ocr_engine name and version, source_format, processing_time_ms, page_count
- **AND** metadata includes: model_config (resolution, mode), timestamp

#### Scenario: Error metadata
- **WHEN** OCR processing fails
- **THEN** metadata includes: error_type (validation, transient, permanent), error_message, retry_count
- **AND** metadata enables troubleshooting and failure analysis

### Requirement: Idempotent Processing
The system SHALL support idempotent job processing to safely handle retries and reprocessing.

#### Scenario: Duplicate job detection
- **WHEN** a job with the same job_id is received multiple times
- **THEN** the system processes only the first occurrence
- **AND** subsequent occurrences are acknowledged but not reprocessed

#### Scenario: Reprocessing existing content
- **WHEN** a job is submitted for content that already has OCR output
- **THEN** the system checks for existing derived content
- **AND** skips processing if OCR already exists (unless force flag is set)
- **AND** returns existing OCR result

### Requirement: Graceful Shutdown
The system SHALL support graceful shutdown to prevent job loss and corruption.

#### Scenario: Worker shutdown
- **WHEN** a shutdown signal is received (SIGTERM, SIGINT)
- **THEN** the worker stops accepting new jobs
- **AND** completes the current job if processing
- **AND** re-queues incomplete jobs for other workers
- **AND** closes connections cleanly (NATS, HTTP clients)

#### Scenario: In-progress job handling
- **WHEN** shutdown occurs during job processing
- **THEN** the system completes OCR request if possible (within shutdown timeout)
- **OR** marks job as failed with "interrupted" status for retry by another worker

### Requirement: Configuration Management
The system SHALL support configuration via environment variables and configuration files.

#### Scenario: Environment variable configuration
- **WHEN** the service starts
- **THEN** configuration is loaded from environment variables
- **AND** includes: NATS_URL, OCR_ENGINE_URL, SIMPLE_CONTENT_URL, QUEUE_GROUP, JOB_SUBJECT
- **AND** validates required configuration and fails fast if missing

#### Scenario: Configuration file override
- **WHEN** a .env file exists in the working directory
- **THEN** configuration is loaded from the file
- **AND** environment variables override file values
- **AND** enables local development without setting env vars

#### Scenario: Default values
- **WHEN** optional configuration is not provided
- **THEN** sensible defaults are applied
- **AND** defaults include: timeout=30s, max_retries=3, resolution=640, queue_group="ocr-workers"
