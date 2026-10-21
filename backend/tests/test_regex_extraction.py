"""Unit tests for layout-specific regex metadata extraction."""

import pytest
from datetime import date
from app.agents.extractor import extract_with_regex

def test_a1_table_layout_extraction():
    sample_text = """
    A1 REFERENCE LABORATORIES & DIAGNOSTICS
    Accredited Medical Diagnostics Facility

    Patient Name: Aarav Roy          Patient ID: pt001
    Report ID: A-20260121-001-2     Report Date: 2026-01-21
    Test / Examination: Complete Blood Count (CBC)
    Status: Final / Verified
    """
    res = extract_with_regex(sample_text)
    assert res["name"] == "Aarav Roy"
    assert res["patient_id"] == "pt001"
    assert res["report_id"] == "A-20260121-001-2"
    assert res["date"] == date(2026, 1, 21)
    assert "Complete Blood Count" in res["test"]

def test_cityscan_cards_layout_extraction():
    sample_text = """
    CITYSCAN ADVANCED IMAGING CENTER
    Department of Radiodiagnosis & Imaging

    PATIENT NAME: ROY, AARAV        MRN / Patient ID: pt001
    Scan ID / Report No: B-20260122-004-1   Exam Date: 2026-01-22
    Study / Procedure: Chest X-Ray PA View
    Modality: Digital Radiography
    """
    res = extract_with_regex(sample_text)
    assert res["name"] == "ROY, AARAV"
    assert res["patient_id"] == "pt001"
    assert res["report_id"] == "B-20260122-004-1"
    assert res["date"] == date(2026, 1, 22)
    assert "Chest X-Ray" in res["test"]

def test_vitals_paginated_layout_extraction():
    sample_text = """
    VITALS DIAGNOSTIC LABORATORIES
    Clinical Pathology & Biochemistry Division

    Client / Patient: Aarav Roy     UHID / ID: pt001
    Sample ID / Report Ref: C-20260124-008-3   Collection Date: 2026-01-24
    Test Panel: Comprehensive Lipid Panel
    Specimen: Serum
    """
    res = extract_with_regex(sample_text)
    assert res["name"] == "Aarav Roy"
    assert res["patient_id"] == "pt001"
    assert res["report_id"] == "C-20260124-008-3"
    assert res["date"] == date(2026, 1, 24)
    assert "Lipid Panel" in res["test"]
