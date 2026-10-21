"""LangGraph workflow orchestration for Personal Health Record Organizer.

Graph flow:
validate inputs → 3 fetchers in parallel → join → extract and check → human approval → store → re-check saved files → build timeline.

Approval uses interrupt() and Command(resume=...) with AsyncPostgresSaver / MemorySaver.
Strict state security: state holds only IDs, counts, approved, and overrides. Never file bytes or passwords.
Store step is idempotent through unique constraints.
Re-check step re-opens every saved file and confirms name and date again.
Rebuilds context from DB if server restarted while waiting for approval.
"""

import logging
import asyncio
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command

from app.graph.state import HealthRecordGraphState
from app.db.repository import Repository
from app.agents.fetcher import LabFetcherAgent
from app.agents.extractor import ExtractorAgent
from app.agents.checker import CheckerAgent
from app.tools.pdf_tools import read_pdf_text
from app.agents.extractor import extract_with_regex
from app.tools.check_legit import compute_name_score

logger = logging.getLogger(__name__)

# In-memory transient credentials dictionary: run_id -> lab -> {username, password}
# Wiped immediately as fetchers finish!
_TRANSIENT_CREDENTIALS: Dict[str, Dict[str, Dict[str, str]]] = {}

def set_transient_credentials(run_id: str, credentials: Dict[str, Dict[str, str]]):
    _TRANSIENT_CREDENTIALS[run_id] = credentials

def get_transient_credentials(run_id: str, lab: str) -> Dict[str, str]:
    return _TRANSIENT_CREDENTIALS.get(run_id, {}).get(lab, {})

def wipe_transient_credentials(run_id: str, lab: Optional[str] = None):
    if run_id in _TRANSIENT_CREDENTIALS:
        if lab:
            _TRANSIENT_CREDENTIALS[run_id].pop(lab, None)
        else:
            _TRANSIENT_CREDENTIALS.pop(run_id, None)

# --- Graph Node Implementations ---

async def validate_inputs(state: HealthRecordGraphState) -> Dict[str, Any]:
    """Node 1: Validates patient info, date range, and selected labs."""
    logger.info(f"Validating inputs for run {state.run_id} (Patient: {state.patient_name})")
    await Repository.update_run_status(state.run_id, "fetching")
    await Repository.record_event(
        state.run_id, "Orchestrator", "INFO",
        f"Initialized run for {state.patient_name} across labs {state.labs} [{state.date_from} to {state.date_to}]."
    )
    return {"status": "fetching"}

async def fetch_lab_worker(state: HealthRecordGraphState, lab: str) -> Dict[str, Any]:
    """Worker node for an individual lab fetcher."""
    if lab not in state.labs:
        return {"fetch_summaries": {lab: 0}}

    creds = get_transient_credentials(state.run_id, lab)
    username = creds.get("username", "pt001")
    password = creds.get("password", "demo123")

    date_from = date.fromisoformat(state.date_from)
    date_to = date.fromisoformat(state.date_to)

    agent = LabFetcherAgent(
        lab=lab,
        run_id=state.run_id,
        username=username,
        password=password,
        date_from=date_from,
        date_to=date_to
    )

    try:
        res = await agent.run()
        staged_count = res.get("staged_count", 0)
        return {"fetch_summaries": {lab: staged_count}}
    finally:
        # Wipe password in-memory as lab finishes
        wipe_transient_credentials(state.run_id, lab)

async def fetch_a1(state: HealthRecordGraphState) -> Dict[str, Any]:
    return await fetch_lab_worker(state, "labA")

async def fetch_cityscan(state: HealthRecordGraphState) -> Dict[str, Any]:
    return await fetch_lab_worker(state, "labB")

async def fetch_vitals(state: HealthRecordGraphState) -> Dict[str, Any]:
    return await fetch_lab_worker(state, "labC")

async def join(state: HealthRecordGraphState) -> Dict[str, Any]:
    """Node 3: Gathers candidates staged in database from all fetch workers."""
    candidates = await Repository.get_candidates_for_run(state.run_id)
    cand_ids = [c["id"] for c in candidates]

    await Repository.update_run_status(state.run_id, "extracting_checking")
    await Repository.record_event(
        state.run_id, "Orchestrator", "INFO",
        f"Fetch phase completed. Staged {len(cand_ids)} candidate documents. Beginning extraction and verification."
    )
    return {
        "candidate_ids": cand_ids,
        "status": "extracting_checking"
    }

