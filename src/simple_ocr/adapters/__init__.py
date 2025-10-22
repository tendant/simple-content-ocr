"""Adapters for external services and OCR engines."""

from simple_ocr.adapters.base import BaseOCREngine, OCRError, OCRResponse
from simple_ocr.adapters.deepseek_engine import DeepSeekOCREngine
from simple_ocr.adapters.factory import OCREngineFactory
from simple_ocr.adapters.mock_engine import MockOCREngine

__all__ = [
    "BaseOCREngine",
    "OCRError",
    "OCRResponse",
    "MockOCREngine",
    "DeepSeekOCREngine",
    "OCREngineFactory",
]
