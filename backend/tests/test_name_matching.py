"""Unit tests for token normalization, hyphen splitting, and name matching scoring rules.

Rules verified:
- "ROY, AARAV" equals "Aarav Roy" (score 1.0, exact token set).
- Hyphens split tokens (e.g. "Sharma-Rao" splits into "sharma", "rao").
- Score 1.0 strictly requires identical token sets; fuzzy scores are capped at 0.99.
- Score >= 0.75 goes to review (unless patient ID matches).
- Score < 0.75 indicates a different person -> exclude (TC3: 'Anita Sharma-Rao' vs 'Anita Sharma').
- Matching patient ID with a close name (score >= 0.75) passes.
"""

import pytest
from datetime import date
from app.tools.check_legit import normalize_tokens, compute_name_score, check_file_legit

def test_token_normalization_and_hyphen_splitting():
    # Hyphens split tokens
    tokens1 = normalize_tokens("Anita Sharma-Rao")
    assert tokens1 == {"anita", "sharma", "rao"}

    # Comma and spacing normalization
    tokens2 = normalize_tokens("ROY, AARAV")
    assert tokens2 == {"roy", "aarav"}

    tokens3 = normalize_tokens("Aarav Roy")
    assert tokens3 == {"aarav", "roy"}

    assert tokens2 == tokens3

def test_exact_name_match_score_is_1_0():
    score, note = compute_name_score("Aarav Roy", "ROY, AARAV")
    assert score == 1.0
    assert note == "exact_token_match"

def test_fuzzy_name_score_capped_at_0_99():
    # Close name with minor typo: score is capped at 0.99 and >= 0.75
    score, note = compute_name_score("Aarav Roy", "Arav Roy")
    assert score < 1.0
    assert score <= 0.99
    assert score >= 0.75

def test_tc3_lookalike_name_excluded():
    """TC3: A report with another patient's name is excluded, including look-alike 'Anita Sharma-Rao'."""
    score, _ = compute_name_score("Anita Sharma", "Anita Sharma-Rao")
    assert score < 0.75, f"Expected score < 0.75 for look-alike, got {score}"

    # Verify check_file_legit verdict is fail with name_mismatch_exclude
    res = check_file_legit(
        file_bytes=b"%PDF-1.4 sample content",
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

def test_matching_patient_id_with_close_name_passes():
    """A matching patient ID with a close name passes."""
    res = check_file_legit(
        file_bytes=b"%PDF-1.4 sample content",
        extracted_name="Arav Roy", # close name (score >= 0.75)
        extracted_patient_id="PT001",
        extracted_date=date(2026, 1, 20),
        portal_date=date(2026, 1, 20),
        expected_patient_name="Aarav Roy",
        expected_patient_id="pt001",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31)
    )
    assert res["verdict"] == "pass"

def test_close_name_without_patient_id_goes_to_review():
    """A close name (score >= 0.75) without patient ID requires human review."""
    res = check_file_legit(
        file_bytes=b"%PDF-1.4 sample content",
        extracted_name="Arav Roy",
        extracted_patient_id=None,
        extracted_date=date(2026, 1, 20),
        portal_date=date(2026, 1, 20),
        expected_patient_name="Aarav Roy",
        expected_patient_id="pt001",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31)
    )
    assert res["verdict"] == "uncertain"
    assert res["code"] == "needs_name_review"
