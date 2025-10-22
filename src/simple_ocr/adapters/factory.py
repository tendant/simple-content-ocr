"""Factory for creating OCR engine instances."""

from typing import Any, Dict

import structlog

from simple_ocr.adapters.base import BaseOCREngine
from simple_ocr.adapters.deepseek_engine import DeepSeekOCREngine
from simple_ocr.adapters.mock_engine import MockOCREngine
from simple_ocr.config import Settings

logger = structlog.get_logger(__name__)


class OCREngineFactory:
    """Factory for creating OCR engine instances based on configuration."""

    # Registry of available engines
    _engines: Dict[str, type[BaseOCREngine]] = {
        "mock": MockOCREngine,
        "deepseek": DeepSeekOCREngine,
    }

    @classmethod
    def create(cls, engine_type: str, config: dict[str, Any]) -> BaseOCREngine:
        """
        Create an OCR engine instance.

        Args:
            engine_type: Type of engine to create (mock, deepseek, etc.).
            config: Configuration dictionary for the engine.

        Returns:
            Initialized OCR engine instance.

        Raises:
            ValueError: If engine type is not supported.
        """
        engine_type = engine_type.lower()

        if engine_type not in cls._engines:
            available = ", ".join(cls._engines.keys())
            raise ValueError(
                f"Unknown OCR engine type: {engine_type}. "
                f"Available engines: {available}"
            )

        engine_class = cls._engines[engine_type]
        logger.info(
            "creating_ocr_engine",
            engine_type=engine_type,
            engine_class=engine_class.__name__,
        )

        return engine_class(config)

    @classmethod
    def create_from_settings(cls, settings: Settings) -> BaseOCREngine:
        """
        Create an OCR engine from application settings.

        Args:
            settings: Application settings object.

        Returns:
            Initialized OCR engine instance.
        """
        engine_type = settings.ocr_engine

        # Build configuration from settings
        config = {
            "model_name": settings.model_name,
            "gpu_memory_utilization": settings.vllm_gpu_memory_utilization,
            "max_model_len": settings.vllm_max_model_len,
            "tensor_parallel_size": settings.vllm_tensor_parallel_size,
        }

        # Add mock-specific configuration if using mock engine
        if engine_type == "mock":
            config.update(
                {
                    "delay_ms": 100,  # Small delay to simulate processing
                    "fail_rate": 0.0,  # No failures by default
                }
            )

        return cls.create(engine_type, config)

    @classmethod
    def register_engine(cls, name: str, engine_class: type[BaseOCREngine]) -> None:
        """
        Register a custom OCR engine.

        This allows extending the factory with custom engines.

        Args:
            name: Name to register the engine under.
            engine_class: OCR engine class (must inherit from BaseOCREngine).

        Raises:
            TypeError: If engine_class doesn't inherit from BaseOCREngine.
        """
        if not issubclass(engine_class, BaseOCREngine):
            raise TypeError(
                f"{engine_class.__name__} must inherit from BaseOCREngine"
            )

        logger.info(
            "registering_custom_ocr_engine",
            name=name,
            engine_class=engine_class.__name__,
        )

        cls._engines[name.lower()] = engine_class

    @classmethod
    def list_engines(cls) -> list[str]:
        """
        List all registered engine types.

        Returns:
            List of registered engine names.
        """
        return list(cls._engines.keys())
