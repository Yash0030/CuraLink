"""End-to-end API test with browser fetchers stubbed out."""

import pytest
import httpx
from datetime import date
from app.main import app
from app.db.repository import Repository
from app.synthetic.generate_samples import create_a1_report, create_cityscan_report

@pytest.mark.asyncio
async def test_api_e2e_lifecycle():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        res_health = await client.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"

        # 2. List Labs
        res_labs = await client.get("/api/labs")
        assert res_labs.status_code == 200
        labs = res_labs.json()
        assert len(labs) == 3
        lab_keys = [l["key"] for l in labs]
        assert "labA" in lab_keys and "labB" in lab_keys and "labC" in lab_keys

        # 3. Create Run (stubbing out real browser by creating DB run and staging candidates)
        run_data = await Repository.create_run(
            patient_name="Aarav Roy",
            patient_id="pt001",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            labs=["labA", "labB"]
        )
        run_id = run_data["id"]

        # Stage two authentic candidates
        cand1 = await Repository.save_candidate(
            run_id=run_id,
            lab="labA",
            filename="A-20260121-001-2.pdf",
            source_url="http://stub/A1.pdf",
            listing_title="CBC",
            portal_report_id="A-20260121-001-2",
            portal_date=date(2026, 1, 21),
            file_bytes=create_a1_report(patient_name="Aarav Roy")
        )
        cand2 = await Repository.save_candidate(
            run_id=run_id,
            lab="labB",
            filename="B-20260122-004-1.pdf",
            source_url="http://stub/CS.pdf",
            listing_title="Chest X-Ray",
            portal_report_id="B-20260122-004-1",
            portal_date=date(2026, 1, 22),
            file_bytes=create_cityscan_report(patient_name="ROY, AARAV")
        )

        # Update candidate extraction and decisions
        await Repository.update_candidate_extraction(
            candidate_id=cand1["id"],
            extract_ok=True,
            extract_note="Test extraction",
            extract_source="regex",
            x_name="Aarav Roy",
            x_patient_id="pt001",
            x_report_id="A-20260121-001-2",
            x_date=date(2026, 1, 21),
            x_test="CBC"
        )
        await Repository.update_candidate_check(
            candidate_id=cand1["id"],
            legit_result={"verdict": "pass"},
            duplicate_result={"verdict": "unique"},
            decision="keep",
            decision_reason="Verified authentic"
        )

        await Repository.update_candidate_extraction(
            candidate_id=cand2["id"],
            extract_ok=True,
            extract_note="Test extraction",
            extract_source="regex",
            x_name="ROY, AARAV",
            x_patient_id="pt001",
            x_report_id="B-20260122-004-1",
            x_date=date(2026, 1, 22),
            x_test="Chest X-Ray"
        )
        await Repository.update_candidate_check(
            candidate_id=cand2["id"],
            legit_result={"verdict": "pass"},
            duplicate_result={"verdict": "unique"},
            decision="keep",
            decision_reason="Verified authentic"
        )

        await Repository.update_run_status(run_id, "waiting_approval")

        # 4. GET /api/runs/{id}
        res_run = await client.get(f"/api/runs/{run_id}")
        assert res_run.status_code == 200
        run_info = res_run.json()
        assert run_info["run"]["id"] == run_id
        assert run_info["decision_counts"]["keep"] == 2

        # 5. GET /api/runs/{id}/events
        res_events = await client.get(f"/api/runs/{run_id}/events")
        assert res_events.status_code == 200

        # 6. GET /api/runs/{id}/candidates
        res_cands = await client.get(f"/api/runs/{run_id}/candidates")
        assert res_cands.status_code == 200
        cands_json = res_cands.json()
        assert len(cands_json) == 2
        assert "file_bytes" not in cands_json[0] # Verify binary payload is omitted

        # 7. POST /api/runs/{id}/approve
        res_approve = await client.post(
            f"/api/runs/{run_id}/approve",
            json={"approved": True, "overrides": {}}
        )
        assert res_approve.status_code == 200
        assert res_approve.json()["approved"] is True

        # 8. GET /api/timeline
        patient_key = run_data["patient_key"]
        res_timeline = await client.get(f"/api/timeline?patient_key={patient_key}")
        assert res_timeline.status_code == 200
        timeline = res_timeline.json()
        assert len(timeline) >= 2
        # Check recheck verification badge field
        assert any(t["candidate_id"] == cand1["id"] for t in timeline)

        # 9. GET /api/files/{candidate_id} (stream PDF)
        res_file = await client.get(f"/api/files/{cand1['id']}")
        assert res_file.status_code == 200
        assert res_file.headers["content-type"] == "application/pdf"
        assert res_file.content.startswith(b"%PDF")
