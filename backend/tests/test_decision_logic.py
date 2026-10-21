"""Unit tests for decision logic (CheckerAgent, Legitimacy, and Duplicate detection).

Tests:
- TC1: Authentic report with matching patient -> keep.
- TC2: Same report downloaded twice (same ID or SHA-256) -> duplicate.
- TC3: Report with look-alike patient name -> exclude.
- TC4: Login HTML saved as .pdf -> reject (code: not_pdf).
- Discrepancy: Portal date differing from PDF date -> needs_review.
- Cross-run: Second run for same patient treats stored reports as duplicates.
- Possible duplicate: Same lab, test, date with different ID -> possible_duplicate (needs_review).
"""

import pytest
from datetime import date
from app.tools.check_legit import check_file_legit
from app.tools.check_duplicate import check_duplicate

def test_tc1_authentic_report_passes():
    """TC1: Valid report with matching name and in-range date passes legitimacy."""
    res = check_file_legit(
        file_bytes=b"%PDF-1.4 standard medical pdf",
        extracted_name="Aarav Roy",
        extracted_patient_id="pt001",
        extracted_date=date(2026, 1, 21),
        portal_date=date(2026, 1, 21),
        expected_patient_name="Aarav Roy",
        expected_patient_id="pt001",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31)
    )
    assert res["verdict"] == "pass"
    assert res["code"] == "legit_pass"

def test_tc2_same_report_downloaded_twice_is_duplicate():
    """TC2: The same report downloaded twice is detected as duplicate."""
    first_candidate = {
        "x_report_id": "A-20260121-001-2",
        "sha256": "abc123hash",
        "lab": "labA",
        "x_test": "CBC",
        "x_date": date(2026, 1, 21)
    }

    # Second candidate with same ID
    second_candidate = {
        "x_report_id": "A-20260121-001-2",
        "sha256": "abc123hash",
        "lab": "labA",
        "x_test": "CBC",
        "x_date": date(2026, 1, 21)
    }

    dup_res = check_duplicate(
        candidate=second_candidate,
        stored_reports=[],
        earlier_valid_candidates=[first_candidate]
    )
    assert dup_res["verdict"] == "duplicate"
    assert dup_res["matched_by"] in ("report_id", "sha256")

def test_tc3_lookalike_patient_name_excluded():
    """TC3: A report with another patient's name is excluded, including 'Anita Sharma-Rao'."""
    res = check_file_legit(
        file_bytes=b"%PDF-1.4 valid binary content",
        extracted_name="Anita Sharma-Rao",
        extracted_patient_id=None,
        extracted_date=date(2026, 1, 20),
        portal_date=date(2026, 1, 20),
        expected_patient_name="Anita Sharma",
        expected_patient_id=None,
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31)
    )
    assert res["verdict"] == "fail"
    assert res["code"] == "name_mismatch_exclude"

def test_tc4_login_html_saved_as_pdf_rejected():
    """TC4: Login HTML saved as .pdf is rejected with code not_pdf."""
    fake_html_bytes = b"<!DOCTYPE html><html><body><h2>Please Login</h2></body></html>"
    res = check_file_legit(
        file_bytes=fake_html_bytes,
        extracted_name="Aarav Roy",
        extracted_patient_id="pt001",
        extracted_date=date(2026, 1, 21),
        portal_date=date(2026, 1, 21),
        expected_patient_name="Aarav Roy",
        expected_patient_id="pt001",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31)
    )
    assert res["verdict"] == "fail"
    assert res["code"] == "not_pdf"

def test_portal_date_discrepancy_uncertain():
    """A portal date that differs from the date inside the PDF is uncertain."""
    res = check_file_legit(
        file_bytes=b"%PDF-1.4 valid content",
        extracted_name="Aarav Roy",
        extracted_patient_id="pt001",
        extracted_date=date(2026, 1, 21),
        portal_date=date(2026, 1, 15), # Discrepancy!
        expected_patient_name="Aarav Roy",
        expected_patient_id="pt001",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31)
    )
    assert res["verdict"] == "uncertain"
    assert res["code"] == "date_discrepancy"

def test_second_run_treats_stored_reports_as_duplicate():
    """A second run for the same patient treats everything already stored as duplicate."""
    stored_reports = [
        {
            "report_id": "A-20260121-001-2",
            "sha256": "hash_from_run_1",
            "lab": "labA",
            "test_name": "CBC",
            "report_date": date(2026, 1, 21)
        }
    ]

    candidate_run_2 = {
        "x_report_id": "A-20260121-001-2",
        "sha256": "different_hash_same_id",
        "lab": "labA",
        "x_test": "CBC",
        "x_date": date(2026, 1, 21)
    }

    dup_res = check_duplicate(
        candidate=candidate_run_2,
        stored_reports=stored_reports,
        earlier_valid_candidates=[]
    )
    assert dup_res["verdict"] == "duplicate"
    assert dup_res["matched_by"] == "report_id"

def test_possible_duplicate_needs_review():
    """Same lab, test and date with a different ID and hash means possible_duplicate, which needs review."""
    earlier_report = {
        "x_report_id": "B-20260122-001-1",
        "sha256": "hash_111",
        "lab": "labB",
        "x_test": "Chest X-Ray PA View",
        "x_date": date(2026, 1, 22)
    }

    new_candidate = {
        "x_report_id": "B-20260122-999-9", # Different ID
        "sha256": "hash_222",              # Different hash
        "lab": "labB",                     # Same lab
        "x_test": "Chest X-Ray PA View",   # Same test
        "x_date": date(2026, 1, 22)        # Same date
    }

    dup_res = check_duplicate(
        candidate=new_candidate,
        stored_reports=[],
        earlier_valid_candidates=[earlier_report]
    )
    assert dup_res["verdict"] == "possible_duplicate"
    assert dup_res["matched_by"] == "lab_test_date"
