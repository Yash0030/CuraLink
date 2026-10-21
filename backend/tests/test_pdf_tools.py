"""Unit tests for Tool 4: read_pdf_text."""

import pytest
from app.tools.pdf_tools import read_pdf_text
from app.synthetic.generate_samples import create_a1_report, create_fake_html_pdf

def test_read_valid_pdf():
    valid_pdf_bytes = create_a1_report(patient_name="Aarav Roy")
    res = read_pdf_text(valid_pdf_bytes)
    assert res["readable"] is True
    assert "Aarav Roy" in res["text"]
    assert res["num_pages"] >= 1

def test_read_empty_file_returns_unreadable():
    res = read_pdf_text(b"")
    assert res["readable"] is False
    assert "empty" in res["reason"].lower()

def test_read_non_pdf_fails_magic_header():
    fake_html = create_fake_html_pdf()
    res = read_pdf_text(fake_html)
    assert res["readable"] is False
    assert "not_pdf" in res["reason"]
