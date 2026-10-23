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
import logging

logger = logging.getLogger(__name__)

from app.db.connection import get_db_pool

# In-memory store for offline/local fallback
_MEM_USERS: Dict[str, Dict[str, Any]] = {}
_MEM_SESSIONS: Dict[str, Dict[str, Any]] = {}
_MEM_USER_LABS: Dict[str, List[Dict[str, Any]]] = {}
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
    # --- User Authentication & Session Persistence ---

    @staticmethod
    async def create_user(name: str, email: str, password_hash: str) -> Dict[str, Any]:
        """Creates a new user account."""
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        clean_email = email.lower().strip()
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO phr.users (id, name, email, password_hash, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            RETURNING id, name, email, created_at
                            """,
                            (user_id, name.strip(), clean_email, password_hash, now, now)
                        )
                        row = await cur.fetchone()
                        await conn.commit()
                        res = dict(row)
                        res["id"] = str(res["id"])
                        return res
            except Exception as e:
                # Fall back to in-memory if DB fails
                pass

        data = {
            "id": user_id,
            "name": name.strip(),
            "email": clean_email,
            "password_hash": password_hash,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        _MEM_USERS[user_id] = data
        return {"id": user_id, "name": name.strip(), "email": clean_email, "created_at": data["created_at"]}

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Finds user by email address."""
        clean_email = email.lower().strip()
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT * FROM phr.users WHERE LOWER(email) = %s", (clean_email,))
                        row = await cur.fetchone()
                        if row:
                            res = dict(row)
                            res["id"] = str(res["id"])
                            return res
            except Exception:
                pass
        for u in _MEM_USERS.values():
            if u["email"].lower() == clean_email:
                return u
        return None

    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves user profile by ID."""
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT id, name, email, created_at FROM phr.users WHERE id = %s", (user_id,))
                        row = await cur.fetchone()
                        if row:
                            res = dict(row)
                            res["id"] = str(res["id"])
                            return res
            except Exception:
                pass
        u = _MEM_USERS.get(user_id)
        if u:
            return {"id": u["id"], "name": u["name"], "email": u["email"], "created_at": u["created_at"]}
        return None

    @staticmethod
    async def create_session(user_id: str, token_hash: str, expires_at: datetime) -> Dict[str, Any]:
        """Creates an authenticated session token for the user."""
        now = datetime.now(timezone.utc)
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO phr.auth_sessions (token_hash, user_id, expires_at, created_at)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (token_hash) DO UPDATE SET expires_at = EXCLUDED.expires_at
                            RETURNING *
                            """,
                            (token_hash, user_id, expires_at, now)
                        )
                        row = await cur.fetchone()
                        await conn.commit()
                        return dict(row)
            except Exception:
                pass
        _MEM_SESSIONS[token_hash] = {
            "token_hash": token_hash,
            "user_id": user_id,
            "expires_at": expires_at,
            "created_at": now
        }
        return _MEM_SESSIONS[token_hash]

    @staticmethod
    async def get_user_by_session_token(token: str) -> Optional[Dict[str, Any]]:
        """Resolves user profile from a bearer session token."""
        token_h = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc)
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            SELECT u.id, u.name, u.email, u.created_at
                            FROM phr.auth_sessions s
                            JOIN phr.users u ON s.user_id = u.id
                            WHERE s.token_hash = %s AND s.expires_at > %s
                            """,
                            (token_h, now)
                        )
                        row = await cur.fetchone()
                        if row:
                            res = dict(row)
                            res["id"] = str(res["id"])
                            return res
            except Exception:
                pass
        sess = _MEM_SESSIONS.get(token_h)
        if sess and sess["expires_at"] > now:
            return await Repository.get_user_by_id(sess["user_id"])
        return None

    @staticmethod
    async def delete_session(token: str) -> bool:
        """Invalidates a session token (logout)."""
        token_h = hashlib.sha256(token.encode("utf-8")).hexdigest()
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("DELETE FROM phr.auth_sessions WHERE token_hash = %s", (token_h,))
                        await conn.commit()
                        return True
            except Exception:
                pass
        if token_h in _MEM_SESSIONS:
            del _MEM_SESSIONS[token_h]
            return True
        return False

    @staticmethod
    async def get_default_test_user() -> Dict[str, Any]:
        """Provides a default user for offline test suites."""
        user = await Repository.get_user_by_email("test@example.com")
        if user:
            return user
        try:
            return await Repository.create_user("Test User", "test@example.com", "$2b$12$dummyhashfortestingonly")
        except Exception:
            return {"id": "00000000-0000-0000-0000-000000000001", "name": "Test User", "email": "test@example.com"}

    # --- Custom User Labs Persistence ---

    @staticmethod
    async def get_user_labs(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns custom lab portals configured by the user."""
        if not user_id:
            return []
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "SELECT id, key, name, url, username, password, layout, has_captcha, created_at FROM phr.user_labs WHERE user_id = %s ORDER BY created_at ASC",
                            (user_id,)
                        )
                        rows = await cur.fetchall()
                        res = []
                        for r in rows:
                            item = dict(r)
                            item["id"] = str(item["id"])
                            item["is_custom"] = True
                            res.append(item)
                        return res
            except Exception:
                pass
        return [dict(l) for l in _MEM_USER_LABS.get(user_id, [])]

    @staticmethod
    async def create_user_lab(
        user_id: str,
        name: str,
        url: str,
        username: str = "",
        password: str = "",
        layout: str = "table",
        has_captcha: bool = False
    ) -> Dict[str, Any]:
        """Adds a custom lab portal for the user."""
        lab_id = str(uuid.uuid4())
        clean_name = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
        key = f"custom_{clean_name}_{lab_id[:6]}"
        now = datetime.now(timezone.utc)
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO phr.user_labs (id, user_id, key, name, url, username, password, layout, has_captcha, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id, key, name, url, username, password, layout, has_captcha, created_at
                            """,
                            (lab_id, user_id, key, name.strip(), url.strip(), username, password, layout, has_captcha, now)
                        )
                        row = await cur.fetchone()
                        await conn.commit()
                        res = dict(row)
                        res["id"] = str(res["id"])
                        res["is_custom"] = True
                        return res
            except Exception as e:
                pass

        data = {
            "id": lab_id,
            "user_id": user_id,
            "key": key,
            "name": name.strip(),
            "url": url.strip(),
            "username": username,
            "password": password,
            "layout": layout,
            "has_captcha": has_captcha,
            "created_at": now.isoformat(),
            "is_custom": True
        }
        _MEM_USER_LABS.setdefault(user_id, []).append(data)
        return data

    @staticmethod
    async def delete_user_lab(user_id: str, key: str) -> bool:
        """Deletes a custom lab portal created by the user."""
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "DELETE FROM phr.user_labs WHERE user_id = %s AND key = %s",
                            (user_id, key)
                        )
                        await conn.commit()
                        return True
            except Exception:
                pass
        if user_id in _MEM_USER_LABS:
            _MEM_USER_LABS[user_id] = [l for l in _MEM_USER_LABS[user_id] if l["key"] != key]
            return True
        return False

    @staticmethod
    async def get_lab_config(key: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Finds custom lab configuration by key."""
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        if user_id:
                            await cur.execute("SELECT * FROM phr.user_labs WHERE key = %s AND user_id = %s", (key, user_id))
                        else:
                            await cur.execute("SELECT * FROM phr.user_labs WHERE key = %s", (key,))
                        row = await cur.fetchone()
                        if row:
                            res = dict(row)
                            res["id"] = str(res["id"])
                            res["is_custom"] = True
                            return res
            except Exception:
                pass
        for labs_list in _MEM_USER_LABS.values():
            for l in labs_list:
                if l["key"] == key:
                    return l
        return None

    # --- Run Orchestration (Scoped to User) ---

    @staticmethod
    async def create_run(
        patient_name: str,
        patient_id: Optional[str],
        date_from: date,
        date_to: date,
        labs: List[str],
        user_id: Optional[str] = None
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
                            INSERT INTO phr.runs (id, user_id, patient_name, patient_id, patient_key, date_from, date_to, labs, status, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING *
                            """,
                            (run_id, user_id, patient_name, patient_id, patient_key, date_from, date_to, labs, "pending", now, now)
                        )
                        row = await cur.fetchone()
                        await conn.commit()
                        res = dict(row)
                        res["id"] = str(res["id"])
                        return res
            except Exception as e:
                pass

        data = {
            "id": run_id,
            "user_id": user_id,
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
    async def get_run(run_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        if user_id:
                            await cur.execute("SELECT * FROM phr.runs WHERE id = %s AND (user_id = %s OR user_id IS NULL)", (run_id, user_id))
                        else:
                            await cur.execute("SELECT * FROM phr.runs WHERE id = %s", (run_id,))
                        row = await cur.fetchone()
                        if row:
                            res = dict(row)
                            res["id"] = str(res["id"])
                            return res
            except Exception:
                pass
        r = _MEM_RUNS.get(run_id)
        if r and (not user_id or not r.get("user_id") or r.get("user_id") == user_id):
            return r
        return None

    @staticmethod
    async def list_runs(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        if user_id:
                            await cur.execute("SELECT * FROM phr.runs WHERE (user_id = %s OR user_id IS NULL) ORDER BY created_at DESC", (user_id,))
                        else:
                            await cur.execute("SELECT * FROM phr.runs ORDER BY created_at DESC")
                        rows = await cur.fetchall()
                        res = []
                        for r in rows:
                            item = dict(r)
                            item["id"] = str(item["id"])
                            res.append(item)
                        return res
            except Exception:
                pass
        runs = [r for r in _MEM_RUNS.values() if not user_id or not r.get("user_id") or r.get("user_id") == user_id]
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
                            "UPDATE phr.runs SET status = %s, error = %s, updated_at = %s WHERE id = %s",
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
    async def delete_run(run_id: str, user_id: Optional[str] = None) -> bool:
        """Deletes a run and cascades to candidates, events, approvals, and associated reports."""
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        if user_id:
                            await cur.execute(
                                "SELECT id FROM phr.runs WHERE id = %s AND (user_id = %s OR user_id IS NULL)",
                                (run_id, user_id)
                            )
                        else:
                            await cur.execute("SELECT id FROM phr.runs WHERE id = %s", (run_id,))
                        row = await cur.fetchone()
                        if not row:
                            return False

                        # Delete reports generated from candidates belonging to this run
                        await cur.execute(
                            "DELETE FROM phr.reports WHERE candidate_id IN (SELECT id FROM phr.candidates WHERE run_id = %s)",
                            (run_id,)
                        )
                        # Delete the run itself (phr.candidates, phr.events, phr.approvals cascade)
                        await cur.execute("DELETE FROM phr.runs WHERE id = %s", (run_id,))
                        await conn.commit()
                        return True
            except Exception as e:
                logger.error(f"Error deleting run {run_id} from database: {e}")
                pass

        # In-memory fallback
        if run_id in _MEM_RUNS:
            r = _MEM_RUNS[run_id]
            if user_id and r.get("user_id") and r.get("user_id") != user_id:
                return False
            cand_ids = [cid for cid, c in _MEM_CANDIDATES.items() if c.get("run_id") == run_id]
            for cid in cand_ids:
                _MEM_CANDIDATES.pop(cid, None)
                rep_ids = [rid for rid, rep in _MEM_REPORTS.items() if rep.get("candidate_id") == cid]
                for rid in rep_ids:
                    _MEM_REPORTS.pop(rid, None)
            global _MEM_EVENTS
            _MEM_EVENTS = [e for e in _MEM_EVENTS if e.get("run_id") != run_id]
            _MEM_APPROVALS.pop(run_id, None)
            del _MEM_RUNS[run_id]
            return True
        return False

    @staticmethod
    async def delete_runs(run_ids: List[str], user_id: Optional[str] = None) -> int:
        """Deletes multiple runs by ID."""
        count = 0
        for rid in run_ids:
            if await Repository.delete_run(rid, user_id=user_id):
                count += 1
        return count

    @staticmethod
    async def clear_all_runs(user_id: Optional[str] = None) -> int:
        """Deletes all runs for the specified user or all runs if unauthenticated."""
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        if user_id:
                            await cur.execute("SELECT id FROM phr.runs WHERE (user_id = %s OR user_id IS NULL)", (user_id,))
                        else:
                            await cur.execute("SELECT id FROM phr.runs")
                        rows = await cur.fetchall()
                        run_ids = [str(r["id"]) for r in rows]
                        for rid in run_ids:
                            await cur.execute(
                                "DELETE FROM phr.reports WHERE candidate_id IN (SELECT id FROM phr.candidates WHERE run_id = %s)",
                                (rid,)
                            )
                            await cur.execute("DELETE FROM phr.runs WHERE id = %s", (rid,))
                        await conn.commit()
                        return len(run_ids)
            except Exception as e:
                logger.error(f"Error clearing runs from database: {e}")
                pass

        runs_to_delete = [
            rid for rid, r in _MEM_RUNS.items()
            if not user_id or not r.get("user_id") or r.get("user_id") == user_id
        ]
        count = 0
        for rid in runs_to_delete:
            if await Repository.delete_run(rid, user_id=user_id):
                count += 1
        return count

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
                            INSERT INTO phr.events (run_id, agent, level, message, data, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (run_id, agent, level, message, json.dumps(data) if data else None, now)
                        )
                        await conn.commit()
                        return
            except Exception as e:
                logger.warning(f"Failed to record event to Postgres ({e}), saving to in-memory event buffer.")
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
                            "SELECT * FROM phr.events WHERE run_id = %s AND id > %s ORDER BY id ASC",
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
                            INSERT INTO phr.candidates (
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
                        res = dict(row)
                        res["id"] = str(res["id"])
                        if res.get("run_id"):
                            res["run_id"] = str(res["run_id"])
                        return res
            except Exception as e:
                logger.warning(f"Failed to save candidate to Postgres ({e}), using in-memory store.")

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
                        await cur.execute("SELECT * FROM phr.candidates WHERE id::text = %s", (candidate_id,))
                        row = await cur.fetchone()
                        if not row:
                            await cur.execute(
                                """
                                SELECT c.* FROM phr.candidates c
                                JOIN phr.reports r ON (r.candidate_id = c.id OR r.sha256 = c.sha256 OR (r.lab = c.lab AND r.report_id = c.portal_report_id))
                                WHERE r.id::text = %s OR r.candidate_id::text = %s OR r.report_id = %s
                                LIMIT 1
                                """,
                                (candidate_id, candidate_id, candidate_id)
                            )
                            row = await cur.fetchone()
                        if row:
                            d = dict(row)
                            d["id"] = str(d["id"])
                            if d.get("run_id"):
                                d["run_id"] = str(d["run_id"])
                            return d
            except Exception as e:
                logger.warning(f"Error querying candidate by id/report {candidate_id}: {e}")

        if candidate_id in _MEM_CANDIDATES:
            return _MEM_CANDIDATES[candidate_id]
        for rep in _MEM_REPORTS.values():
            if rep.get("id") == candidate_id or rep.get("candidate_id") == candidate_id or rep.get("report_uuid") == candidate_id:
                cid = rep.get("candidate_id")
                if cid and cid in _MEM_CANDIDATES:
                    return _MEM_CANDIDATES[cid]
        return None

    @staticmethod
    async def get_candidates_for_run(run_id: str) -> List[Dict[str, Any]]:
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT * FROM phr.candidates WHERE run_id = %s ORDER BY lab, filename", (run_id,))
                        rows = await cur.fetchall()
                        result = []
                        for r in rows:
                            d = dict(r)
                            d["id"] = str(d["id"])
                            if d.get("run_id"):
                                d["run_id"] = str(d["run_id"])
                            result.append(d)
                        return result
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
                            UPDATE phr.candidates SET
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
        legit_json = json.dumps(legit_result, default=str) if legit_result is not None else None
        dup_json = json.dumps(duplicate_result, default=str) if duplicate_result is not None else None
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            UPDATE phr.candidates SET
                                legit_result = %s,
                                duplicate_result = %s,
                                decision = %s,
                                decision_reason = %s
                            WHERE id = %s
                            """,
                            (legit_json, dup_json, decision, decision_reason, candidate_id)
                        )
                        await conn.commit()
                        return
            except Exception as e:
                import logging
                logging.getLogger("phr-organizer.repo").error(f"Failed to update candidate check ({e})")
        if candidate_id in _MEM_CANDIDATES:
            _MEM_CANDIDATES[candidate_id].update({
                "legit_result": legit_result,
                "duplicate_result": duplicate_result,
                "decision": decision,
                "decision_reason": decision_reason
            })

    @staticmethod
    async def get_stored_reports(patient_key: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all permanent reports stored for the given patient key and user."""
        clean_prefix = patient_key.split('_')[0] if patient_key else ""
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        if user_id:
                            await cur.execute(
                                """
                                SELECT * FROM phr.reports 
                                WHERE (user_id = %s OR user_id IS NULL)
                                  AND (
                                    patient_key = %s 
                                    OR patient_key LIKE %s
                                    OR %s LIKE patient_key || '%%'
                                  )
                                ORDER BY report_date DESC
                                """,
                                (user_id, patient_key, f"{clean_prefix}%", patient_key)
                            )
                        else:
                            await cur.execute(
                                """
                                SELECT * FROM phr.reports 
                                WHERE (
                                    patient_key = %s 
                                    OR patient_key LIKE %s
                                    OR %s LIKE patient_key || '%%'
                                )
                                ORDER BY report_date DESC
                                """,
                                (patient_key, f"{clean_prefix}%", patient_key)
                            )
                        rows = await cur.fetchall()
                        return [dict(r) for r in rows]
            except Exception as e:
                logger.error(f"Error fetching stored reports: {e}")
                pass
        return [
            r for r in _MEM_REPORTS.values()
            if (
                r["patient_key"] == patient_key
                or r["patient_key"].startswith(clean_prefix)
                or patient_key.startswith(r["patient_key"])
            ) and (not user_id or not r.get("user_id") or r.get("user_id") == user_id)
        ]

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
                            INSERT INTO phr.approvals (id, run_id, approved, overrides, created_at)
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
        sha256: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Stores candidate into reports table with user isolation and strict deduplication."""
        rep_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        # Pre-check: Avoid duplicate report insertion for same user/patient
                        if user_id:
                            await cur.execute(
                                """
                                SELECT id FROM phr.reports 
                                WHERE (user_id = %s OR user_id IS NULL)
                                  AND (sha256 = %s OR (lab = %s AND report_id = %s))
                                LIMIT 1
                                """,
                                (user_id, sha256, lab, report_id)
                            )
                        else:
                            await cur.execute(
                                """
                                SELECT id FROM phr.reports 
                                WHERE (sha256 = %s OR (lab = %s AND report_id = %s))
                                LIMIT 1
                                """,
                                (sha256, lab, report_id)
                            )
                        existing_row = await cur.fetchone()
                        if existing_row:
                            logger.info(f"Duplicate report detected for {lab}/{report_id} ({sha256[:8]}). Linking candidate without duplicating report row.")
                            await cur.execute(
                                """
                                UPDATE phr.reports 
                                SET candidate_id = COALESCE(candidate_id, %s)
                                WHERE id = %s
                                """,
                                (candidate_id, existing_row["id"])
                            )
                            await cur.execute(
                                "UPDATE phr.candidates SET status = 'stored' WHERE id = %s",
                                (candidate_id,)
                            )
                            await conn.commit()
                            return True

                        await cur.execute(
                            """
                            INSERT INTO phr.reports (id, user_id, candidate_id, patient_key, lab, report_id, test_name, report_date, sha256, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                            RETURNING id
                            """,
                            (rep_id, user_id, candidate_id, patient_key, lab, report_id, test_name, report_date, sha256, now)
                        )
                        row = await cur.fetchone()
                        await cur.execute(
                            "UPDATE phr.candidates SET status = 'stored' WHERE id = %s",
                            (candidate_id,)
                        )
                        await conn.commit()
                        return True
            except Exception as e:
                logger.error(f"Error storing candidate {candidate_id}: {e}")
                pass

        # In-memory store
        for existing in _MEM_REPORTS.values():
            if (not user_id or not existing.get("user_id") or existing.get("user_id") == user_id) and (
                existing["report_id"] == report_id or existing["sha256"] == sha256
            ):
                if candidate_id in _MEM_CANDIDATES:
                    _MEM_CANDIDATES[candidate_id]["status"] = "stored"
                return True

        _MEM_REPORTS[rep_id] = {
            "id": rep_id,
            "user_id": user_id,
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
                            "UPDATE phr.candidates SET status = 'not_stored' WHERE id = %s",
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
                            "UPDATE phr.candidates SET recheck_ok = %s, recheck_note = %s WHERE id = %s",
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
    async def get_timeline(patient_key: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns sorted health timeline joined with candidate verification metadata scoped to user."""
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        query = """
                            SELECT
                                r.id AS report_uuid,
                                r.user_id,
                                COALESCE(r.candidate_id, c.id) AS candidate_id,
                                r.patient_key,
                                r.lab,
                                r.report_id,
                                r.test_name,
                                r.report_date,
                                r.sha256,
                                r.created_at,
                                COALESCE(c.filename, r.report_id || '.pdf') AS filename,
                                COALESCE(c.x_name, r.patient_key) AS x_name,
                                c.x_patient_id,
                                COALESCE(c.recheck_ok, true) AS recheck_ok,
                                c.recheck_note
                            FROM phr.reports r
                            LEFT JOIN phr.candidates c ON (
                                r.candidate_id = c.id 
                                OR r.sha256 = c.sha256 
                                OR (r.lab = c.lab AND r.report_id = c.portal_report_id)
                            )
                        """
                        where_clauses = []
                        params = []
                        if patient_key:
                            where_clauses.append("r.patient_key = %s")
                            params.append(patient_key)
                        if user_id:
                            where_clauses.append("(r.user_id = %s OR r.user_id IS NULL)")
                            params.append(user_id)
                        if where_clauses:
                            query += " WHERE " + " AND ".join(where_clauses)
                        query += " ORDER BY r.report_date DESC, r.created_at DESC"
                        await cur.execute(query, tuple(params))
                        rows = await cur.fetchall()
                        seen_hashes = set()
                        deduped = []
                        for row in rows:
                            row_dict = dict(row)
                            h = row_dict.get("sha256")
                            if h and h in seen_hashes:
                                continue
                            if h:
                                seen_hashes.add(h)
                            deduped.append(row_dict)
                        return deduped
            except Exception:
                pass

        timeline = []
        for rep in _MEM_REPORTS.values():
            if patient_key and rep["patient_key"] != patient_key:
                continue
            if user_id and rep.get("user_id") and rep["user_id"] != user_id:
                continue
            cand = _MEM_CANDIDATES.get(rep.get("candidate_id", ""), {})
            timeline.append({
                "report_uuid": rep["id"],
                "user_id": rep.get("user_id"),
                "candidate_id": rep.get("candidate_id") or cand.get("id"),
                "patient_key": rep["patient_key"],
                "lab": rep["lab"],
                "report_id": rep["report_id"],
                "test_name": rep["test_name"],
                "report_date": rep["report_date"],
                "sha256": rep["sha256"],
                "created_at": rep["created_at"],
                "filename": cand.get("filename") or f"{rep['report_id']}.pdf",
                "x_name": cand.get("x_name") or rep["patient_key"],
                "x_patient_id": cand.get("x_patient_id"),
                "recheck_ok": cand.get("recheck_ok", True),
                "recheck_note": cand.get("recheck_note")
            })
        timeline.sort(key=lambda x: str(x.get("report_date", "")), reverse=True)
        return timeline

    @staticmethod
    async def delete_timeline_report(report_id: str, user_id: Optional[str] = None) -> bool:
        """Deletes a single health report from the timeline."""
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        if user_id:
                            await cur.execute(
                                "DELETE FROM phr.reports WHERE id = %s AND (user_id = %s OR user_id IS NULL) RETURNING id",
                                (report_id, user_id)
                            )
                        else:
                            await cur.execute(
                                "DELETE FROM phr.reports WHERE id = %s RETURNING id",
                                (report_id,)
                            )
                        row = await cur.fetchone()
                        await conn.commit()
                        return bool(row)
            except Exception as e:
                logger.error(f"Error deleting report {report_id}: {e}")
                pass

        if report_id in _MEM_REPORTS:
            rep = _MEM_REPORTS[report_id]
            if user_id and rep.get("user_id") and rep["user_id"] != user_id:
                return False
            del _MEM_REPORTS[report_id]
            return True
        return False

    @staticmethod
    async def delete_timeline_reports(report_ids: List[str], user_id: Optional[str] = None) -> int:
        """Deletes multiple selected reports from the timeline."""
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        if user_id:
                            await cur.execute(
                                "DELETE FROM phr.reports WHERE id = ANY(%s) AND (user_id = %s OR user_id IS NULL) RETURNING id",
                                (report_ids, user_id)
                            )
                        else:
                            await cur.execute(
                                "DELETE FROM phr.reports WHERE id = ANY(%s) RETURNING id",
                                (report_ids,)
                            )
                        rows = await cur.fetchall()
                        await conn.commit()
                        return len(rows)
            except Exception as e:
                logger.error(f"Error deleting batch reports: {e}")
                pass

        count = 0
        for rid in report_ids:
            if await Repository.delete_timeline_report(rid, user_id=user_id):
                count += 1
        return count

    @staticmethod
    async def clear_all_timeline(user_id: Optional[str] = None) -> int:
        """Clears all health reports from the timeline."""
        pool = get_db_pool()
        if pool and not pool.closed:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        if user_id:
                            await cur.execute(
                                "DELETE FROM phr.reports WHERE (user_id = %s OR user_id IS NULL) RETURNING id",
                                (user_id,)
                            )
                        else:
                            await cur.execute("DELETE FROM phr.reports RETURNING id")
                        rows = await cur.fetchall()
                        await conn.commit()
                        return len(rows)
            except Exception as e:
                logger.error(f"Error clearing timeline: {e}")
                pass

        global _MEM_REPORTS
        initial_len = len(_MEM_REPORTS)
        if user_id:
            _MEM_REPORTS = {rid: r for rid, r in _MEM_REPORTS.items() if r.get("user_id") and r["user_id"] != user_id}
            return initial_len - len(_MEM_REPORTS)
        else:
            _MEM_REPORTS = {}
            return initial_len
