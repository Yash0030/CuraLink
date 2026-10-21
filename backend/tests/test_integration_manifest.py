"""Integration test running ExtractorAgent and CheckerAgent over generated synthetic PDFs, comparing against a ground-truth manifest."""

import pytest
import asyncio
from datetime import date
from app.db.repository import Repository
from app.agents.extractor import ExtractorAgent
from app.agents.checker import CheckerAgent
from app.synthetic.generate_samples import (
    create_a1_report,
    create_cityscan_report,
    create_vitals_report,
    create_fake_html_pdf
)

@pytest.mark.asyncio
async def test_integration_manifest_evaluation():
    run_id = "test-manifest-run-123"
    patient_name = "Aarav Roy"
    patient_id = "pt001"
    date_from = date(2026, 1, 1)
    date_to = date(2026, 1, 31)

    # 1. Define Ground Truth Manifest
    manifest = [
        {
            "id": "item-1",
            "lab": "labA",
            "filename": "A-20260121-001-2.pdf",
            "portal_report_id": "A-20260121-001-2",
            "portal_date": date(2026, 1, 21),
            "bytes": create_a1_report(patient_name="Aarav Roy", report_id="A-20260121-001-2", report_date="2026-01-21"),
            "expected_decision": "keep"
        },
        {
            "id": "item-2",
            "lab": "labB",
            "filename": "B-20260122-004-1.pdf",
            "portal_report_id": "B-20260122-004-1",
            "portal_date": date(2026, 1, 22),
            "bytes": create_cityscan_report(patient_name="ROY, AARAV", report_id="B-20260122-004-1", report_date="2026-01-22"),
            "expected_decision": "keep"
        },
        {
            "id": "item-3",
            "lab": "labC",
            "filename": "C-20260124-008-3.pdf",
            "portal_report_id": "C-20260124-008-3",
            "portal_date": date(2026, 1, 24),
            "bytes": create_vitals_report(patient_name="Aarav Roy", report_id="C-20260124-008-3", report_date="2026-01-24"),
            "expected_decision": "keep"
        },
        {
            "id": "item-4-tc2-dup",
            "lab": "labA",
            "filename": "A-20260121-001-2-copy.pdf",
            "portal_report_id": "A-20260121-001-2",
            "portal_date": date(2026, 1, 21),
            "bytes": create_a1_report(patient_name="Aarav Roy", report_id="A-20260121-001-2", report_date="2026-01-21"),
            "expected_decision": "duplicate" # TC2: duplicate report ID
        },
        {
            "id": "item-5-tc3-lookalike",
            "lab": "labA",
            "filename": "anita_sharma_rao.pdf",
            "portal_report_id": "A-20260120-999-1",
            "portal_date": date(2026, 1, 20),
            "bytes": create_a1_report(patient_name="Anita Sharma-Rao", report_id="A-20260120-999-1", report_date="2026-01-20"),
            "expected_decision": "exclude" # TC3: different patient name
        },
        {
            "id": "item-6-tc4-fake",
            "lab": "labB",
            "filename": "login_redirect.pdf",
            "portal_report_id": "B-20260119-000-0",
            "portal_date": date(2026, 1, 19),
            "bytes": create_fake_html_pdf(),
            "expected_decision": "reject" # TC4: not a valid PDF
        },
        {
            "id": "item-7-date-discrepancy",
            "lab": "labC",
            "filename": "discrepancy.pdf",
            "portal_report_id": "C-20260125-777-1",
            "portal_date": date(2026, 1, 10), # Portal says Jan 10, PDF says Jan 24
            "bytes": create_vitals_report(patient_name="Aarav Roy", report_id="C-20260125-777-1", report_date="2026-01-24"),
            "expected_decision": "needs_review" # Portal date != PDF date
        }
    ]

    earlier_valid = []
    stored_reports = []

    for item in manifest:
        # Stage candidate in repository
        cand = await Repository.save_candidate(
            run_id=run_id,
            lab=item["lab"],
            filename=item["filename"],
            source_url=f"http://test/{item['filename']}",
            listing_title="Test Panel",
            portal_report_id=item["portal_report_id"],
            portal_date=item["portal_date"],
            file_bytes=item["bytes"]
        )

        # 1. Run Extractor
        extract_res = await ExtractorAgent.process_candidate(cand, run_id)
        fresh_cand = await Repository.get_candidate(cand["id"])

        # 2. Run Checker
        check_res = await CheckerAgent.evaluate_candidate(
            candidate=fresh_cand,
            expected_patient_name=patient_name,
            expected_patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
            stored_reports=stored_reports,
            earlier_valid_candidates=earlier_valid,
            run_id=run_id
        )

        actual_decision = check_res["decision"]
        assert actual_decision == item["expected_decision"], (
            f"Manifest mismatch for {item['filename']}: expected '{item['expected_decision']}', got '{actual_decision}'. "
            f"Reason: {check_res['decision_reason']}"
        )

        if actual_decision == "keep":
            earlier_valid.append(fresh_cand)
