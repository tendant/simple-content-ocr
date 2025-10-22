# Specification: Job Processing

## ADDED Requirements

### Requirement: NATS Job Consumer
The system SHALL consume OCR jobs from NATS using the simple-process job structure.

#### Scenario: Subscribe to job queue
- **WHEN** the worker service starts
- **THEN** it subscribes to NATS subject "simple-process.jobs"
- **AND** uses queue group "ocr-workers" for load distribution
- **AND** multiple workers share the queue group for horizontal scaling

#### Scenario: Job deserialization
- **WHEN** a NATS message is received
- **THEN** the system deserializes CloudEvents envelope
- **AND** extracts job metadata (job_id, content_id, tenant_id, owner_id)
- **AND** validates required fields (job_id, content_id)

#### Scenario: Invalid job rejection
- **WHEN** a malformed job is received (missing fields, invalid JSON)
- **THEN** the system acknowledges the message (remove from queue)
- **AND** publishes failure event with validation error
- **AND** does not retry processing

### Requirement: Job Idempotency
The system SHALL implement idempotent job processing using job_id as idempotency key.

#### Scenario: Duplicate job detection
- **WHEN** a job with duplicate job_id is received
- **THEN** the system checks for existing processing state
- **AND** skips processing if job already completed
- **AND** acknowledges message without reprocessing

#### Scenario: Idempotency across workers
- **WHEN** multiple workers receive duplicate jobs (due to NATS redelivery)
- **THEN** only one worker processes the job
- **AND** other workers detect duplicate via shared state (e.g., database check)
- **AND** duplicate workers acknowledge message and skip

#### Scenario: Idempotency reset
- **WHEN** force reprocessing is requested (force=true in job hints)
- **THEN** idempotency check is bypassed
- **AND** job is reprocessed regardless of previous state
- **AND** previous OCR output is overwritten or versioned

### Requirement: Lifecycle Event Publishing
The system SHALL publish lifecycle events to NATS for job progress tracking and observability.

#### Scenario: Job started event
- **WHEN** OCR processing begins
- **THEN** event is published to "ocr.job.started" subject
- **AND** event includes: job_id, content_id, tenant_id, timestamp, worker_id
- **AND** event follows CloudEvents v1.0 format

#### Scenario: Job progress event
- **WHEN** processing multi-page documents
- **THEN** progress events are published to "ocr.job.progress"
- **AND** events include: job_id, pages_completed, total_pages, percent_complete

#### Scenario: Job completed event
- **WHEN** OCR processing succeeds
- **THEN** event is published to "ocr.job.completed"
- **AND** event includes: job_id, content_id, derived_content_id, processing_time_ms, page_count
- **AND** downstream systems can subscribe to completion events

#### Scenario: Job failed event
- **WHEN** OCR processing fails
- **THEN** event is published to "ocr.job.failed"
- **AND** event includes: job_id, error_type (validation, transient, permanent), error_message, retry_count
- **AND** enables alerting on persistent failures

### Requirement: Job Retry Strategy
The system SHALL implement intelligent retry logic for transient failures with exponential backoff.

#### Scenario: Transient failure retry
- **WHEN** OCR processing fails with transient error (network timeout, temporary service unavailability)
- **THEN** the system re-queues the job with retry metadata
- **AND** increments retry_count in job metadata
- **AND** applies exponential backoff delay (e.g., 1s, 2s, 4s, 8s)

#### Scenario: Maximum retry limit
- **WHEN** retry_count reaches maximum (e.g., 3 retries)
- **THEN** the system marks job as permanently failed
- **AND** publishes final failure event
- **AND** does not re-queue for further retries

#### Scenario: Immediate failure for validation errors
- **WHEN** validation error occurs (unsupported format, missing content)
- **THEN** job is marked as permanently failed immediately
- **AND** no retries are attempted
- **AND** failure event indicates validation error type

### Requirement: Queue Group Load Balancing
The system SHALL distribute jobs across worker instances using NATS queue groups.

#### Scenario: Round-robin distribution
- **WHEN** multiple workers share the same queue group
- **THEN** NATS distributes jobs evenly across workers
- **AND** each job is delivered to exactly one worker
- **AND** enables horizontal scaling by adding worker instances

#### Scenario: Worker failure handling
- **WHEN** a worker crashes during job processing
- **THEN** NATS redelivers unacknowledged message to another worker
- **AND** new worker detects incomplete processing state
- **AND** job is retried from the beginning

#### Scenario: Backpressure handling
- **WHEN** all workers are busy processing jobs
- **THEN** new jobs remain in NATS queue until workers become available
- **AND** queue depth increases (observable via NATS monitoring)
- **AND** workers pull jobs as capacity allows (natural backpressure)

### Requirement: Job Acknowledgment Strategy
The system SHALL acknowledge NATS messages only after successful processing or permanent failure.

#### Scenario: Successful processing acknowledgment
- **WHEN** OCR processing completes successfully
- **AND** derived content is uploaded to simple-content
- **THEN** the worker acknowledges the NATS message
- **AND** message is removed from queue

#### Scenario: Permanent failure acknowledgment
- **WHEN** job fails with permanent error (validation, corrupted file)
- **THEN** the worker acknowledges the NATS message (remove from queue)
- **AND** publishes failure event for observability
- **AND** prevents infinite retry loop

