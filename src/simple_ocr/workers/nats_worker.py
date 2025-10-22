"""NATS worker for processing OCR jobs asynchronously."""

import asyncio
import json
import signal
from typing import Any, Optional

import structlog
from cloudevents.http import from_json
from nats.aio.client import Client as NATS
from nats.js.api import StreamConfig
from nats.js.client import JetStreamContext

from simple_ocr.adapters.content_client import SimpleContentClient
from simple_ocr.adapters.factory import OCREngineFactory
from simple_ocr.config import Settings, get_settings
from simple_ocr.models.job import OCRJob, OCRJobStatus
from simple_ocr.services.ocr_service import OCRService

logger = structlog.get_logger(__name__)


class NATSWorker:
    """Worker that processes OCR jobs from NATS JetStream."""

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the NATS worker.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self.nats_client: Optional[NATS] = None
        self.jetstream: Optional[JetStreamContext] = None
        self.ocr_service: Optional[OCRService] = None
        self.running = False
        self._shutdown_event = asyncio.Event()

        logger.info(
            "nats_worker_initialized",
            nats_url=settings.nats_url,
            subject=settings.nats_subject,
            stream=settings.nats_stream,
        )

    async def start(self) -> None:
        """Start the NATS worker and begin processing jobs."""
        logger.info("starting_nats_worker")

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        try:
            # Connect to NATS
            await self._connect_nats()

            # Setup JetStream
            await self._setup_jetstream()

            # Initialize OCR service
            await self._initialize_ocr_service()

            # Start consuming messages
            self.running = True
            await self._consume_messages()

        except Exception as e:
            logger.error("worker_startup_failed", error=str(e))
            raise
        finally:
            await self.cleanup()

    async def _connect_nats(self) -> None:
        """Connect to NATS server."""
        logger.info("connecting_to_nats", url=self.settings.nats_url)

        self.nats_client = NATS()
        await self.nats_client.connect(servers=[self.settings.nats_url])

        logger.info("nats_connected")

    async def _setup_jetstream(self) -> None:
        """Setup JetStream stream and consumer."""
        if not self.nats_client:
            raise RuntimeError("NATS client not connected")

        self.jetstream = self.nats_client.jetstream()

        # Create or update stream
        try:
            stream_config = StreamConfig(
                name=self.settings.nats_stream,
                subjects=[f"{self.settings.nats_subject}.>"],
            )

            await self.jetstream.add_stream(config=stream_config)
            logger.info("jetstream_stream_created", stream=self.settings.nats_stream)

        except Exception as e:
            # Stream might already exist
            logger.info(
                "jetstream_stream_exists",
                stream=self.settings.nats_stream,
                error=str(e),
            )

    async def _initialize_ocr_service(self) -> None:
        """Initialize the OCR processing service."""
        logger.info("initializing_ocr_service")

        # Create OCR engine
        ocr_engine = OCREngineFactory.create_from_settings(self.settings)

        # Create content client
        content_client = SimpleContentClient(
            base_url=self.settings.content_api_url,
            timeout=self.settings.content_api_timeout,
            max_retries=self.settings.content_api_max_retries,
        )

        # Create OCR service
        self.ocr_service = OCRService(
            ocr_engine=ocr_engine,
            content_client=content_client,
            temp_dir=self.settings.temp_dir,
            cleanup_temp_files=self.settings.cleanup_temp_files,
        )

        logger.info("ocr_service_initialized")

    async def _consume_messages(self) -> None:
        """Consume and process messages from NATS."""
        if not self.jetstream or not self.ocr_service:
            raise RuntimeError("JetStream or OCR service not initialized")

        logger.info(
            "starting_message_consumption",
            subject=self.settings.nats_subject,
            consumer=self.settings.nats_consumer,
        )

        # Create pull subscription
        psub = await self.jetstream.pull_subscribe(
            subject=self.settings.nats_subject,
            durable=self.settings.nats_consumer,
        )

        logger.info("pull_subscription_created", consumer=self.settings.nats_consumer)

        # Process messages
        while self.running:
            try:
                # Fetch messages (with timeout)
                msgs = await psub.fetch(
                    batch=self.settings.nats_max_concurrent,
                    timeout=5.0,  # 5 second timeout
                )

                if not msgs:
                    await asyncio.sleep(0.1)
                    continue

                # Process messages concurrently
                tasks = [self._process_message(msg) for msg in msgs]
                await asyncio.gather(*tasks, return_exceptions=True)

            except TimeoutError:
                # No messages available, continue
                continue

            except Exception as e:
                logger.error("message_consumption_error", error=str(e))
                await asyncio.sleep(1)  # Brief pause before retry

        logger.info("message_consumption_stopped")

    async def _process_message(self, msg: Any) -> None:
        """
        Process a single NATS message.

        Args:
            msg: NATS message containing OCR job.
        """
        try:
            # Parse CloudEvent
            event = from_json(msg.data)

            logger.info(
                "processing_message",
                event_type=event.get_type(),
                event_id=event.get("id"),
            )

            # Extract job data
            job_data = event.get_data()
            if not job_data:
                logger.warning("empty_job_data", event_id=event.get("id"))
                await msg.ack()
                return

            # Parse OCR job
            job = OCRJob(**job_data)

            logger.info(
                "processing_ocr_job",
                job_id=job.job_id,
                content_id=job.content_id,
            )

            # Process the job
            result = await self.ocr_service.process_job(job)

            # Publish result event
            await self._publish_result(result)

            # Acknowledge message
            await msg.ack()

            logger.info(
                "message_processed",
                job_id=job.job_id,
                status=result.status,
                processing_time_ms=result.processing_time_ms,
            )

        except Exception as e:
            logger.error(
                "message_processing_failed",
                error=str(e),
                error_type=type(e).__name__,
            )

            # Negative acknowledge (will be redelivered)
            try:
                await msg.nak()
            except Exception as nak_error:
                logger.error("nak_failed", error=str(nak_error))

    async def _publish_result(self, result: Any) -> None:
        """
        Publish OCR result as CloudEvent.

        Args:
            result: OCR processing result.
        """
        if not self.nats_client:
            logger.warning("cannot_publish_result_nats_not_connected")
            return

        try:
            # Create CloudEvent for result
            from cloudevents.http import CloudEvent

            event = CloudEvent(
                {
                    "type": "com.simple-ocr.job.completed"
                    if result.status == OCRJobStatus.COMPLETED
                    else "com.simple-ocr.job.failed",
                    "source": "simple-ocr-worker",
                    "subject": result.job_id,
                },
                result.model_dump(),
            )

            # Publish to NATS
            subject = f"{self.settings.nats_subject}.results"
            await self.nats_client.publish(
                subject, json.dumps(event.get_data()).encode("utf-8")
            )

            logger.info(
                "result_published",
                job_id=result.job_id,
                status=result.status,
                subject=subject,
            )

        except Exception as e:
            logger.error("result_publish_failed", error=str(e), job_id=result.job_id)

    async def shutdown(self) -> None:
        """Gracefully shutdown the worker."""
        logger.info("shutting_down_worker")

        self.running = False
        self._shutdown_event.set()

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("cleaning_up_worker_resources")

        if self.ocr_service:
            await self.ocr_service.cleanup()

        if self.nats_client:
            await self.nats_client.close()
            logger.info("nats_connection_closed")

        logger.info("worker_cleanup_completed")


async def main() -> None:
    """Main entry point for the NATS worker."""
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging_level=20),  # INFO
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logger.info("starting_simple_ocr_nats_worker")

    # Load settings
    settings = get_settings()

    # Create and start worker
    worker = NATSWorker(settings)

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt_received")
    except Exception as e:
        logger.error("worker_failed", error=str(e))
        raise
    finally:
        await worker.cleanup()

    logger.info("worker_stopped")


if __name__ == "__main__":
    asyncio.run(main())
