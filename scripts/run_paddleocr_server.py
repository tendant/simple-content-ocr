#!/usr/bin/env python3
"""Standalone launcher for PaddleOCR-VL custom server."""

import argparse
import sys
from pathlib import Path

# Add src to Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))


def main():
    """Run the PaddleOCR-VL server."""
    parser = argparse.ArgumentParser(description="PaddleOCR-VL Custom Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers (keep at 1 for GPU)")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")

    args = parser.parse_args()

    try:
        import uvicorn

        print("=" * 60)
        print("PaddleOCR-VL Custom Inference Server")
        print("=" * 60)
        print(f"Host: {args.host}")
        print(f"Port: {args.port}")
        print(f"Workers: {args.workers}")
        print(f"Log Level: {args.log_level}")
        print("=" * 60)
        print()
        print("Endpoints:")
        print(f"  - Health: http://{args.host}:{args.port}/health")
        print(f"  - Models: http://{args.host}:{args.port}/v1/models")
        print(f"  - Chat: http://{args.host}:{args.port}/v1/chat/completions")
        print("=" * 60)
        print()

        uvicorn.run(
            "paddleocr_server.server:app",
            host=args.host,
            port=args.port,
            workers=args.workers,
            log_level=args.log_level,
            reload=args.reload,
        )
    except ImportError as e:
        print(f"Error: Missing dependency - {e}")
        print()
        print("Please install required dependencies:")
        print("  pip install -r requirements-server.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
