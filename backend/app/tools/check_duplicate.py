"""Tool 6: check_duplicate

Evaluates whether a candidate file is unique, an exact duplicate, or a possible duplicate.
Compares against:
1. Permanently stored reports from earlier runs for this patient.
2. Earlier valid files accepted in the current run (first copy wins).

Rules:
- Same report ID OR same SHA-256 => duplicate.
- Same lab, test, and date (with different ID and hash) => possible_duplicate (needs review).
- Otherwise => unique.
"""

from typing import Dict, Any, List, Optional
from datetime import date, datetime

def _dates_equal(d1: Any, d2: Any) -> bool:
    if not d1 or not d2:
        return False
    if isinstance(d1, datetime):
        d1 = d1.date()
    if isinstance(d2, datetime):
        d2 = d2.date()
    return str(d1) == str(d2)

def _normalize_str(s: Optional[str]) -> str:
    if not s:
        return ""
    return s.strip().lower()

def check_duplicate(
    candidate: Dict[str, Any],
    stored_reports: List[Dict[str, Any]],
    earlier_valid_candidates: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Evaluates duplication against stored reports and current run's accepted candidates.

    Returns:
        dict: {
            "verdict": "unique" | "duplicate" | "possible_duplicate",
            "matched_by": str | None,
            "matched_item": dict | None,
            "reason": str
        }
    """
    cand_report_id = _normalize_str(candidate.get("x_report_id") or candidate.get("portal_report_id"))
    cand_sha256 = _normalize_str(candidate.get("sha256"))
    cand_lab = _normalize_str(candidate.get("lab"))
    cand_test = _normalize_str(candidate.get("x_test") or candidate.get("listing_title"))
    cand_date = candidate.get("x_date") or candidate.get("portal_date")

    # Combine comparison pool: earlier stored reports first, then earlier valid candidates in current run
    all_reference_items = []
    for item in stored_reports:
        all_reference_items.append({
            "source": "stored_report",
            "report_id": _normalize_str(item.get("report_id")),
            "sha256": _normalize_str(item.get("sha256")),
            "lab": _normalize_str(item.get("lab")),
            "test_name": _normalize_str(item.get("test_name")),
            "report_date": item.get("report_date"),
            "raw": item
        })
    for item in earlier_valid_candidates:
        all_reference_items.append({
            "source": "current_run",
            "report_id": _normalize_str(item.get("x_report_id") or item.get("portal_report_id")),
            "sha256": _normalize_str(item.get("sha256")),
            "lab": _normalize_str(item.get("lab")),
            "test_name": _normalize_str(item.get("x_test") or item.get("listing_title")),
            "report_date": item.get("x_date") or item.get("portal_date"),
            "raw": item
        })

    # Step 1: Check Exact Duplicate (Report ID or SHA-256)
    for ref in all_reference_items:
        if cand_report_id and ref["report_id"] and cand_report_id == ref["report_id"]:
            return {
                "verdict": "duplicate",
                "matched_by": "report_id",
                "matched_item": ref["raw"],
                "reason": f"Exact duplicate: report ID '{cand_report_id}' matches previously processed record ({ref['source']})."
            }
        if cand_sha256 and ref["sha256"] and cand_sha256 == ref["sha256"]:
            return {
                "verdict": "duplicate",
                "matched_by": "sha256",
                "matched_item": ref["raw"],
                "reason": f"Exact duplicate: file SHA-256 hash matches previously processed document ({ref['source']})."
            }

    # Step 2: Check Possible Duplicate (Same lab, test, and date)
    for ref in all_reference_items:
        lab_match = (cand_lab and ref["lab"] and cand_lab == ref["lab"])
        test_match = (cand_test and ref["test_name"] and (cand_test in ref["test_name"] or ref["test_name"] in cand_test))
        date_match = _dates_equal(cand_date, ref["report_date"])

        if lab_match and test_match and date_match:
            return {
                "verdict": "possible_duplicate",
                "matched_by": "lab_test_date",
                "matched_item": ref["raw"],
                "reason": f"Possible duplicate: same lab ('{cand_lab}'), test ('{cand_test}'), and date ('{cand_date}') with differing ID/content. Needs human review."
            }

    return {
        "verdict": "unique",
        "matched_by": None,
        "matched_item": None,
        "reason": "File is unique and distinct from all processed records."
    }
