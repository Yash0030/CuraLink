"""Tool 4: read_pdf_text

Reads staged PDF bytes, validates PDF signature (%PDF), extracts text using pypdf,
and handles corrupt, non-PDF, or empty text files with explicit reasons.
"""

import io
from typing import Dict, Any, Tuple
import pypdf

def read_pdf_text(file_bytes: bytes) -> Dict[str, Any]:
    """Inspects file bytes, verifies %PDF magic bytes, extracts text, and returns status.

    Returns:
        dict: {
            "readable": bool,
            "reason": str,
            "text": str,
            "num_pages": int
        }
    """
    if not file_bytes:
        return {
            "readable": False,
            "reason": "File is empty (0 bytes)",
            "text": "",
            "num_pages": 0
        }

    # Verify %PDF header
    if not file_bytes.startswith(b"%PDF"):
        return {
            "readable": False,
            "reason": "File does not start with %PDF magic header (code: not_pdf)",
            "text": "",
            "num_pages": 0
        }

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        num_pages = len(reader.pages)
        if num_pages == 0:
            return {
                "readable": False,
                "reason": "PDF has 0 pages",
                "text": "",
                "num_pages": 0
            }

        extracted_texts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            extracted_texts.append(page_text)

        full_text = "\n".join(extracted_texts).strip()
        if not full_text:
            return {
                "readable": False,
                "reason": "PDF contains no extractable text",
                "text": "",
                "num_pages": num_pages
            }

        return {
            "readable": True,
            "reason": "Successfully parsed and extracted text",
            "text": full_text,
            "num_pages": num_pages
        }

    except Exception as e:
        return {
            "readable": False,
            "reason": f"PDF parse error: {str(e)}",
            "text": "",
            "num_pages": 0
        }
