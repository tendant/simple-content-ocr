"""Model loading and inference for PaddleOCR-VL."""

import base64
import io
import logging
import re
from typing import Optional

import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor

logger = logging.getLogger(__name__)


class PaddleOCRModel:
    """PaddleOCR-VL model wrapper for inference."""

    def __init__(self, model_name: str = "PaddlePaddle/PaddleOCR-VL"):
        """Initialize the model.

        Args:
            model_name: HuggingFace model name
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32

        logger.info(f"Loading model {model_name} on {self.device} with dtype {self.dtype}")

        # Load processor and model
        self.processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
        self.model = (
            AutoModelForCausalLM.from_pretrained(
                model_name, trust_remote_code=True, torch_dtype=self.dtype
            )
            .to(self.device)
            .eval()
        )

        logger.info("Model loaded successfully")

    def generate(
        self,
        image: Image.Image,
        prompt: str,
        max_new_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Generate text from image using the model.

        Args:
            image: PIL Image to process
            prompt: Text prompt for the model
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        # Prepare inputs
        inputs = self.processor(images=image, text=prompt, return_tensors="pt").to(self.device)

        # Generate
        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
            )

        # Decode output
        generated_text = self.processor.batch_decode(output_ids, skip_special_tokens=True)[0]

        # Extract only the generated part (remove prompt)
        # The model typically repeats the prompt, so we try to extract just the answer
        if prompt in generated_text:
            generated_text = generated_text.split(prompt)[-1].strip()

        return generated_text

    def extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from generated text.

        Args:
            text: Generated text that may contain JSON

        Returns:
            Extracted JSON string or None if not found
        """
        # Try to find JSON block in the text
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            return match.group(0)
        return None

    def get_memory_usage(self) -> Optional[float]:
        """Get current GPU memory usage in MB.

        Returns:
            Memory usage in MB or None if not on CUDA
        """
        if self.device == "cuda":
            return torch.cuda.memory_allocated() / 1024 / 1024
        return None


def load_image_from_base64(base64_str: str) -> Image.Image:
    """Load image from base64 string.

    Args:
        base64_str: Base64-encoded image string (with or without data URI prefix)

    Returns:
        PIL Image
    """
    # Remove data URI prefix if present
    if "base64," in base64_str:
        base64_str = base64_str.split("base64,")[1]

    # Decode base64
    image_data = base64.b64decode(base64_str)
    image = Image.open(io.BytesIO(image_data)).convert("RGB")

    return image


def load_image_from_url(url: str) -> Image.Image:
    """Load image from URL.

    Args:
        url: Image URL (http/https) or base64 data URI

    Returns:
        PIL Image
    """
    if url.startswith("data:image"):
        # Base64-encoded image
        return load_image_from_base64(url)
    elif url.startswith(("http://", "https://")):
        # Remote URL - use requests
        import requests

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        return image
    else:
        # Assume it's a local file path or base64 without prefix
        try:
            return load_image_from_base64(url)
        except Exception:
            # Try as file path
            return Image.open(url).convert("RGB")
