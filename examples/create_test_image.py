"""Create a test image for OCR testing."""

from PIL import Image, ImageDraw, ImageFont

# Create a white background image
width, height = 800, 600
image = Image.new("RGB", (width, height), color="white")
draw = ImageDraw.Draw(image)

# Add some text
text_content = [
    "Simple OCR Test Document",
    "",
    "This is a test image for OCR processing.",
    "It contains multiple lines of text.",
    "",
    "Features:",
    "- Line 1: Basic text recognition",
    "- Line 2: Multi-line support",
    "- Line 3: Various formatting",
    "",
    "The OCR engine should extract all this text",
    "and convert it to markdown format.",
]

# Draw text
y_position = 50
for line in text_content:
    # Use default font (may vary by system)
    draw.text((50, y_position), line, fill="black")
    y_position += 40

# Save the image
output_path = "test_document.png"
image.save(output_path)
print(f"✅ Created test image: {output_path}")
print(f"📊 Size: {width}x{height}")
print(f"🔍 You can now test with: python examples/test_local_file.py {output_path}")