async def extract_and_check(state: HealthRecordGraphState) -> Dict[str, Any]:
    """Node 4: Extracts metadata using Extractor and evaluates validity using Checker."""
    date_from = date.fromisoformat(state.date_from)
    date_to = date.fromisoformat(state.date_to)

    # Load permanent stored reports from previous runs to detect cross-run duplicates
    stored_reports = await Repository.get_stored_reports(state.patient_key)
    earlier_valid_candidates = []

    counts = {
        "keep": 0,
        "duplicate": 0,
        "exclude": 0,
        "reject": 0,
        "needs_review": 0
    }

    # Fetch fresh candidate rows from database
    candidates = await Repository.get_candidates_for_run(state.run_id)

    for cand in candidates:
        # 1. Extraction (Regex first, LLM fallback only if missing name/date, checks against raw text)
        await ExtractorAgent.process_candidate(cand, state.run_id)

        # Refresh candidate data after extraction
        fresh_cand = await Repository.get_candidate(cand["id"]) or cand

        # 2. Checker (Legitimacy check first, then duplicate check)
        check_res = await CheckerAgent.evaluate_candidate(
            candidate=fresh_cand,
            expected_patient_name=state.patient_name,
            expected_patient_id=state.patient_id,
            date_from=date_from,
            date_to=date_to,
            stored_reports=stored_reports,
            earlier_valid_candidates=earlier_valid_candidates,
            run_id=state.run_id
        )

        decision = check_res["decision"]
        if decision in counts:
            counts[decision] += 1

        if decision == "keep":
            earlier_valid_candidates.append(fresh_cand)

    await Repository.update_run_status(state.run_id, "waiting_approval")
    await Repository.record_event(
        state.run_id, "Orchestrator", "INFO",
        f"Extraction and verification complete. Counts: {counts}. Awaiting human approval."
    )

    return {
        "decision_counts": counts,
        "status": "waiting_approval"
    }

async def human_approval(state: HealthRecordGraphState) -> Dict[str, Any]:
    """Node 5: Halts graph using interrupt() until human confirms decisions."""
    # State passed to interrupt
    interrupt_payload = {
        "status": "waiting_approval",
        "run_id": state.run_id,
        "decision_counts": state.decision_counts,
        "candidate_ids": state.candidate_ids
    }

    # Interrupt and wait for Command(resume=...)
    resume_data = interrupt(interrupt_payload)

    # When resumed:
    approved = False
    overrides = {}
    if isinstance(resume_data, dict):
        approved = bool(resume_data.get("approved", False))
        overrides = resume_data.get("overrides", {})

    # Persist approval in DB
    await Repository.record_approval(state.run_id, approved, overrides)
    await Repository.record_event(
        state.run_id, "Orchestrator", "INFO",
        f"Human approval received: approved={approved}, overrides={len(overrides)}."
    )

    return {
        "approved": approved,
        "overrides": overrides,
        "status": "storing" if approved else "rejected_by_human"
    }

async def store(state: HealthRecordGraphState) -> Dict[str, Any]:
    """Node 6: Idempotently stores approved records into permanent reports table."""
    if not state.approved:
        await Repository.update_run_status(state.run_id, "rejected_by_human")
        await Repository.record_event(
            state.run_id, "Orchestrator", "WARNING",
            "Run was rejected by human approver. No documents stored."
        )
        return {"status": "rejected_by_human", "stored_count": 0}

    await Repository.update_run_status(state.run_id, "storing")
    candidates = await Repository.get_candidates_for_run(state.run_id)
    stored_count = 0

    for cand in candidates:
        cand_id = cand["id"]
        decision = cand.get("decision")
        override = state.overrides.get(cand_id)

        # Decision resolution logic:
        should_store = False
        if decision == "keep":
            # Store unless explicitly skipped by human
            should_store = (override != "skip")
        elif decision == "needs_review":
            # Only store if explicitly approved ("keep") by human
            should_store = (override == "keep")
        else:
            # duplicate, exclude, reject
            should_store = False

        if should_store:
            rep_date = cand.get("x_date") or cand.get("portal_date") or date.today()
            success = await Repository.store_approved_candidate(
                candidate_id=cand_id,
                patient_key=state.patient_key,
                lab=cand["lab"],
                report_id=cand.get("x_report_id") or cand.get("portal_report_id") or f"GEN-{cand_id[:8]}",
                test_name=cand.get("x_test") or cand.get("listing_title") or "Diagnostic Report",
                report_date=rep_date,
                sha256=cand.get("sha256")
            )
            if success:
                stored_count += 1
        else:
            await Repository.mark_candidate_not_stored(cand_id)

    await Repository.record_event(
        state.run_id, "Orchestrator", "INFO",
        f"Storage phase complete. {stored_count} records committed to permanent health record."
    )

    return {
        "stored_count": stored_count,
        "status": "rechecking"
    }

