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

import io
import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, Query, BackgroundTasks, Depends
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
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Mock Portal under root paths if requested, and under /portal for convenience
app.mount("/portal", mock_portal_app)
# Mount individual lab portals directly for local testing convenience
for lab_key in ("labA", "labB", "labC"):
    app.mount(f"/{lab_key}", mock_portal_app)

# --- Pydantic Schemas ---

class LabLoginInfo(BaseModel):
    enabled: bool = True
    username: str = "pt001"
    password: str = "demo123"

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
    """Executes the compiled LangGraph workflow asynchronously."""
    checkpointer = await get_checkpointer()
    workflow_graph = create_health_record_graph()
    app_graph = workflow_graph.compile(checkpointer=checkpointer)

    thread_config = {"configurable": {"thread_id": run_id}}
    _RUNNING_GRAPH_THREADS[run_id] = {
        "graph": app_graph,
        "config": thread_config
    }

    try:
        # Run graph until interrupt or completion
        async for chunk in app_graph.astream(initial_state.model_dump(), thread_config):
            logger.info(f"[Run {run_id}] Graph progress chunk: {list(chunk.keys())}")
    except Exception as e:
        logger.error(f"[Run {run_id}] Graph execution error: {e}", exc_info=True)
        await Repository.update_run_status(run_id, "failed", str(e))
        await Repository.record_event(run_id, "Orchestrator", "ERROR", f"Graph execution failed: {e}")
    finally:
        wipe_transient_credentials(run_id)

# --- API Endpoints ---

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
async def list_labs():
    """Returns metadata and configurations for all supported lab portals."""
    labs_list = []
    for key, cfg in PORTAL_CONFIG.items():
        labs_list.append({
            "key": key,
            "name": cfg["name"],
            "layout": cfg["layout"],
            "has_captcha": cfg["has_captcha"],
            "reports_path": cfg["reports_path"]
        })
    return labs_list

@app.post("/api/runs")
async def create_run(req: CreateRunRequest, background_tasks: BackgroundTasks):
    """Creates a new collection run and launches parallel fetchers."""
    # Validate date range
    if req.date_from > req.date_to:
        raise HTTPException(status_code=400, detail="date_from cannot be after date_to")

    # Filter enabled labs
    selected_labs = [
        lab for lab, cred in req.logins.items()
        if cred.enabled and lab in PORTAL_CONFIG
    ]
    if not selected_labs:
        raise HTTPException(status_code=400, detail="At least one lab portal must be selected.")

    # 1. Create run record in database
    run_record = await Repository.create_run(
        patient_name=req.patient_name.strip(),
        patient_id=req.patient_id.strip() if req.patient_id else None,
        date_from=req.date_from,
        date_to=req.date_to,
        labs=selected_labs
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
async def get_all_runs():
    """Returns list of past and active runs."""
    return await Repository.list_runs()

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
    elif req.answer:
        success = CaptchaManager.submit_answer(run_id, lab, req.answer.strip())
    else:
        raise HTTPException(status_code=400, detail="Either answer or solved_live must be provided.")

    if not success:
        raise HTTPException(status_code=404, detail="No active CAPTCHA session waiting for this lab.")

    return {"status": "relayed", "lab": lab}

@app.post("/api/runs/{run_id}/approve")
async def approve_run(run_id: str, req: ApproveRunRequest):
    """Human approval submission: resumes LangGraph execution to store and re-check records."""
    run = await Repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    thread_info = _RUNNING_GRAPH_THREADS.get(run_id)
    checkpointer = await get_checkpointer()

    # Rebuild state from DB if server restarted while waiting for approval
    state = await rebuild_run_context(run_id)
    if not state:
        raise HTTPException(status_code=500, detail="Could not rebuild run context.")

    state.approved = req.approved
    state.overrides = req.overrides

    # If LangGraph app thread is waiting at interrupt, resume it:
    if thread_info:
        try:
            from langgraph.types import Command
            app_graph = thread_info["graph"]
            config = thread_info["config"]
            resume_cmd = Command(resume={"approved": req.approved, "overrides": req.overrides})
            # Resume graph stream in background task
            asyncio.create_task(app_graph.ainvoke(resume_cmd, config))
            return {"status": "resumed", "approved": req.approved}
        except Exception as e:
            logger.warning(f"Error resuming graph via Command: {e}. Executing sequential completion.")

    # Fallback direct execution of remaining steps (store -> recheck -> build_timeline)
    await Repository.record_approval(run_id, req.approved, req.overrides)
    if req.approved:
        store_res = await store(state)
        state.stored_count = store_res.get("stored_count", 0)
        await recheck_saved_files(state)
        await build_timeline(state)
    else:
        await Repository.update_run_status(run_id, "rejected_by_human")

    return {"status": "completed", "approved": req.approved}

@app.get("/api/timeline")
async def get_timeline(patient_key: Optional[str] = None):
    """Returns the unified, dated, indexed health timeline."""
    return await Repository.get_timeline(patient_key)

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
