"""Tool 5: check_file_legit

Evaluates file legitimacy:
- Validates %PDF magic bytes (fails with 'not_pdf' for HTML/corrupt files - TC4).
- Missing name or date -> uncertain.
- Patient ID mismatch -> hard fail.
- Tokenized name matching:
  - Normalizes tokens: "ROY, AARAV" == "Aarav Roy".
  - Hyphens split tokens.
  - Score of 1.0 strictly requires identical token sets; fuzzy scores capped at 0.99.
  - Score >= 0.75 goes to review (unless matching patient ID elevates it to pass).
  - Score < 0.75 means a different person -> exclude (TC3).
- Date outside range -> fail.
- Portal date differing from PDF date -> uncertain.
"""

import re
from datetime import date, datetime
from typing import Dict, Any, Optional, Set, Tuple
from difflib import SequenceMatcher

def normalize_tokens(name: str) -> Set[str]:
    """Splits name into lowercase alphanumeric tokens. Hyphens and punctuation split tokens."""
    if not name:
        return set()
    # Replace hyphens and punctuation with spaces
    cleaned = re.sub(r"[-_,.\t\r\n/]+", " ", name.strip().lower())
    tokens = [t for t in re.split(r"\s+", cleaned) if t]
    return set(tokens)

def compute_name_score(name1: str, name2: str) -> Tuple[float, str]:
    """Calculates name similarity according to hackathon rules:
    - Score 1.0 strictly requires identical token sets.
    - Hyphens split tokens.
    - Fuzzy scores are capped at 0.99.
    - Score >= 0.75 goes to review (unless matching patient ID elevates it to pass).
    - Score < 0.75 means a different person -> exclude (e.g. look-alike 'Anita Sharma-Rao').
    """
    tokens1 = normalize_tokens(name1)
    tokens2 = normalize_tokens(name2)

    if not tokens1 or not tokens2:
        return 0.0, "missing_name_tokens"

    # Exact token set match (order independent)
    if tokens1 == tokens2:
        return 1.0, "exact_token_match"

    # If same number of tokens, align them for typo detection (e.g. "Arav Roy" vs "Aarav Roy")
    if len(tokens1) == len(tokens2):
        l1 = sorted(list(tokens1))
        l2 = sorted(list(tokens2))
        token_sim = sum(SequenceMatcher(None, a, b).ratio() for a, b in zip(l1, l2)) / len(l1)
        score = min(0.99, round(token_sim, 4))
        return score, f"token_typo_match (sim={token_sim:.2f})"

    # If differing number of tokens (e.g. compound surname or extra person name like 'Anita Sharma-Rao'):
    # Jaccard overlap strictly penalizes extra tokens
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    jaccard = len(intersection) / len(union) if union else 0.0

    score = min(0.99, round(jaccard, 4))
    return score, f"differing_token_set (jaccard={jaccard:.2f})"

def check_file_legit(
    file_bytes: Optional[bytes],
    extracted_name: Optional[str],
    extracted_patient_id: Optional[str],
    extracted_date: Optional[date],
    portal_date: Optional[date],
    expected_patient_name: str,
    expected_patient_id: Optional[str],
    date_from: date,
    date_to: date
) -> Dict[str, Any]:
    """Performs strict legitimacy verification on a candidate file.

    Returns:
        dict: {
            "verdict": "pass" | "uncertain" | "fail",
            "code": str,
            "reasons": list[str],
            "evidence": dict,
            "name_score": float
        }
    """
    reasons = []
    evidence = {
        "expected_name": expected_patient_name,
        "extracted_name": extracted_name,
        "expected_patient_id": expected_patient_id,
        "extracted_patient_id": extracted_patient_id,
        "extracted_date": str(extracted_date) if extracted_date else None,
        "portal_date": str(portal_date) if portal_date else None,
        "date_range": [str(date_from), str(date_to)]
    }

    # 1. Verify %PDF signature (TC4)
    if not file_bytes or not file_bytes.startswith(b"%PDF"):
        return {
            "verdict": "fail",
            "code": "not_pdf",
            "reasons": ["File does not start with %PDF magic header (TC4)."],
            "evidence": evidence,
            "name_score": 0.0
        }

    # 2. Hard patient ID check
    patient_id_matched = False
    if expected_patient_id and extracted_patient_id:
        exp_id_clean = expected_patient_id.strip().lower()
        ext_id_clean = extracted_patient_id.strip().lower()
        if exp_id_clean != ext_id_clean:
            return {
                "verdict": "fail",
                "code": "patient_id_mismatch",
                "reasons": [f"Patient ID mismatch: expected '{expected_patient_id}', got '{extracted_patient_id}'."],
                "evidence": evidence,
                "name_score": 0.0
            }
        else:
            patient_id_matched = True

    # 3. Missing name or date check -> uncertain
    if not extracted_name or not extracted_name.strip():
        return {
            "verdict": "uncertain",
            "code": "missing_name",
            "reasons": ["Extracted name is missing from document."],
            "evidence": evidence,
            "name_score": 0.0
        }

    if not extracted_date:
        return {
            "verdict": "uncertain",
            "code": "missing_date",
            "reasons": ["Extracted date is missing from document."],
            "evidence": evidence,
            "name_score": 0.0
        }

    # 4. Name matching
    name_score, score_note = compute_name_score(expected_patient_name, extracted_name)
    evidence["name_score"] = name_score
    evidence["name_score_note"] = score_note

    if name_score < 0.75:
        return {
            "verdict": "fail",
            "code": "name_mismatch_exclude",
            "reasons": [f"Name similarity {name_score:.2f} < 0.75 indicates a different person (e.g. look-alike '{extracted_name}'). Exclude."],
            "evidence": evidence,
            "name_score": name_score
        }

    is_name_review = False
    if name_score < 1.0:
        # Score is between 0.75 and 0.99
        if patient_id_matched:
            # "A matching patient ID with a close name passes."
            reasons.append(f"Name similarity is {name_score:.2f} but patient ID matched exactly; accepted.")
        else:
            # Goes to review
            is_name_review = True
            reasons.append(f"Name similarity {name_score:.2f} requires human review.")

    # 5. Date range check
    if isinstance(extracted_date, datetime):
        extracted_date = extracted_date.date()
    if isinstance(date_from, datetime):
        date_from = date_from.date()
    if isinstance(date_to, datetime):
        date_to = date_to.date()

    if not (date_from <= extracted_date <= date_to):
        return {
            "verdict": "fail",
            "code": "date_out_of_range",
            "reasons": [f"Document date {extracted_date} is outside requested range [{date_from} to {date_to}]."],
            "evidence": evidence,
            "name_score": name_score
        }

    # 6. Portal date vs PDF date check -> uncertain
    if portal_date:
        if isinstance(portal_date, datetime):
            portal_date = portal_date.date()
        if portal_date != extracted_date:
            return {
                "verdict": "uncertain",
                "code": "date_discrepancy",
                "reasons": [f"Portal listing date ({portal_date}) differs from PDF document date ({extracted_date})."],
                "evidence": evidence,
                "name_score": name_score
            }

    if is_name_review:
        return {
            "verdict": "uncertain",
            "code": "needs_name_review",
            "reasons": reasons,
            "evidence": evidence,
            "name_score": name_score
        }

    return {
        "verdict": "pass",
        "code": "legit_pass",
        "reasons": ["All legitimacy checks passed."],
        "evidence": evidence,
        "name_score": name_score
    }
