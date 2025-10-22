# Examples

This directory contains example scripts for testing and using the simple-content-ocr service.

## Quick Start

### 1. Test with Local File (Easiest!)

```bash
# Create a test image
uv run python examples/create_test_image.py

# Process it with OCR
uv run python examples/test_local_file.py test_document.png

# Check the output
cat output/test_document_ocr.md
```

### 2. Basic Usage Examples

```bash
# Demonstrates all OCR engine features
uv run python examples/basic_usage.py
```

## Available Scripts

### `test_local_file.py`

**Test the OCR pipeline with local files** - No infrastructure needed!

```bash
# Process an image
uv run python examples/test_local_file.py path/to/image.png

# Process a PDF
uv run python examples/test_local_file.py document.pdf

# Use DeepSeek engine (requires GPU)
uv run python examples/test_local_file.py image.png --engine deepseek

# Custom output directory
uv run python examples/test_local_file.py image.png --output ./results

# Get help
uv run python examples/test_local_file.py --help
```

**Features:**
- Works with any local image or PDF file
- No NATS or simple-content API required
- Saves markdown output to `./output/` directory
- Shows processing progress and stats
- Perfect for development and testing

### `create_test_image.py`

**Create a sample test image** with text for OCR testing.

```bash
uv run python examples/create_test_image.py
```

Creates `test_document.png` with sample text content.

### `basic_usage.py`

**Demonstrates OCR engine usage** patterns.

```bash
uv run python examples/basic_usage.py
```

Shows:
- Mock engine usage
- Factory patterns
- Custom engine registration
- Context managers

## Testing Different File Types

### Images

```bash
# PNG
uv run python examples/test_local_file.py sample.png

# JPEG
uv run python examples/test_local_file.py photo.jpg

# TIFF
uv run python examples/test_local_file.py scan.tiff
```

### Documents

```bash
# PDF (single page)
uv run python examples/test_local_file.py document.pdf

# PDF (multi-page)
uv run python examples/test_local_file.py report.pdf
```

## Output

All processed files are saved to the `output/` directory by default:

```
output/
├── test_document_ocr.md
├── sample_ocr.md
└── document_ocr.md
```

Each output file contains:
- Extracted markdown text
- Document structure preserved
- Metadata embedded

## Batch Processing

Process multiple files:

```bash
# Process all PNG files in a directory
for file in test_files/*.png; do
    uv run python examples/test_local_file.py "$file"
done

# Process with custom output
for file in *.pdf; do
    uv run python examples/test_local_file.py "$file" --output ./results
done
```

## Next Steps

After local testing:

1. **Test HTTP API** - See `docs/TESTING_GUIDE.md`
2. **Test NATS Worker** - See `docs/PIPELINE.md`
3. **Production Deployment** - See `README.md`

## Troubleshooting

### "File not found"

Use absolute paths or ensure you're in the project root:

```bash
cd /path/to/simple-content-ocr
uv run python examples/test_local_file.py ./test_document.png
```

### "Module not found"

Make sure to use `uv run`:

```bash
# ✅ Correct
uv run python examples/test_local_file.py image.png

# ❌ Wrong (unless venv is activated)
python examples/test_local_file.py image.png
```

### Output directory

The output directory is created automatically, but you can specify a custom one:

```bash
mkdir -p my_output
uv run python examples/test_local_file.py image.png --output my_output
```

## More Information

- **Full Testing Guide**: `../docs/TESTING_GUIDE.md`
- **Pipeline Documentation**: `../docs/PIPELINE.md`
- **OCR Engines**: `../docs/OCR_ENGINES.md`
