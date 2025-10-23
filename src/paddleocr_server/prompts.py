"""OCR prompts for different extraction modes."""

from typing import Optional

# Default prompt for general markdown extraction
DEFAULT_OCR_PROMPT = """Extract all text content from this image and format it as markdown.

Requirements:
- Preserve the document structure and hierarchy
- Use proper markdown formatting (headings, lists, tables, etc.)
- For tables, use markdown table syntax
- For mathematical formulas, use LaTeX notation
- Maintain the original text order and layout
- Include all visible text, including headers, footers, and annotations

Output only the markdown content without any explanation or metadata."""


# Alternative prompts for specific document types
RECEIPT_PROMPT = """Extract receipt information as JSON with the following structure:
{
  "merchant": "merchant name",
  "date": "transaction date",
  "currency": "currency code",
  "subtotal": 0.00,
  "tax": 0.00,
  "total": 0.00,
  "items": [
    {"name": "item name", "qty": 1, "price": 0.00}
  ]
}

Only output valid JSON. If a field is not found, use empty string or 0."""


INVOICE_PROMPT = """Extract invoice information as JSON with the following structure:
{
  "invoice_number": "",
  "date": "",
  "due_date": "",
  "vendor": "",
  "customer": "",
  "currency": "",
  "subtotal": 0.00,
  "tax": 0.00,
  "total": 0.00,
  "line_items": [
    {"description": "", "quantity": 1, "unit_price": 0.00, "amount": 0.00}
  ]
}

Only output valid JSON. If a field is not found, use empty string or 0."""


TABLE_PROMPT = """Extract all tables from this image as markdown tables.

Requirements:
- Use proper markdown table syntax with | separators
- Include table headers if present
- Preserve cell alignment
- Handle merged cells by repeating content
- If multiple tables exist, separate them with blank lines

Output only the markdown tables without any explanation."""


FORM_PROMPT = """Extract form fields and their values as JSON with the structure:
{
  "fields": [
    {"label": "field label", "value": "field value"}
  ]
}

Only output valid JSON. Include all visible fields and their corresponding values."""


def get_prompt_for_mode(mode: str) -> str:
    """Get the appropriate prompt based on extraction mode.

    Args:
        mode: Extraction mode (markdown, receipt, invoice, table, form, or custom)

    Returns:
        The prompt string for the specified mode
    """
    prompts = {
        "markdown": DEFAULT_OCR_PROMPT,
        "receipt": RECEIPT_PROMPT,
        "invoice": INVOICE_PROMPT,
        "table": TABLE_PROMPT,
        "form": FORM_PROMPT,
    }
    return prompts.get(mode, DEFAULT_OCR_PROMPT)


def build_user_prompt(system_prompt: Optional[str] = None, mode: str = "markdown") -> str:
    """Build the complete user prompt for OCR.

    Args:
        system_prompt: Custom system prompt from user (overrides mode)
        mode: Extraction mode if no custom system prompt

    Returns:
        The complete prompt string
    """
    if system_prompt:
        return system_prompt
    return get_prompt_for_mode(mode)
