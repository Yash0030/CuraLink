"""Seed Official Hackathon Test Scenarios (Step 7 of Build Guide).

Populates labelled runs into PostgreSQL/Neon preserving:
- TC1 (Aarav Roy - PT001): Multi-Lab Sync (3 portals -> 6 reports verified into 1 timeline)
- TC2 (Reyansh Reddy - PT002): Initial run (exact duplicate flagged, stored once)
- TC2 (Reyansh Reddy - PT002): Re-run (stored once across runs verification)
- TC3 (Gopal Chauhan - PT003): Wrong patient (Diya Ghosh) auto-excluded
- TC3b (Anita Sharma - PT006): Look-alike name collision auto-excluded
- TC4 (Aditya Malhotra - PT004): Non-PDF / corrupt HTML page auto-rejected
- Bonus (Mohan Chopra - PT005): Date mismatch between portal and PDF (sent to human review)
"""

import sys
import os
import uuid
import json
import hashlib
from datetime import datetime, date, timezone, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from app.db.connection import init_pool, close_pool, get_db_pool
from app.db.repository import Repository, generate_patient_key
from app.synthetic.generate_samples import (
    create_a1_report,
    create_cityscan_report,
    create_vitals_report,
    create_fake_html_pdf,
)

async def seed_scenarios():
    print("Connecting to database pool...")
    await init_pool()
    pool = get_db_pool()
    if not pool:
        print("ERROR: Database pool could not be initialized.")
        return

    now = datetime.now(timezone.utc)
    base_time = now - timedelta(hours=2)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            print("Cleaning up previously seeded demo test runs...")
            # Remove candidates and events associated with demo runs
            await cur.execute("""
                DELETE FROM phr.runs 
                WHERE patient_id IN ('pt001', 'pt002', 'pt003', 'pt004', 'pt005', 'pt006')
                   OR LOWER(patient_name) LIKE '%aarav%'
                   OR LOWER(patient_name) LIKE '%reyansh%'
                   OR LOWER(patient_name) LIKE '%gopal%'
                   OR LOWER(patient_name) LIKE '%aditya%'
                   OR LOWER(patient_name) LIKE '%anita%'
                   OR LOWER(patient_name) LIKE '%mohan%';
            """)
            await conn.commit()

    # -------------------------------------------------------------
    # 1. TC1: Aarav Roy (PT001) - 3 Portals -> 1 Unified Timeline
    # -------------------------------------------------------------
    print("Seeding TC1: Aarav Roy (PT001) - Multi-Lab Sync...")
    tc1_time = base_time + timedelta(minutes=10)
    run1 = await Repository.create_run(
        patient_name="Aarav Roy",
        patient_id="pt001",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 4, 30),
        labs=["labA", "labB", "labC"]
    )
    run1_id = run1["id"]
    patient_key_1 = run1["patient_key"]

    cands_tc1 = [
        ("labA", "A-20260121-001-2.pdf", "Complete Blood Count (CBC)", "A-20260121-001-2", date(2026, 1, 21),
         create_a1_report("Aarav Roy", "pt001", "A-20260121-001-2", "2026-01-21", "Complete Blood Count (CBC)")),
        ("labA", "A-20260307-001-1.pdf", "Liver Function Test (LFT)", "A-20260307-001-1", date(2026, 3, 7),
         create_a1_report("Aarav Roy", "pt001", "A-20260307-001-1", "2026-03-07", "Liver Function Test (LFT)")),
        ("labB", "B-20260218-001-2.pdf", "Chest X-Ray PA View", "B-20260218-001-2", date(2026, 2, 18),
         create_cityscan_report("ROY, AARAV", "pt001", "B-20260218-001-2", "2026-02-18", "Chest X-Ray PA View")),
        ("labB", "B-20260219-001-1.pdf", "MRI Lumbar Spine", "B-20260219-001-1", date(2026, 2, 19),
         create_cityscan_report("ROY, AARAV", "pt001", "B-20260219-001-1", "2026-02-19", "MRI Lumbar Spine")),
        ("labC", "C-20260309-001-1.pdf", "Comprehensive Lipid Panel", "C-20260309-001-1", date(2026, 3, 9),
         create_vitals_report("Aarav Roy", "pt001", "C-20260309-001-1", "2026-03-09", "Comprehensive Lipid Panel")),
        ("labC", "C-20260312-001-2.pdf", "HbA1c Glycated Hemoglobin", "C-20260312-001-2", date(2026, 3, 12),
         create_vitals_report("Aarav Roy", "pt001", "C-20260312-001-2", "2026-03-12", "HbA1c Glycated Hemoglobin")),
    ]

    for lab, fname, title, rep_id, rep_dt, pdf_b in cands_tc1:
        c = await Repository.save_candidate(
            run_id=run1_id, lab=lab, filename=fname,
            source_url=f"/{lab}/download/{fname}",
            listing_title=title, portal_report_id=rep_id,
            portal_date=rep_dt, file_bytes=pdf_b
        )
        await Repository.update_candidate_extraction(
            candidate_id=c["id"], extract_ok=True,
            extract_note=f"Parsed metadata cleanly via regex from {lab.upper()}",
            extract_source="regex", x_name="Aarav Roy", x_patient_id="pt001",
            x_report_id=rep_id, x_date=rep_dt, x_test=title
        )
        await Repository.update_candidate_check(
            candidate_id=c["id"],
            legit_result={"verdict": "pass", "reasons": ["Valid %PDF- header", "Patient identity exact match"]},
            duplicate_result={"verdict": "unique", "sha256": c["sha256"]},
            decision="keep",
            decision_reason="Verified authentic, matching patient, and unique."
        )
        # Store in timeline
        await Repository.store_approved_candidate(
            candidate_id=c["id"],
            patient_key=patient_key_1,
            lab=lab,
            report_id=rep_id,
            test_name=title,
            report_date=rep_dt,
            sha256=c["sha256"]
        )

    await Repository.record_event(run1_id, "Orchestrator", "INFO", "Started collection for Aarav Roy across A1, CityScan, and Vitals.")
    await Repository.record_event(run1_id, "Fetcher", "INFO", "Completed parallel retrieval: 6 reports downloaded across 3 lab portals.")
    await Repository.record_event(run1_id, "Extractor", "INFO", "Successfully extracted medical metadata from all 6 documents.")
    await Repository.record_event(run1_id, "QualityChecker", "INFO", "All 6 documents verified authentic, uniquely identified, and matching patient 'Aarav Roy'.")
    await Repository.record_event(run1_id, "User", "INFO", "User approved collection batch. 6 reports committed to patient health timeline.")
    await Repository.record_event(run1_id, "Rechecker", "INFO", "Byte-level verification passed: 6/6 stored files verified matching SHA-256 and patient identifier.")
    await Repository.record_approval(run1_id, approved=True, overrides={})
    await Repository.update_run_status(run1_id, "completed")

    # -------------------------------------------------------------
    # 2. TC2: Reyansh Reddy (PT002) - Run 1 (Duplicate Flagged)
    # -------------------------------------------------------------
    print("Seeding TC2: Reyansh Reddy (PT002) - Run 1 (Duplicate Flagged)...")
    tc2_time = base_time + timedelta(minutes=25)
    run2 = await Repository.create_run(
        patient_name="Reyansh Reddy",
        patient_id="pt002",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 4, 30),
        labs=["labA"]
    )
    run2_id = run2["id"]
    patient_key_2 = run2["patient_key"]

    pdf_reyansh = create_a1_report("Reyansh Reddy", "pt002", "A-20260407-002-1", "2026-04-07", "Complete Blood Count (CBC)")

    # 1. Unique copy
    c2_1 = await Repository.save_candidate(
        run_id=run2_id, lab="labA", filename="A-20260407-002-1.pdf",
        source_url="/labA/download/A-20260407-002-1.pdf",
        listing_title="Complete Blood Count (CBC)",
        portal_report_id="A-20260407-002-1",
        portal_date=date(2026, 4, 7),
        file_bytes=pdf_reyansh
    )
    await Repository.update_candidate_extraction(
        candidate_id=c2_1["id"], extract_ok=True,
        extract_note="Parsed metadata cleanly via regex from A1",
        extract_source="regex", x_name="Reyansh Reddy", x_patient_id="pt002",
        x_report_id="A-20260407-002-1", x_date=date(2026, 4, 7), x_test="Complete Blood Count (CBC)"
    )
    await Repository.update_candidate_check(
        candidate_id=c2_1["id"],
        legit_result={"verdict": "pass", "reasons": ["Valid %PDF- header", "Patient identity exact match"]},
        duplicate_result={"verdict": "unique", "sha256": c2_1["sha256"]},
        decision="keep",
        decision_reason="Verified authentic, matching patient, and unique."
    )
    # Store unique copy in timeline
    await Repository.store_approved_candidate(
        candidate_id=c2_1["id"], patient_key=patient_key_2,
        lab="labA", report_id="A-20260407-002-1",
        test_name="Complete Blood Count (CBC)", report_date=date(2026, 4, 7),
        sha256=c2_1["sha256"]
    )

    # 2. Duplicate copy
    c2_2 = await Repository.save_candidate(
        run_id=run2_id, lab="labA", filename="A-20260407-002-1_copy.pdf",
        source_url="/labA/download/A-20260407-002-1_copy.pdf",
        listing_title="Complete Blood Count (CBC) [Duplicate]",
        portal_report_id="A-20260407-002-1",
        portal_date=date(2026, 4, 7),
        file_bytes=pdf_reyansh
    )
    await Repository.update_candidate_extraction(
        candidate_id=c2_2["id"], extract_ok=True,
        extract_note="Duplicate candidate identical to A-20260407-002-1.pdf",
        extract_source="regex", x_name="Reyansh Reddy", x_patient_id="pt002",
        x_report_id="A-20260407-002-1", x_date=date(2026, 4, 7), x_test="Complete Blood Count (CBC)"
    )
    await Repository.update_candidate_check(
        candidate_id=c2_2["id"],
        legit_result={"verdict": "pass"},
        duplicate_result={"verdict": "duplicate", "match_type": "checksum_and_report_id", "matched_with": "A-20260407-002-1.pdf"},
        decision="duplicate",
        decision_reason="Exact duplicate: report ID 'A-20260407-002-1' and SHA-256 match previously processed record in current run."
    )

    await Repository.record_event(run2_id, "Orchestrator", "INFO", "Started collection for Reyansh Reddy on A1 Reference Labs.")
    await Repository.record_event(run2_id, "Fetcher", "INFO", "Downloaded 2 reports from A1 portal.")
    await Repository.record_event(run2_id, "QualityChecker", "WARNING", "Duplicate detected! 'A-20260407-002-1_copy.pdf' has identical SHA-256 and report ID to 'A-20260407-002-1.pdf'. Flagged as DUPLICATE.")
    await Repository.record_event(run2_id, "User", "INFO", "User confirmed approval: 1 unique report stored, 1 duplicate discarded.")
    await Repository.record_event(run2_id, "Rechecker", "INFO", "Stored once verification passed: exactly 1 copy stored in timeline.")
    await Repository.record_approval(run2_id, approved=True, overrides={})
    await Repository.update_run_status(run2_id, "completed")

    # -------------------------------------------------------------
    # 3. TC2: Reyansh Reddy (PT002) - Run 2 (Stored Once Verification)
    # -------------------------------------------------------------
    print("Seeding TC2: Reyansh Reddy (PT002) - Run 2 (Stored Once Verification)...")
    tc2_run2_time = base_time + timedelta(minutes=40)
    run2_re = await Repository.create_run(
        patient_name="Reyansh Reddy (Re-run)",
        patient_id="pt002",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 4, 30),
        labs=["labA"]
    )
    run2_re_id = run2_re["id"]

    # Both downloaded files are cross-run duplicates of existing timeline report!
    c2_re1 = await Repository.save_candidate(
        run_id=run2_re_id, lab="labA", filename="A-20260407-002-1.pdf",
        source_url="/labA/download/A-20260407-002-1.pdf",
        listing_title="Complete Blood Count (CBC)",
        portal_report_id="A-20260407-002-1",
        portal_date=date(2026, 4, 7),
        file_bytes=pdf_reyansh
    )
    await Repository.update_candidate_extraction(
        candidate_id=c2_re1["id"], extract_ok=True,
        extract_note="Re-fetched document", extract_source="regex",
        x_name="Reyansh Reddy", x_patient_id="pt002",
        x_report_id="A-20260407-002-1", x_date=date(2026, 4, 7), x_test="Complete Blood Count (CBC)"
    )
    await Repository.update_candidate_check(
        candidate_id=c2_re1["id"],
        legit_result={"verdict": "pass"},
        duplicate_result={"verdict": "duplicate", "match_type": "cross_run_stored", "matched_with": "stored_reports"},
        decision="duplicate",
        decision_reason="Exact duplicate: matches previously verified record already committed to timeline (cross-run match against stored_reports)."
    )

    c2_re2 = await Repository.save_candidate(
        run_id=run2_re_id, lab="labA", filename="A-20260407-002-1_copy.pdf",
        source_url="/labA/download/A-20260407-002-1_copy.pdf",
        listing_title="Complete Blood Count (CBC) [Duplicate]",
        portal_report_id="A-20260407-002-1",
        portal_date=date(2026, 4, 7),
        file_bytes=pdf_reyansh
    )
    await Repository.update_candidate_extraction(
        candidate_id=c2_re2["id"], extract_ok=True,
        extract_note="Re-fetched duplicate copy", extract_source="regex",
        x_name="Reyansh Reddy", x_patient_id="pt002",
        x_report_id="A-20260407-002-1", x_date=date(2026, 4, 7), x_test="Complete Blood Count (CBC)"
    )
    await Repository.update_candidate_check(
        candidate_id=c2_re2["id"],
        legit_result={"verdict": "pass"},
        duplicate_result={"verdict": "duplicate", "match_type": "cross_run_stored", "matched_with": "stored_reports"},
        decision="duplicate",
        decision_reason="Exact duplicate: matches previously verified record already committed to timeline (cross-run match against stored_reports)."
    )

    await Repository.record_event(run2_re_id, "Orchestrator", "INFO", "Started repeat collection for Reyansh Reddy to test cross-run idempotency.")
    await Repository.record_event(run2_re_id, "Fetcher", "INFO", "Retrieved 2 reports from A1 portal.")
    await Repository.record_event(run2_re_id, "QualityChecker", "WARNING", "Candidate A-20260407-002-1.pdf already exists in timeline! Flagged as cross-run duplicate.")
    await Repository.record_event(run2_re_id, "QualityChecker", "WARNING", "Candidate A-20260407-002-1_copy.pdf already exists in timeline! Flagged as cross-run duplicate.")
    await Repository.record_event(run2_re_id, "User", "INFO", "Confirmed exclusion of redundant cross-run copies. 0 new reports committed to timeline.")
    await Repository.record_event(run2_re_id, "Rechecker", "INFO", "'Stored Once Across Runs' rule satisfied: timeline count unchanged.")
    await Repository.record_approval(run2_re_id, approved=True, overrides={})
    await Repository.update_run_status(run2_re_id, "completed")

    # -------------------------------------------------------------
    # 4. TC3: Gopal Chauhan (PT003) - Wrong Patient Excluded
    # -------------------------------------------------------------
    print("Seeding TC3: Gopal Chauhan (PT003) - Wrong Patient Excluded...")
    tc3_time = base_time + timedelta(minutes=55)
    run3 = await Repository.create_run(
        patient_name="Gopal Chauhan",
        patient_id="pt003",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 4, 30),
        labs=["labB"]
    )
    run3_id = run3["id"]

    pdf_diya = create_cityscan_report("Diya Ghosh", "pt020", "B-20260206-020-9", "2026-02-06", "Ultrasound Whole Abdomen")
    c3 = await Repository.save_candidate(
        run_id=run3_id, lab="labB", filename="B-20260206-020-9.pdf",
        source_url="/labB/download/B-20260206-020-9.pdf",
        listing_title="Ultrasound Whole Abdomen",
        portal_report_id="B-20260206-020-9",
        portal_date=date(2026, 2, 6),
        file_bytes=pdf_diya
    )
    await Repository.update_candidate_extraction(
        candidate_id=c3["id"], extract_ok=True,
        extract_note="Parsed metadata via regex: Patient name is Diya Ghosh (PT020)",
        extract_source="regex", x_name="Diya Ghosh", x_patient_id="pt020",
        x_report_id="B-20260206-020-9", x_date=date(2026, 2, 6), x_test="Ultrasound Whole Abdomen"
    )
    await Repository.update_candidate_check(
        candidate_id=c3["id"],
        legit_result={"verdict": "fail", "reason": "Patient identity mismatch: Diya Ghosh (PT020) does not match requested patient Gopal Chauhan (PT003)"},
        duplicate_result={"verdict": "unique"},
        decision="exclude",
        decision_reason="Mismatched patient identity: report belongs to Diya Ghosh (PT020), not Gopal Chauhan (PT003)."
    )

    await Repository.record_event(run3_id, "Orchestrator", "INFO", "Started collection for Gopal Chauhan (PT003) on CityScan Imaging.")
    await Repository.record_event(run3_id, "Fetcher", "INFO", "Downloaded candidate B-20260206-020-9.pdf from CityScan portal.")
    await Repository.record_event(run3_id, "Extractor", "INFO", "Extracted document fields: Patient = 'Diya Ghosh', MRN = 'PT020', Date = '2026-02-06'.")
    await Repository.record_event(run3_id, "QualityChecker", "WARNING", "Identity mismatch detected! Extracted patient 'Diya Ghosh' differs from target 'Gopal Chauhan' (Token similarity: 0.08). Decision: EXCLUDE.")
    await Repository.record_event(run3_id, "User", "INFO", "User confirmed automatic exclusion of foreign patient report.")
    await Repository.record_approval(run3_id, approved=True, overrides={})
    await Repository.update_run_status(run3_id, "completed")

    # -------------------------------------------------------------
    # 5. TC3b: Anita Sharma (PT006) - Look-alike Name Collision
    # -------------------------------------------------------------
    print("Seeding TC3b: Anita Sharma (PT006) - Name Collision...")
    tc3b_time = base_time + timedelta(minutes=70)
    run3b = await Repository.create_run(
        patient_name="Anita Sharma",
        patient_id="pt006",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 4, 30),
        labs=["labB"]
    )
    run3b_id = run3b["id"]

    pdf_anita_rao = create_cityscan_report("Anita Sharma-Rao", "pt007", "B-20260107-007-9", "2026-01-07", "CT Scan Head & Brain")
    c3b = await Repository.save_candidate(
        run_id=run3b_id, lab="labB", filename="B-20260107-007-9.pdf",
        source_url="/labB/download/B-20260107-007-9.pdf",
        listing_title="CT Scan Head & Brain",
        portal_report_id="B-20260107-007-9",
        portal_date=date(2026, 1, 7),
        file_bytes=pdf_anita_rao
    )
    await Repository.update_candidate_extraction(
        candidate_id=c3b["id"], extract_ok=True,
        extract_note="Extracted patient name 'Anita Sharma-Rao' (MRN PT007)",
        extract_source="regex", x_name="Anita Sharma-Rao", x_patient_id="pt007",
        x_report_id="B-20260107-007-9", x_date=date(2026, 1, 7), x_test="CT Scan Head & Brain"
    )
    await Repository.update_candidate_check(
        candidate_id=c3b["id"],
        legit_result={"verdict": "fail", "reason": "Look-alike name discrepancy: 'Anita Sharma-Rao' does not strictly match target 'Anita Sharma'"},
        duplicate_result={"verdict": "unique"},
        decision="exclude",
        decision_reason="Look-alike name collision: candidate name 'Anita Sharma-Rao' (PT007) does not match requested patient 'Anita Sharma' (PT006)."
    )

    await Repository.record_event(run3b_id, "Orchestrator", "INFO", "Started collection for Anita Sharma (PT006) on CityScan Imaging.")
    await Repository.record_event(run3b_id, "Fetcher", "INFO", "Downloaded report B-20260107-007-9.pdf from CityScan portal.")
    await Repository.record_event(run3b_id, "QualityChecker", "WARNING", "Partial look-alike match rejected: 'Anita Sharma-Rao' != 'Anita Sharma'. Decision: EXCLUDE.")
    await Repository.record_event(run3b_id, "User", "INFO", "User confirmed exclusion of name-collision report.")
    await Repository.record_approval(run3b_id, approved=True, overrides={})
    await Repository.update_run_status(run3b_id, "completed")

    # -------------------------------------------------------------
    # 6. TC4: Aditya Malhotra (PT004) - Non-PDF Rejected
    # -------------------------------------------------------------
    print("Seeding TC4: Aditya Malhotra (PT004) - Non-PDF Rejected...")
    tc4_time = base_time + timedelta(minutes=85)
    run4 = await Repository.create_run(
        patient_name="Aditya Malhotra",
        patient_id="pt004",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 4, 30),
        labs=["labC"]
    )
    run4_id = run4["id"]

    html_bytes = create_fake_html_pdf()
    c4 = await Repository.save_candidate(
        run_id=run4_id, lab="labC", filename="C-20260303-004-9.pdf",
        source_url="/labC/download/C-20260303-004-9.pdf",
        listing_title="Diagnostic Panel Download",
        portal_report_id="C-20260303-004-9",
        portal_date=date(2026, 3, 3),
        file_bytes=html_bytes,
        content_type="text/html"
    )
    await Repository.update_candidate_extraction(
        candidate_id=c4["id"], extract_ok=False,
        extract_note="Extraction aborted: file is not a valid PDF document (HTML redirection content)",
        extract_source="error", x_name=None, x_patient_id=None,
        x_report_id=None, x_date=None, x_test=None
    )
    await Repository.update_candidate_check(
        candidate_id=c4["id"],
        legit_result={"verdict": "fail", "reason": "Invalid PDF magic bytes: file starts with '<!DOCTYPE html>', expected '%PDF-'"},
        duplicate_result={"verdict": "unique"},
        decision="reject",
        decision_reason="Corrupt / invalid file format: header is HTML '<!DOCTYPE html>', not '%PDF-'. Detected login redirection page saved with .pdf extension."
    )

    await Repository.record_event(run4_id, "Orchestrator", "INFO", "Started collection for Aditya Malhotra (PT004) on Vitals Diagnostic.")
    await Repository.record_event(run4_id, "Fetcher", "INFO", "Downloaded candidate C-20260303-004-9.pdf from Vitals portal.")
    await Repository.record_event(run4_id, "QualityChecker", "ERROR", "Format verification failed! Document lacks %PDF- header magic bytes; contains HTML login redirection. Decision: REJECT.")
    await Repository.record_event(run4_id, "User", "INFO", "User confirmed rejection of corrupt non-PDF candidate.")
    await Repository.record_approval(run4_id, approved=True, overrides={})
    await Repository.update_run_status(run4_id, "completed")

    # -------------------------------------------------------------
    # 7. Bonus: Mohan Chopra (PT005) - Date Mismatch Discrepancy
    # -------------------------------------------------------------
    print("Seeding Bonus: Mohan Chopra (PT005) - Date Discrepancy...")
    tc5_time = base_time + timedelta(minutes=100)
    run5 = await Repository.create_run(
        patient_name="Mohan Chopra",
        patient_id="pt005",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 4, 30),
        labs=["labA"]
    )
    run5_id = run5["id"]

    pdf_mohan = create_a1_report("Mohan Chopra", "pt005", "A-20260401-005-1", "2026-04-01", "Thyroid Profile Total (T3, T4, TSH)")
    c5 = await Repository.save_candidate(
        run_id=run5_id, lab="labA", filename="A-20260401-005-1.pdf",
        source_url="/labA/download/A-20260401-005-1.pdf",
        listing_title="Thyroid Profile Total (T3, T4, TSH)",
        portal_report_id="A-20260401-005-1",
        portal_date=date(2026, 4, 4),  # Portal lists 4 Apr, but PDF internally states 1 Apr!
        file_bytes=pdf_mohan
    )
    await Repository.update_candidate_extraction(
        candidate_id=c5["id"], extract_ok=True,
        extract_note="Extracted PDF report date: 2026-04-01",
        extract_source="regex", x_name="Mohan Chopra", x_patient_id="pt005",
        x_report_id="A-20260401-005-1", x_date=date(2026, 4, 1), x_test="Thyroid Profile Total (T3, T4, TSH)"
    )
    await Repository.update_candidate_check(
        candidate_id=c5["id"],
        legit_result={"verdict": "anomaly", "reason": "Date mismatch: Portal date (2026-04-04) differs from internal PDF date (2026-04-01) by 3 days"},
        duplicate_result={"verdict": "unique"},
        decision="needs_review",
        decision_reason="Date discrepancy detected: Portal listed 2026-04-04 but document text states 2026-04-01. Flagged for human review."
    )

    await Repository.record_event(run5_id, "Orchestrator", "INFO", "Started collection for Mohan Chopra (PT005) on A1 Reference Labs.")
    await Repository.record_event(run5_id, "Fetcher", "INFO", "Downloaded candidate A-20260401-005-1.pdf.")
    await Repository.record_event(run5_id, "Extractor", "INFO", "Extracted internal report date: 2026-04-01.")
    await Repository.record_event(run5_id, "QualityChecker", "WARNING", "Date mismatch detected: portal lists 2026-04-04 while internal report text states 2026-04-01. Sent to Human Review Queue.")
    await Repository.update_run_status(run5_id, "waiting_approval")

    # Order the created_at timestamps cleanly in Postgres
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            runs_ordered = [
                (run5_id, tc5_time),
                (run4_id, tc4_time),
                (run3b_id, tc3b_time),
                (run3_id, tc3_time),
                (run2_re_id, tc2_run2_time),
                (run2_id, tc2_time),
                (run1_id, tc1_time),
            ]
            for rid, t in runs_ordered:
                await cur.execute("UPDATE phr.runs SET created_at = %s, updated_at = %s WHERE id = %s", (t, t, rid))
            await conn.commit()

    print("\nSUCCESS: All official test scenarios seeded perfectly!")
    print("1. TC1: Aarav Roy (PT001) - 6 reports verified in 1 timeline (Completed)")
    print("2. TC2: Reyansh Reddy (PT002) Run 1 - Duplicate flagged, stored once (Completed)")
    print("3. TC2: Reyansh Reddy (PT002) Run 2 - Stored once across runs verified (Completed)")
    print("4. TC3: Gopal Chauhan (PT003) - Diya Ghosh excluded (Completed)")
    print("5. TC3b: Anita Sharma (PT006) - Look-alike name excluded (Completed)")
    print("6. TC4: Aditya Malhotra (PT004) - Non-PDF rejected (Completed)")
    print("7. Bonus: Mohan Chopra (PT005) - Date mismatch (Waiting for Approval)")

    await close_pool()

if __name__ == "__main__":
    asyncio.run(seed_scenarios())
