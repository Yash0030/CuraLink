"""Database repository for Personal Health Record Organizer.

Handles all persistence operations for runs, candidates, reports, events, and approvals.
Provides full PostgreSQL/Neon support with an in-memory fallback for offline test suites.
"""

import re
import uuid
import hashlib
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional
import json

from app.db.connection import get_db_pool

# In-memory store for offline/local fallback
_MEM_RUNS: Dict[str, Dict[str, Any]] = {}
_MEM_CANDIDATES: Dict[str, Dict[str, Any]] = {}
_MEM_REPORTS: Dict[str, Dict[str, Any]] = {}
_MEM_EVENTS: List[Dict[str, Any]] = []
_MEM_APPROVALS: Dict[str, Dict[str, Any]] = {}

def generate_patient_key(patient_name: str, patient_id: Optional[str] = None) -> str:
    """Generates a stable, normalized patient key for partitioning health records."""
    clean_name = re.sub(r"[^a-zA-Z0-9]+", "_", patient_name.strip().lower()).strip("_")
    if patient_id and patient_id.strip():
        clean_id = re.sub(r"[^a-zA-Z0-9]+", "_", patient_id.strip().lower()).strip("_")
        return f"{clean_name}_{clean_id}"
    return clean_name

class Repository:
    @staticmethod
    async def create_run(
        patient_name: str,
        patient_id: Optional[str],
        date_from: date,
        date_to: date,
        labs: List[str]
    ) -> Dict[str, Any]:
        run_id = str(uuid.uuid4())
        patient_key = generate_patient_key(patient_name, patient_id)
        now = datetime.now(timezone.utc)

        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO runs (id, patient_name, patient_id, patient_key, date_from, date_to, labs, status, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *
                            """,
                            (run_id, patient_name, patient_id, patient_key, date_from, date_to, labs, "pending", now, now)
                        )
                        row = await cur.fetchone()
                        await conn.commit()
                        return dict(row)
            except Exception as e:
                # Fall back to in-memory if DB fails
                pass

        data = {
            "id": run_id,
            "patient_name": patient_name,
            "patient_id": patient_id,
            "patient_key": patient_key,
            "date_from": date_from,
            "date_to": date_to,
            "labs": labs,
            "status": "pending",
            "error": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        _MEM_RUNS[run_id] = data
        return data

    @staticmethod
    async def get_run(run_id: str) -> Optional[Dict[str, Any]]:
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT * FROM runs WHERE id = %s", (run_id,))
                        row = await cur.fetchone()
                        if row:
                            return dict(row)
            except Exception:
                pass
        return _MEM_RUNS.get(run_id)

    @staticmethod
    async def list_runs() -> List[Dict[str, Any]]:
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT * FROM runs ORDER BY created_at DESC")
                        rows = await cur.fetchall()
                        return [dict(r) for r in rows]
            except Exception:
                pass
        runs = list(_MEM_RUNS.values())
        runs.sort(key=lambda x: str(x.get("created_at")), reverse=True)
        return runs

    @staticmethod
    async def update_run_status(run_id: str, status: str, error: Optional[str] = None):
        now = datetime.now(timezone.utc)
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "UPDATE runs SET status = %s, error = %s, updated_at = %s WHERE id = %s",
                            (status, error, now, run_id)
                        )
                        await conn.commit()
                        return
            except Exception:
                pass
        if run_id in _MEM_RUNS:
            _MEM_RUNS[run_id]["status"] = status
            _MEM_RUNS[run_id]["error"] = error
            _MEM_RUNS[run_id]["updated_at"] = now.isoformat()

    @staticmethod
    async def record_event(run_id: str, agent: str, level: str, message: str, data: Optional[Dict[str, Any]] = None):
        now = datetime.now(timezone.utc)
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO events (run_id, agent, level, message, data, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (run_id, agent, level, message, json.dumps(data) if data else None, now)
                        )
                        await conn.commit()
                        return
            except Exception:
                pass
        _MEM_EVENTS.append({
            "id": len(_MEM_EVENTS) + 1,
            "run_id": run_id,
            "agent": agent,
            "level": level,
            "message": message,
            "data": data,
            "created_at": now.isoformat()
        })

    @staticmethod
    async def get_events(run_id: str, after_id: int = 0) -> List[Dict[str, Any]]:
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "SELECT * FROM events WHERE run_id = %s AND id > %s ORDER BY id ASC",
                            (run_id, after_id)
                        )
                        rows = await cur.fetchall()
                        return [dict(r) for r in rows]
            except Exception:
                pass
        return [
            e for e in _MEM_EVENTS
            if e["run_id"] == run_id and e["id"] > after_id
        ]

    @staticmethod
    async def save_candidate(
        run_id: str,
        lab: str,
        filename: str,
        source_url: str,
        listing_title: str,
        portal_report_id: str,
        portal_date: Optional[date],
        file_bytes: bytes,
        http_status: int = 200,
        content_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        cand_id = str(uuid.uuid4())
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        size_bytes = len(file_bytes)
        now = datetime.now(timezone.utc)

        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO candidates (
                                id, run_id, lab, filename, source_url, listing_title,
                                portal_report_id, portal_date, fetched_at, http_status,
                                content_type, file_bytes, size_bytes, sha256, status
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'staging')
                            ON CONFLICT (run_id, lab, filename) DO UPDATE SET
                                fetched_at = EXCLUDED.fetched_at,
                                file_bytes = EXCLUDED.file_bytes,
                                size_bytes = EXCLUDED.size_bytes,
                                sha256 = EXCLUDED.sha256
                            RETURNING *
                            """,
                            (
                                cand_id, run_id, lab, filename, source_url, listing_title,
                                portal_report_id, portal_date, now, http_status,
                                content_type, file_bytes, size_bytes, sha256
                            )
                        )
                        row = await cur.fetchone()
                        await conn.commit()
                        return dict(row)
            except Exception:
                pass

        # In-memory storage
        cand_data = {
            "id": cand_id,
            "run_id": run_id,
            "lab": lab,
            "filename": filename,
            "source_url": source_url,
            "listing_title": listing_title,
            "portal_report_id": portal_report_id,
            "portal_date": portal_date,
            "fetched_at": now.isoformat(),
            "http_status": http_status,
            "content_type": content_type,
            "file_bytes": file_bytes,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "extract_ok": None,
            "extract_note": None,
            "extract_source": None,
            "x_name": None,
            "x_patient_id": None,
            "x_report_id": None,
            "x_date": None,
            "x_test": None,
            "legit_result": None,
            "duplicate_result": None,
            "decision": None,
            "decision_reason": None,
            "status": "staging",
            "recheck_ok": None,
            "recheck_note": None
        }
        # Enforce unique (run_id, lab, filename)
        for existing_id, item in list(_MEM_CANDIDATES.items()):
            if item["run_id"] == run_id and item["lab"] == lab and item["filename"] == filename:
                cand_data["id"] = existing_id
                _MEM_CANDIDATES[existing_id] = cand_data
                return cand_data

        _MEM_CANDIDATES[cand_id] = cand_data
        return cand_data

    @staticmethod
    async def get_candidate(candidate_id: str) -> Optional[Dict[str, Any]]:
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT * FROM candidates WHERE id = %s", (candidate_id,))
                        row = await cur.fetchone()
                        if row:
                            return dict(row)
            except Exception:
                pass
        return _MEM_CANDIDATES.get(candidate_id)

    @staticmethod
    async def get_candidates_for_run(run_id: str) -> List[Dict[str, Any]]:
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT * FROM candidates WHERE run_id = %s ORDER BY lab, filename", (run_id,))
                        rows = await cur.fetchall()
                        return [dict(r) for r in rows]
            except Exception:
                pass
        return [c for c in _MEM_CANDIDATES.values() if c["run_id"] == run_id]

    @staticmethod
    async def update_candidate_extraction(
        candidate_id: str,
        extract_ok: bool,
        extract_note: str,
        extract_source: str,
        x_name: Optional[str],
        x_patient_id: Optional[str],
        x_report_id: Optional[str],
        x_date: Optional[date],
        x_test: Optional[str]
    ):
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            UPDATE candidates SET
                                extract_ok = %s,
                                extract_note = %s,
                                extract_source = %s,
                                x_name = %s,
                                x_patient_id = %s,
                                x_report_id = %s,
                                x_date = %s,
                                x_test = %s
                            WHERE id = %s
                            """,
                            (extract_ok, extract_note, extract_source, x_name, x_patient_id, x_report_id, x_date, x_test, candidate_id)
                        )
                        await conn.commit()
                        return
            except Exception:
                pass
        if candidate_id in _MEM_CANDIDATES:
            _MEM_CANDIDATES[candidate_id].update({
                "extract_ok": extract_ok,
                "extract_note": extract_note,
                "extract_source": extract_source,
                "x_name": x_name,
                "x_patient_id": x_patient_id,
                "x_report_id": x_report_id,
                "x_date": x_date,
                "x_test": x_test
            })

    @staticmethod
    async def update_candidate_check(
        candidate_id: str,
        legit_result: Dict[str, Any],
        duplicate_result: Dict[str, Any],
        decision: str,
        decision_reason: str
    ):
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            UPDATE candidates SET
                                legit_result = %s,
                                duplicate_result = %s,
                                decision = %s,
                                decision_reason = %s
                            WHERE id = %s
                            """,
                            (json.dumps(legit_result), json.dumps(duplicate_result), decision, decision_reason, candidate_id)
                        )
                        await conn.commit()
                        return
            except Exception:
                pass
        if candidate_id in _MEM_CANDIDATES:
            _MEM_CANDIDATES[candidate_id].update({
                "legit_result": legit_result,
                "duplicate_result": duplicate_result,
                "decision": decision,
                "decision_reason": decision_reason
            })

    @staticmethod
    async def get_stored_reports(patient_key: str) -> List[Dict[str, Any]]:
        """Returns all permanent reports stored for the given patient key."""
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "SELECT * FROM reports WHERE patient_key = %s ORDER BY report_date DESC",
                            (patient_key,)
                        )
                        rows = await cur.fetchall()
                        return [dict(r) for r in rows]
            except Exception:
                pass
        return [r for r in _MEM_REPORTS.values() if r["patient_key"] == patient_key]

    @staticmethod
    async def record_approval(run_id: str, approved: bool, overrides: Dict[str, str]):
        app_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO approvals (id, run_id, approved, overrides, created_at)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (app_id, run_id, approved, json.dumps(overrides), now)
                        )
                        await conn.commit()
                        return
            except Exception:
                pass
        _MEM_APPROVALS[run_id] = {
            "id": app_id,
            "run_id": run_id,
            "approved": approved,
            "overrides": overrides,
            "created_at": now.isoformat()
        }

    @staticmethod
    async def store_approved_candidate(
        candidate_id: str,
        patient_key: str,
        lab: str,
        report_id: str,
        test_name: str,
        report_date: date,
        sha256: str
    ) -> bool:
        """Stores candidate into reports table. Idempotent via UNIQUE (patient_key, report_id) and UNIQUE (patient_key, sha256)."""
        rep_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO reports (id, candidate_id, patient_key, lab, report_id, test_name, report_date, sha256, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                            RETURNING id
                            """,
                            (rep_id, candidate_id, patient_key, lab, report_id, test_name, report_date, sha256, now)
                        )
                        row = await cur.fetchone()
                        await cur.execute(
                            "UPDATE candidates SET status = 'stored' WHERE id = %s",
                            (candidate_id,)
                        )
                        await conn.commit()
                        return bool(row)
            except Exception:
                pass

        # In-memory store
        for existing in _MEM_REPORTS.values():
            if existing["patient_key"] == patient_key and (
                existing["report_id"] == report_id or existing["sha256"] == sha256
            ):
                if candidate_id in _MEM_CANDIDATES:
                    _MEM_CANDIDATES[candidate_id]["status"] = "not_stored"
                return False

        _MEM_REPORTS[rep_id] = {
            "id": rep_id,
            "candidate_id": candidate_id,
            "patient_key": patient_key,
            "lab": lab,
            "report_id": report_id,
            "test_name": test_name,
            "report_date": report_date,
            "sha256": sha256,
            "created_at": now.isoformat()
        }
        if candidate_id in _MEM_CANDIDATES:
            _MEM_CANDIDATES[candidate_id]["status"] = "stored"
        return True

    @staticmethod
    async def mark_candidate_not_stored(candidate_id: str):
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "UPDATE candidates SET status = 'not_stored' WHERE id = %s",
                            (candidate_id,)
                        )
                        await conn.commit()
                        return
            except Exception:
                pass
        if candidate_id in _MEM_CANDIDATES:
            _MEM_CANDIDATES[candidate_id]["status"] = "not_stored"

    @staticmethod
    async def update_candidate_recheck(candidate_id: str, recheck_ok: bool, recheck_note: str):
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "UPDATE candidates SET recheck_ok = %s, recheck_note = %s WHERE id = %s",
                            (recheck_ok, recheck_note, candidate_id)
                        )
                        await conn.commit()
                        return
            except Exception:
                pass
        if candidate_id in _MEM_CANDIDATES:
            _MEM_CANDIDATES[candidate_id]["recheck_ok"] = recheck_ok
            _MEM_CANDIDATES[candidate_id]["recheck_note"] = recheck_note

    @staticmethod
    async def get_timeline(patient_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns sorted health timeline joined with candidate verification metadata."""
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        query = """
                            SELECT
                                r.id AS report_uuid,
                                r.candidate_id,
                                r.patient_key,
                                r.lab,
                                r.report_id,
                                r.test_name,
                                r.report_date,
                                r.sha256,
                                r.created_at,
                                c.filename,
                                c.x_name,
                                c.x_patient_id,
                                c.recheck_ok,
                                c.recheck_note
                            FROM reports r
                            LEFT JOIN candidates c ON r.candidate_id = c.id
                        """
                        params = []
                        if patient_key:
                            query += " WHERE r.patient_key = %s"
                            params.append(patient_key)
                        query += " ORDER BY r.report_date DESC, r.created_at DESC"
                        await cur.execute(query, tuple(params))
                        rows = await cur.fetchall()
                        return [dict(row) for row in rows]
            except Exception:
                pass

        timeline = []
        for rep in _MEM_REPORTS.values():
            if patient_key and rep["patient_key"] != patient_key:
                continue
            cand = _MEM_CANDIDATES.get(rep.get("candidate_id", ""), {})
            timeline.append({
                "report_uuid": rep["id"],
                "candidate_id": rep.get("candidate_id"),
                "patient_key": rep["patient_key"],
                "lab": rep["lab"],
                "report_id": rep["report_id"],
                "test_name": rep["test_name"],
                "report_date": rep["report_date"],
                "sha256": rep["sha256"],
                "created_at": rep["created_at"],
                "filename": cand.get("filename"),
                "x_name": cand.get("x_name"),
                "x_patient_id": cand.get("x_patient_id"),
                "recheck_ok": cand.get("recheck_ok"),
                "recheck_note": cand.get("recheck_note")
            })
        timeline.sort(key=lambda x: str(x.get("report_date", "")), reverse=True)
        return timeline