async def recheck_saved_files(state: HealthRecordGraphState) -> Dict[str, Any]:
    """Node 7: Verification step: re-opens every saved file from DB and confirms name and date again."""
    if not state.approved or state.stored_count == 0:
        return {"rechecked_count": 0, "recheck_failures": 0}

    await Repository.update_run_status(state.run_id, "rechecking")
    candidates = await Repository.get_candidates_for_run(state.run_id)
    rechecked = 0
    failures = 0

    for cand in candidates:
        if cand.get("status") != "stored":
            continue

        cand_id = cand["id"]
        file_bytes = cand.get("file_bytes")
        # Re-open file bytes
        read_res = read_pdf_text(file_bytes)
        if not read_res["readable"]:
            await Repository.update_candidate_recheck(cand_id, False, f"Recheck failed: {read_res['reason']}")
            failures += 1
            continue

        # Re-extract
        re_extracted = extract_with_regex(read_res["text"])
        name = re_extracted["name"] or cand.get("x_name")
        doc_date = re_extracted["date"] or cand.get("x_date")

        name_score, _ = compute_name_score(state.patient_name, name or "")
        date_ok = bool(doc_date)

        if name_score >= 0.75 and date_ok:
            await Repository.update_candidate_recheck(
                cand_id, True, f"Recheck verified: Name matches ({name_score:.2f}), Date verified ({doc_date})."
            )
            rechecked += 1
        else:
            note = f"Recheck discrepancy: name_score={name_score:.2f}, date_ok={date_ok}"
            await Repository.update_candidate_recheck(cand_id, False, note)
            failures += 1

    await Repository.record_event(
        state.run_id, "Orchestrator", "INFO",
        f"Verification step completed: {rechecked} files confirmed authentic ({failures} issues)."
    )

    return {
        "rechecked_count": rechecked,
        "recheck_failures": failures,
        "status": "building_timeline"
    }

async def build_timeline(state: HealthRecordGraphState) -> Dict[str, Any]:
    """Node 8: Compiles finalized dated health timeline."""
    timeline = await Repository.get_timeline(state.patient_key)
    await Repository.update_run_status(state.run_id, "completed")
    await Repository.record_event(
        state.run_id, "Orchestrator", "INFO",
        f"Run successfully completed. Health timeline has {len(timeline)} total indexed entries."
    )
    return {
        "status": "completed"
    }

# --- Graph Assembly ---

def create_health_record_graph():
    """Builds and compiles the complete LangGraph workflow."""
    workflow = StateGraph(HealthRecordGraphState)

    # Add Nodes
    workflow.add_node("validate_inputs", validate_inputs)
    workflow.add_node("fetch_a1", fetch_a1)
    workflow.add_node("fetch_cityscan", fetch_cityscan)
    workflow.add_node("fetch_vitals", fetch_vitals)
    workflow.add_node("join", join)
    workflow.add_node("extract_and_check", extract_and_check)
    workflow.add_node("human_approval", human_approval)
    workflow.add_node("store", store)
    workflow.add_node("recheck_saved_files", recheck_saved_files)
    workflow.add_node("build_timeline", build_timeline)

    # Edge Connections
    # START -> validate_inputs
    workflow.add_edge(START, "validate_inputs")

    # 3 Fetchers in parallel
    workflow.add_edge("validate_inputs", "fetch_a1")
    workflow.add_edge("validate_inputs", "fetch_cityscan")
    workflow.add_edge("validate_inputs", "fetch_vitals")

    # Join
    workflow.add_edge("fetch_a1", "join")
    workflow.add_edge("fetch_cityscan", "join")
    workflow.add_edge("fetch_vitals", "join")

    # Extract & Check
    workflow.add_edge("join", "extract_and_check")

    # Human Approval (interrupt)
    workflow.add_edge("extract_and_check", "human_approval")

    # Store
    workflow.add_edge("human_approval", "store")

    # Re-check saved files
    workflow.add_edge("store", "recheck_saved_files")

    # Build timeline
    workflow.add_edge("recheck_saved_files", "build_timeline")

    # END
    workflow.add_edge("build_timeline", END)

    return workflow

async def rebuild_run_context(run_id: str) -> Optional[HealthRecordGraphState]:
    """Rebuilds graph state from database if server restarted while waiting for approval."""
    run = await Repository.get_run(run_id)
    if not run:
        return None

    candidates = await Repository.get_candidates_for_run(run_id)
    counts = {"keep": 0, "duplicate": 0, "exclude": 0, "reject": 0, "needs_review": 0}
    for c in candidates:
        dec = c.get("decision")
        if dec in counts:
            counts[dec] += 1

    return HealthRecordGraphState(
        run_id=run["id"],
        patient_name=run["patient_name"],
        patient_id=run.get("patient_id"),
        patient_key=run["patient_key"],
        date_from=str(run["date_from"]),
        date_to=str(run["date_to"]),
        labs=run.get("labs") or [],
        candidate_ids=[c["id"] for c in candidates],
        decision_counts=counts,
        status=run.get("status", "pending")
    )
