#!/usr/bin/env python3
"""Test script for PaddleOCR-VL custom server.

Verifies that the custom server is running and works correctly with
OpenAI-compatible API endpoints.
"""

import argparse
import base64
import sys
import time
from pathlib import Path

import requests


def check_server_health(base_url: str) -> bool:
    """Check if server is healthy."""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✓ Server is healthy")
            print(f"  - Model loaded: {health['model_loaded']}")
            print(f"  - Device: {health['device']}")
            if health.get("memory_used_mb"):
                print(f"  - Memory: {health['memory_used_mb']:.1f} MB")
            return True
        else:
            print(f"✗ Server health check failed: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"✗ Cannot connect to server: {e}")
        return False


def list_models(base_url: str) -> bool:
    """List available models."""
    try:
        response = requests.get(f"{base_url}/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print(f"✓ Models endpoint working")
            print(f"  - Available models: {len(models['data'])}")
            for model in models["data"]:
                print(f"    • {model['id']}")
            return True
        else:
            print(f"✗ Models endpoint failed: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"✗ Cannot list models: {e}")
        return False


def test_ocr(base_url: str, image_path: str, mode: str = "markdown") -> bool:
    """Test OCR with an image."""
    try:
        # Load and encode image
        with open(image_path, "rb") as f:
            image_data = f.read()
            image_b64 = base64.b64encode(image_data).decode()

        # Prepare prompt based on mode
        if mode == "markdown":
            text_prompt = "Extract all text from this image as markdown"
        elif mode == "receipt":
            text_prompt = "Extract receipt information as JSON"
        elif mode == "table":
            text_prompt = "Extract all tables from this image as markdown tables"
        else:
            text_prompt = "Extract text from this image"

        # Make request
        print(f"✓ Testing OCR ({mode} mode)...")
        start_time = time.time()

        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json={
                "model": "PaddlePaddle/PaddleOCR-VL",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": text_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                            },
                        ],
                    }
                ],
                "max_tokens": 2048,
                "temperature": 0.7,
            },
            timeout=60,
        )

        elapsed = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            extracted_text = result["choices"][0]["message"]["content"]

            print(f"✓ OCR completed in {elapsed:.1f}s")
            print(f"  - Prompt tokens: {result['usage']['prompt_tokens']}")
            print(f"  - Completion tokens: {result['usage']['completion_tokens']}")
            print(f"  - Total tokens: {result['usage']['total_tokens']}")
            print(f"\nExtracted content:")
            print("=" * 60)
            print(extracted_text[:500])
            if len(extracted_text) > 500:
                print(f"... ({len(extracted_text) - 500} more characters)")
            print("=" * 60)
            return True
        else:
            print(f"✗ OCR failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False

    except requests.RequestException as e:
        print(f"✗ OCR request failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all tests."""
    parser = argparse.ArgumentParser(description="Test PaddleOCR-VL custom server")
    parser.add_argument(
        "--url",
        default="http://localhost:8001",
        help="Server base URL (default: http://localhost:8001)",
    )
    parser.add_argument(
        "--image",
        help="Path to test image (optional, creates one if not provided)",
    )
    parser.add_argument(
        "--mode",
        choices=["markdown", "receipt", "table"],
        default="markdown",
        help="OCR extraction mode",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("PaddleOCR-VL Custom Server Test")
    print("=" * 60)
    print(f"Server URL: {args.url}")
    print(f"Mode: {args.mode}")
    print("=" * 60)
    print()

    # Test 1: Health check
    print("1. Health Check")
    if not check_server_health(args.url):
        print("\n✗ Server is not running or not healthy")
        print("\nTo start the server:")
        print("  python scripts/run_paddleocr_server.py")
        sys.exit(1)
    print()

    # Test 2: List models
    print("2. List Models")
    if not list_models(args.url):
        sys.exit(1)
    print()

    # Test 3: OCR
    print("3. OCR Test")
    if args.image:
        image_path = args.image
    else:
        # Try to find or create test image
        test_image = Path("test_document.png")
        if not test_image.exists():
            print("Creating test image...")
            try:
                from PIL import Image, ImageDraw, ImageFont

                img = Image.new("RGB", (800, 600), color="white")
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
                except:
                    font = ImageFont.load_default()

                draw.text((50, 50), "# Test Document", fill="black", font=font)
                draw.text((50, 150), "This is a test document", fill="black")
                draw.text((50, 200), "for OCR extraction.", fill="black")

                img.save(test_image)
                print(f"✓ Created {test_image}")
            except Exception as e:
                print(f"✗ Could not create test image: {e}")
                print("Please provide an image with --image")
                sys.exit(1)

        image_path = str(test_image)

    if not test_ocr(args.url, image_path, args.mode):
        sys.exit(1)
    print()

    print("=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
