"""FastAPI backend application for Personal Health Record Organizer.

Endpoints:
- GET /health
- GET /api/labs
- POST /api/runs (patient, dates, per-lab logins)
- GET /api/runs
- GET /api/runs/{id} (status, decision counts, waiting CAPTCHAs)
- GET /api/runs/{id}/events?after=
- GET /api/runs/{id}/candidates
- GET /api/runs/{id}/captcha/{lab}/image
- POST /api/runs/{id}/captcha/{lab}
- POST /api/runs/{id}/approve (approved, overrides)
- GET /api/timeline?patient_key=
- GET /api/files/{candidate_id} (streams PDF)
"""

import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import io
import logging
from datetime import date, datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, Query, BackgroundTasks, Depends, Request
from app.auth import (
    hash_password,
    verify_password,
    generate_session_token,
    hash_token,
    get_current_user,
    get_current_user_optional
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.db.connection import init_pool, close_pool
from app.db.repository import Repository
from app.tools.captcha_manager import CaptchaManager
from app.portal_selectors import PORTAL_CONFIG
from app.graph.state import HealthRecordGraphState
from app.graph.checkpointer import get_checkpointer
from app.graph.workflow import (
    create_health_record_graph,
    set_transient_credentials,
    wipe_transient_credentials,
    store,
    recheck_saved_files,
    build_timeline,
    rebuild_run_context
)
from app.mock_portal.server import mock_portal_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("phr-organizer")

# Active running graphs memory reference (run_id -> task / future)
_RUNNING_GRAPH_THREADS: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Personal Health Record Organizer Backend...")
    await init_pool()
    yield
    logger.info("Shutting down backend and closing database pools...")
    await close_pool()

app = FastAPI(
    title="Personal Health Record Organizer API",
    description="Local Agentic AI Health Record Organizer for Ziro Hackathon 2026",
    version="1.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        *settings.cors_origins_list,
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Mock Portal router directly so /{lab}/login, /{lab}/reports, and /{lab}/download/{filename}
# are served directly from the root of the FastAPI server without mounting path discrepancies.
app.include_router(mock_portal_app.router)
app.mount("/portal", mock_portal_app)

# Request logging middleware for comprehensive visibility
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = datetime.now()
    path = request.url.path
    method = request.method
    # Skip verbose logging for high-frequency poll endpoints to keep terminal clean
    is_poll = path.endswith("/events") or path.endswith("/candidates") or path.endswith("/health")

    if not is_poll:
        logger.info(f"--> [{method}] {path}")

    try:
        response = await call_next(request)
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        if not is_poll or response.status_code >= 400:
            logger.info(f"<-- [{method}] {path} completed with status {response.status_code} ({duration_ms:.1f}ms)")
        return response
    except Exception as e:
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.error(f"<-- [{method}] {path} failed with exception after {duration_ms:.1f}ms: {e}", exc_info=True)
        raise

# --- Pydantic Schemas ---

class UserSignUpRequest(BaseModel):
    name: str
    email: str
    password: str

class UserLoginRequest(BaseModel):
    email: str
    password: str

class AddLabRequest(BaseModel):
    name: str
    url: str
    username: str = ""
    password: str = ""
    layout: str = "table"

class LabLoginInfo(BaseModel):
    enabled: bool = True
    username: str = ""
    password: str = ""

class CreateRunRequest(BaseModel):
    patient_name: str
    patient_id: Optional[str] = None
    date_from: date
    date_to: date
    logins: Dict[str, LabLoginInfo]

class CaptchaSubmitRequest(BaseModel):
    answer: Optional[str] = None
    solved_live: bool = False

class ApproveRunRequest(BaseModel):
    approved: bool
    overrides: Dict[str, str] = Field(default_factory=dict)

# --- Background Graph Runner ---

async def execute_run_workflow(run_id: str, initial_state: HealthRecordGraphState):
    """Executes the compiled LangGraph workflow asynchronously with rich progress logging."""
    logger.info(f"[Run {run_id}] Initializing workflow for patient '{initial_state.patient_name}' across labs: {initial_state.labs}")
    checkpointer = await get_checkpointer()
    workflow_graph = create_health_record_graph()
    app_graph = workflow_graph.compile(checkpointer=checkpointer)

    thread_config = {"configurable": {"thread_id": run_id}}
    _RUNNING_GRAPH_THREADS[run_id] = {
        "graph": app_graph,
        "config": thread_config,
        "task": asyncio.current_task()
    }

    try:
        logger.info(f"[Run {run_id}] Streaming LangGraph execution...")
        async for chunk in app_graph.astream(initial_state.model_dump(), thread_config):
            for node_name, update in chunk.items():
                keys = list(update.keys()) if isinstance(update, dict) else type(update)
                logger.info(f"[Run {run_id}] Node completed: [{node_name}] -> yielded: {keys}")
        logger.info(f"[Run {run_id}] Stream paused or ended (e.g. reached human_approval interrupt or completion).")
    except asyncio.CancelledError:
        logger.info(f"[Run {run_id}] LangGraph execution task was cancelled.")
        await Repository.update_run_status(run_id, "cancelled", "Cancelled by user")
        await Repository.record_event(run_id, "Orchestrator", "WARNING", "Collection run was cancelled by user.")
        raise
    except Exception as e:
        logger.error(f"[Run {run_id}] Graph execution error: {e}", exc_info=True)
        await Repository.update_run_status(run_id, "failed", str(e))
        await Repository.record_event(run_id, "Orchestrator", "ERROR", f"Graph execution failed: {e}")
    finally:
        wipe_transient_credentials(run_id)
        run_record = await Repository.get_run(run_id)
        if run_record and run_record.get("status") in ("failed", "cancelled", "completed", "rejected_by_human"):
            _RUNNING_GRAPH_THREADS.pop(run_id, None)

# --- API Endpoints ---

# 1. Authentication Endpoints
@app.post("/api/auth/signup")
async def signup(req: UserSignUpRequest):
    """Registers a new user account with secure bcrypt hashing."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Full name is required")
    if not req.email.strip() or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Valid email address is required")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")

    existing = await Repository.get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    pw_hash = hash_password(req.password)
    user = await Repository.create_user(req.name.strip(), req.email.strip(), pw_hash)

    token = generate_session_token()
    token_h = hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    await Repository.create_session(user["id"], token_h, expires_at)

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }

@app.post("/api/auth/login")
async def login(req: UserLoginRequest):
    """Authenticates user and creates a secure 30-day session token."""
    clean_email = req.email.strip()
    user = await Repository.get_user_by_email(clean_email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = generate_session_token()
    token_h = hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    await Repository.create_session(str(user["id"]), token_h, expires_at)

    return {
        "token": token,
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"]
        }
    }

@app.get("/api/auth/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns the authenticated user's profile."""
    return {
        "user": {
            "id": str(current_user["id"]),
            "name": current_user["name"],
            "email": current_user["email"]
        }
    }

@app.post("/api/auth/logout")
async def logout(request: Request):
    """Logs out user and invalidates current session token."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
        await Repository.delete_session(token)
    return {"status": "logged_out"}

@app.get("/health")
async def health_check():
    """Health status and configuration verification."""
    return {
        "status": "healthy",
        "service": "Personal Health Record Organizer",
        "checkpointer": settings.CHECKPOINTER,
        "browser_mode": settings.BROWSER_MODE,
        "groq_model": settings.GROQ_MODEL,
        "database_configured": bool(settings.DATABASE_URL),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/labs")
async def list_labs(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Returns metadata and configurations for all supported lab portals including custom labs."""
    labs_list = []
    for key, cfg in PORTAL_CONFIG.items():
        labs_list.append({
            "key": key,
            "name": cfg["name"],
            "layout": cfg["layout"],
            "has_captcha": cfg["has_captcha"],
            "reports_path": cfg["reports_path"],
            "is_custom": False
        })

    if current_user:
        user_labs = await Repository.get_user_labs(current_user["id"])
        for ul in user_labs:
            labs_list.append({
                "key": ul["key"],
                "name": ul["name"],
                "layout": ul.get("layout", "table"),
                "has_captcha": ul.get("has_captcha", False),
                "reports_path": ul.get("url", ""),
                "url": ul.get("url", ""),
                "is_custom": True,
                "default_username": ul.get("username", ""),
                "default_password": ul.get("password", "")
            })

    return labs_list

@app.post("/api/labs")
async def add_lab(req: AddLabRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Adds a new custom lab portal for the authenticated user."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Lab name is required")
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="Portal URL is required")

    created = await Repository.create_user_lab(
        user_id=str(current_user["id"]),
        name=req.name.strip(),
        url=req.url.strip(),
        username=req.username.strip(),
        password=req.password.strip(),
        layout=req.layout
    )
    return created

@app.delete("/api/labs/{lab_key}")
async def delete_lab(lab_key: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Deletes a custom lab portal created by the user."""
    if lab_key in PORTAL_CONFIG:
        raise HTTPException(status_code=400, detail="Cannot delete default system lab portals")

    deleted = await Repository.delete_user_lab(str(current_user["id"]), lab_key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Custom lab not found or not owned by you")
    return {"status": "deleted", "key": lab_key}

@app.post("/api/runs")
async def create_run(
    req: CreateRunRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Creates a new collection run and launches parallel fetchers."""
    # Validate date range
    if req.date_from > req.date_to:
        raise HTTPException(status_code=400, detail="date_from cannot be after date_to")

    user_id = str(current_user["id"]) if current_user else None

    # Discover allowed lab keys
    valid_keys = set(PORTAL_CONFIG.keys())
    if user_id:
        user_custom_labs = await Repository.get_user_labs(user_id)
        valid_keys.update(l["key"] for l in user_custom_labs)

    # Filter enabled labs
    selected_labs = [
        lab for lab, cred in req.logins.items()
        if cred.enabled and lab in valid_keys
    ]
    if not selected_labs:
        raise HTTPException(status_code=400, detail="At least one lab portal must be selected.")

    # 1. Create run record in database
    run_record = await Repository.create_run(
        patient_name=req.patient_name.strip(),
        patient_id=req.patient_id.strip() if req.patient_id else None,
        date_from=req.date_from,
        date_to=req.date_to,
        labs=selected_labs,
        user_id=user_id
    )
    run_id = run_record["id"]

    # 2. Store passwords strictly in transient in-memory store (never DB!)
    cred_map = {
        lab: {"username": cred.username, "password": cred.password}
        for lab, cred in req.logins.items() if cred.enabled
    }
    set_transient_credentials(run_id, cred_map)

    # 3. Initialize Graph State
    initial_state = HealthRecordGraphState(
        run_id=run_id,
        user_id=user_id,
        patient_name=req.patient_name.strip(),
        patient_id=req.patient_id.strip() if req.patient_id else None,
        patient_key=run_record["patient_key"],
        date_from=req.date_from.isoformat(),
        date_to=req.date_to.isoformat(),
        labs=selected_labs,
        status="pending"
    )

    # 4. Launch LangGraph execution in background
    background_tasks.add_task(execute_run_workflow, run_id, initial_state)

    return {
        "run_id": run_id,
        "patient_key": run_record["patient_key"],
        "status": "pending",
        "labs": selected_labs
    }

@app.get("/api/runs")
async def get_all_runs(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Returns list of past and active runs scoped to user."""
    user_id = str(current_user["id"]) if current_user else None
    return await Repository.list_runs(user_id=user_id)

@app.get("/api/runs/{run_id}")
async def get_run_details(run_id: str):
    """Returns run metadata, decision counts, and active CAPTCHA challenges."""
    run = await Repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    candidates = await Repository.get_candidates_for_run(run_id)
    decision_counts = {
        "keep": 0,
        "duplicate": 0,
        "exclude": 0,
        "reject": 0,
        "needs_review": 0
    }
    for c in candidates:
        dec = c.get("decision")
        if dec in decision_counts:
            decision_counts[dec] += 1

    waiting_captchas = CaptchaManager.get_active_labs_for_run(run_id)

    return {
        "run": run,
        "decision_counts": decision_counts,
        "total_candidates": len(candidates),
        "waiting_captchas": waiting_captchas
    }

@app.get("/api/runs/{run_id}/events")
async def get_run_events(run_id: str, after: int = Query(default=0)):
    """Live agent events log polling endpoint (polled every 1.5s by UI)."""
    return await Repository.get_events(run_id, after_id=after)

@app.get("/api/runs/{run_id}/candidates")
async def get_run_candidates(run_id: str):
    """Returns candidate records staged for approval (omitting heavy file_bytes)."""
    candidates = await Repository.get_candidates_for_run(run_id)
    sanitized = []
    for c in candidates:
        item = dict(c)
        item.pop("file_bytes", None)  # Do not send binary payload over JSON
        sanitized.append(item)
    return sanitized

@app.get("/api/runs/{run_id}/captcha/{lab}/image")
async def get_captcha_image(run_id: str, lab: str):
    """Streams screenshot of active CAPTCHA challenge for UI modal."""
    img_bytes = CaptchaManager.get_image(run_id, lab)
    if not img_bytes:
        # Return fallback placeholder if challenge cleared or not found
        svg = """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="80"><text x="20" y="45" font-family="sans-serif" font-size="14" fill="#64748b">No active challenge</text></svg>"""
        return Response(content=svg.encode('utf-8'), media_type="image/svg+xml")

    # Sniff format
    media_type = "image/png"
    if img_bytes.startswith(b"\xff\xd8"):
        media_type = "image/jpeg"
    elif b"<svg" in img_bytes[:100]:
        media_type = "image/svg+xml"

    return Response(content=img_bytes, media_type=media_type)

@app.post("/api/runs/{run_id}/captcha/{lab}")
async def submit_captcha(run_id: str, lab: str, req: CaptchaSubmitRequest):
    """Relays human CAPTCHA answer or live-view solve signal."""
    if req.solved_live:
        success = CaptchaManager.submit_solved_live(run_id, lab)
        action_msg = f"User solved CAPTCHA challenge in live view for {lab.upper()}."
    elif req.answer:
        success = CaptchaManager.submit_answer(run_id, lab, req.answer.strip())
        action_msg = f"User submitted CAPTCHA answer for {lab.upper()}."
    else:
        raise HTTPException(status_code=400, detail="Either answer or solved_live must be provided.")

    if not success:
        raise HTTPException(status_code=404, detail="No active CAPTCHA session waiting for this lab.")

    await Repository.record_event(run_id, "User", "INFO", action_msg)
    return {"status": "relayed", "lab": lab}

@app.post("/api/runs/{run_id}/approve")
async def approve_run(run_id: str, req: ApproveRunRequest):
    """Human approval submission: resumes LangGraph execution to store and re-check records."""
    try:
        run = await Repository.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found in database.")

        # Record detailed user actions for the activity log
        candidates = await Repository.get_candidates_for_run(run_id)
        if not req.approved:
            await Repository.record_event(
                run_id, "User", "WARNING",
                f"User rejected collection run approval. All {len(candidates)} reports were discarded."
            )
        else:
            accepted_count = 0
            rejected_count = 0
            for c in candidates:
                cid = str(c["id"])
                name = c.get("x_test") or c.get("listing_title") or c.get("filename")
                override = req.overrides.get(cid)
                if override in ("keep", "accept"):
                    accepted_count += 1
                    await Repository.record_event(run_id, "User", "INFO", f"User manually accepted '{name}' ({c.get('filename')}) via override.")
                elif override in ("skip", "reject", "exclude"):
                    rejected_count += 1
                    await Repository.record_event(run_id, "User", "WARNING", f"User manually rejected '{name}' ({c.get('filename')}) via override.")
                else:
                    dec = c.get("decision")
                    if dec == "keep":
                        accepted_count += 1
                        await Repository.record_event(run_id, "User", "INFO", f"User confirmed acceptance of '{name}' ({c.get('filename')}).")
                    else:
                        rejected_count += 1
                        await Repository.record_event(run_id, "User", "INFO", f"User confirmed exclusion of '{name}' ({c.get('filename')}) [{dec}].")
            
            await Repository.record_event(
                run_id, "User", "INFO",
                f"User approved collection run: {accepted_count} report(s) accepted, {rejected_count} report(s) excluded/rejected."
            )

        thread_info = _RUNNING_GRAPH_THREADS.get(run_id)
        checkpointer = await get_checkpointer()

        # Rebuild state from DB if server restarted while waiting for approval
        state = await rebuild_run_context(run_id)
        if not state:
            raise HTTPException(status_code=500, detail="Could not rebuild run context.")

        state.approved = req.approved
        state.overrides = req.overrides

        # Record approval in DB
        await Repository.record_approval(run_id, req.approved, req.overrides)

        # If LangGraph app thread is waiting at interrupt, resume it and await completion:
        if thread_info:
            try:
                from langgraph.types import Command
                app_graph = thread_info["graph"]
                config = thread_info["config"]
                resume_cmd = Command(resume={"approved": req.approved, "overrides": req.overrides})
                await app_graph.ainvoke(resume_cmd, config)
                _RUNNING_GRAPH_THREADS.pop(run_id, None)
                return {"status": "completed", "approved": req.approved}
            except Exception as e:
                logger.warning(f"Error resuming graph via Command: {e}. Executing sequential completion.")

        # Direct execution of remaining steps (store -> recheck -> build_timeline)
        if req.approved:
            store_res = await store(state)
            state.stored_count = store_res.get("stored_count", 0)
            await recheck_saved_files(state)
            await build_timeline(state)
        else:
            await Repository.update_run_status(run_id, "rejected_by_human")

        _RUNNING_GRAPH_THREADS.pop(run_id, None)
        return {"status": "completed", "approved": req.approved}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in approve_run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Approval execution failed: {str(e)}")

class BatchDeleteRunsRequest(BaseModel):
    run_ids: Optional[List[str]] = None

@app.post("/api/runs/{run_id}/cancel")
async def cancel_run(run_id: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Cancels an active or waiting collection run and safely unblocks pending CAPTCHAs."""
    user_id = str(current_user["id"]) if current_user else None
    run = await Repository.get_run(run_id, user_id=user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Cancel any waiting CAPTCHA challenges immediately
    CaptchaManager.cancel_run_captchas(run_id)

    # Cancel running background graph thread if still active
    thread_info = _RUNNING_GRAPH_THREADS.pop(run_id, None)
    if thread_info:
        task = thread_info.get("task")
        if task and not task.done():
            task.cancel()

    # Mark status as cancelled in database
    await Repository.update_run_status(run_id, "cancelled", "Cancelled by user")
    await Repository.record_event(run_id, "User", "WARNING", "User cancelled the collection run.")
    wipe_transient_credentials(run_id)

    return {"status": "cancelled", "run_id": run_id}

@app.delete("/api/runs/{run_id}")
async def delete_single_run(run_id: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Deletes a run and all associated staging candidates and events."""
    user_id = str(current_user["id"]) if current_user else None

    # If currently active, unblock and cancel
    CaptchaManager.cancel_run_captchas(run_id)
    thread_info = _RUNNING_GRAPH_THREADS.pop(run_id, None)
    if thread_info:
        task = thread_info.get("task")
        if task and not task.done():
            task.cancel()
    wipe_transient_credentials(run_id)

    deleted = await Repository.delete_run(run_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Run not found or already deleted")
    return {"status": "deleted", "run_id": run_id}

@app.delete("/api/runs")
@app.post("/api/runs/delete")
async def delete_runs(
    req: Optional[BatchDeleteRunsRequest] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Deletes selected runs or all past runs for the user."""
    user_id = str(current_user["id"]) if current_user else None

    if req and req.run_ids:
        for rid in req.run_ids:
            CaptchaManager.cancel_run_captchas(rid)
            t_info = _RUNNING_GRAPH_THREADS.pop(rid, None)
            if t_info and t_info.get("task") and not t_info["task"].done():
                t_info["task"].cancel()
            wipe_transient_credentials(rid)
        count = await Repository.delete_runs(req.run_ids, user_id=user_id)
    else:
        for rid in list(_RUNNING_GRAPH_THREADS.keys()):
            CaptchaManager.cancel_run_captchas(rid)
            t_info = _RUNNING_GRAPH_THREADS.pop(rid, None)
            if t_info and t_info.get("task") and not t_info["task"].done():
                t_info["task"].cancel()
            wipe_transient_credentials(rid)
        count = await Repository.clear_all_runs(user_id=user_id)

    return {"status": "deleted", "count": count}

@app.get("/api/timeline")
async def get_timeline(
    patient_key: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Returns the unified, dated, indexed health timeline scoped to user."""
    user_id = str(current_user["id"]) if current_user else None
    return await Repository.get_timeline(patient_key, user_id=user_id)

@app.get("/api/files/{candidate_id}")
async def get_candidate_file(candidate_id: str):
    """Streams candidate PDF document for in-browser viewing."""
    candidate = await Repository.get_candidate(candidate_id)
    if not candidate or not candidate.get("file_bytes"):
        raise HTTPException(status_code=404, detail="PDF file not found")

    file_bytes = candidate["file_bytes"]
    filename = candidate.get("filename", f"report_{candidate_id}.pdf")
    content_type = candidate.get("content_type", "application/pdf")

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type,
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "Content-Length": str(len(file_bytes))
        }
    )