#### Scenario: Transient failure negative acknowledgment
- **WHEN** job fails with transient error (network timeout)
- **AND** retry limit not reached
- **THEN** the worker negatively acknowledges the message (nack)
- **AND** NATS redelivers message with delay for retry

#### Scenario: Shutdown during processing
- **WHEN** worker receives shutdown signal during job processing
- **THEN** the message is not acknowledged
- **AND** NATS redelivers message to another worker after timeout
- **AND** ensures job is not lost

### Requirement: Job Prioritization
The system SHALL support job priority levels for processing order.

#### Scenario: High-priority job processing
- **WHEN** a job includes priority="high" in hints
- **THEN** the job is placed in high-priority queue or subject
- **AND** workers consume high-priority jobs first
- **AND** ensures critical content is processed quickly

#### Scenario: Default priority
- **WHEN** a job does not specify priority
- **THEN** default priority is "normal"
- **AND** jobs are processed in FIFO order within priority level

#### Scenario: Low-priority batch jobs
- **WHEN** backfill jobs are submitted with priority="low"
- **THEN** low-priority jobs are processed only when high/normal queues are empty
- **AND** prevents backfill from impacting real-time processing

### Requirement: Job Timeout Enforcement
The system SHALL enforce per-job timeouts to prevent resource exhaustion from stuck jobs.

#### Scenario: Timeout from job hints
- **WHEN** a job specifies timeout_seconds in hints
- **THEN** the worker enforces the specified timeout
- **AND** cancels processing if timeout is exceeded
- **AND** publishes failure event with "timeout" error type

#### Scenario: Default timeout
- **WHEN** a job does not specify timeout
- **THEN** default timeout of 30 seconds is applied
- **AND** timeout applies to OCR inference (per page for multi-page docs)

#### Scenario: Timeout cancellation
- **WHEN** timeout is exceeded during OCR processing
- **THEN** HTTP request to OCR engine is cancelled
- **AND** temporary files are cleaned up
- **AND** job is marked as failed with timeout error

### Requirement: Job Filtering by Hints
The system SHALL process job hints for behavior customization.

#### Scenario: Resolution hint
- **WHEN** job includes hint "resolution=1024"
- **THEN** OCR engine is configured to use 1024x1024 resolution
- **AND** overrides default resolution (640x640)

#### Scenario: Force reprocessing hint
- **WHEN** job includes hint "force=true"
- **THEN** existing OCR output is ignored
- **AND** content is reprocessed regardless of existing derived content

#### Scenario: Output format hint
- **WHEN** job includes hint "output_format=markdown"
- **THEN** markdown format is used (default)
- **AND** enables future support for additional formats (hOCR, JSON) without breaking changes

#### Scenario: Unknown hint handling
- **WHEN** job includes unrecognized hints
- **THEN** unknown hints are logged but do not cause job failure
- **AND** enables forward compatibility with new hint types

### Requirement: NATS Connection Management
The system SHALL manage NATS connection lifecycle with reconnection logic.

#### Scenario: Initial connection
- **WHEN** worker service starts
- **THEN** it connects to NATS server using configured URL
- **AND** retries connection with exponential backoff if initial connection fails
- **AND** fails service startup after maximum connection attempts

#### Scenario: Connection loss handling
- **WHEN** NATS connection is lost during operation
- **THEN** the NATS client automatically attempts reconnection
- **AND** worker pauses job consumption until connection is restored
- **AND** in-flight jobs are re-queued by NATS after timeout

#### Scenario: Graceful disconnect
- **WHEN** worker receives shutdown signal
- **THEN** it stops accepting new jobs
- **AND** drains in-flight messages (waits for current job completion)
- **AND** closes NATS connection cleanly

### Requirement: Job Result Structure
The system SHALL produce structured job results following simple-process conventions.

#### Scenario: Successful result
- **WHEN** OCR processing succeeds
- **THEN** result includes: job_id, status="completed", derived_content_id, processing_time_ms
- **AND** result includes metadata: page_count, ocr_engine, source_format

#### Scenario: Failed result
- **WHEN** OCR processing fails
- **THEN** result includes: job_id, status="failed", error_type, error_message
- **AND** result includes debug info: retry_count, processing_time_ms, worker_id

#### Scenario: CloudEvents envelope
- **WHEN** publishing job results
- **THEN** results are wrapped in CloudEvents v1.0 envelope
- **AND** envelope includes: id, source, type, specversion=1.0, time, datacontenttype=application/json

### Requirement: Dead Letter Queue
The system SHALL route permanently failed jobs to a dead letter queue for manual review.

#### Scenario: Permanent failure routing
- **WHEN** a job fails permanently (validation error, max retries exceeded)
- **THEN** the job is published to "ocr.dlq" subject
- **AND** includes full job context and error details
- **AND** enables manual investigation and reprocessing

#### Scenario: DLQ monitoring
- **WHEN** jobs accumulate in dead letter queue
- **THEN** ops team is alerted (via monitoring system)
- **AND** DLQ messages are retained for analysis
- **AND** can be replayed after fixing underlying issues

#### Scenario: DLQ replay
- **WHEN** DLQ messages need reprocessing
- **THEN** jobs can be republished to main queue with force=true hint
- **AND** idempotency keys are preserved
- **AND** tracks reprocessing attempts in metadata
