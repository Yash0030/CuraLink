"""Checker Agent.

Per file, executes:
1. Legitimacy check (Tool 5: check_file_legit)
2. Duplicate check (Tool 6: check_duplicate)
Determines final candidate decision:
- 'keep': Passed legitimacy and unique.
- 'duplicate': Duplicate by Report ID or SHA-256 hash.
- 'exclude': Different patient (e.g. look-alike name with score < 0.75 - TC3).
- 'reject': Corrupt/non-PDF (TC4), patient ID mismatch, date out of range.
- 'needs_review': Borderline name score (>= 0.75), portal vs PDF date discrepancy, missing metadata, or possible duplicate.

The LLM is used ONLY to rewrite borderline reasons into one plain, user-friendly sentence.
Exact checks stay strictly in plain code.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import date
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from app.config import settings
from app.tools.check_legit import check_file_legit
from app.tools.check_duplicate import check_duplicate
from app.db.repository import Repository

logger = logging.getLogger(__name__)

async def rewrite_reason_with_llm(raw_reason: str) -> str:
    """Uses Groq LLM to rewrite borderline technical reasons into one plain sentence."""
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_your_groq"):
        return raw_reason

    try:
        llm = ChatGroq(
            model=settings.GROQ_MODEL,
            groq_api_key=settings.GROQ_API_KEY,
            temperature=0.0
        )
        prompt = (
            "Rewrite the following document check discrepancy into ONE plain, user-friendly sentence "
            "explaining why this medical record needs human approval. Do not add assumptions:\n\n"
            f"Technical reason: {raw_reason}"
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        # Return first sentence if multiple
        sentences = content.split("\n")
        return sentences[0].strip().strip('"')
    except Exception as e:
        logger.warning(f"LLM reason rewrite failed: {e}")
        return raw_reason

class CheckerAgent:
    @staticmethod
    async def evaluate_candidate(
        candidate: Dict[str, Any],
        expected_patient_name: str,
        expected_patient_id: Optional[str],
        date_from: date,
        date_to: date,
        stored_reports: List[Dict[str, Any]],
        earlier_valid_candidates: List[Dict[str, Any]],
        run_id: str
    ) -> Dict[str, Any]:
        """Runs legitimacy check first, then duplicate check, one file at a time."""
        cand_id = candidate["id"]
        filename = candidate.get("filename", "")
        file_bytes = candidate.get("file_bytes")
        extracted_name = candidate.get("x_name")
        extracted_id = candidate.get("x_patient_id")
        extracted_date = candidate.get("x_date")
        portal_date = candidate.get("portal_date")

        # Step 1: Legitimacy Check (Tool 5)
        legit_res = check_file_legit(
            file_bytes=file_bytes,
            extracted_name=extracted_name,
            extracted_patient_id=extracted_id,
            extracted_date=extracted_date,
            portal_date=portal_date,
            expected_patient_name=expected_patient_name,
            expected_patient_id=expected_patient_id,
            date_from=date_from,
            date_to=date_to
        )

        logger.info(f"[Checker] File '{filename}' -> Legitimacy: verdict={legit_res['verdict']} (name_score={legit_res.get('name_score', 0):.2f}, code={legit_res.get('code')})")

        decision = None
        decision_reason = None
        duplicate_res = {"verdict": "skipped", "reason": "Not evaluated due to legitimacy failure"}

        # Categorize legitimacy verdicts
        if legit_res["verdict"] == "fail":
            code = legit_res["code"]
            if code == "name_mismatch_exclude":
                decision = "exclude"
                decision_reason = legit_res["reasons"][0]
            elif code == "not_pdf":
                decision = "reject"
                decision_reason = "Corrupt or non-PDF file: does not contain valid %PDF header (TC4)."
            elif code == "patient_id_mismatch":
                decision = "reject"
                decision_reason = legit_res["reasons"][0]
            elif code == "date_out_of_range":
                decision = "reject"
                decision_reason = legit_res["reasons"][0]
            else:
                decision = "reject"
                decision_reason = legit_res["reasons"][0]

        elif legit_res["verdict"] == "uncertain":
            decision = "needs_review"
            decision_reason = " ".join(legit_res["reasons"])
            # Rewrite borderline reason into one plain sentence using LLM
            decision_reason = await rewrite_reason_with_llm(decision_reason)

        elif legit_res["verdict"] == "pass":
            # Step 2: Duplicate Check (Tool 6)
            duplicate_res = check_duplicate(
                candidate=candidate,
                stored_reports=stored_reports,
                earlier_valid_candidates=earlier_valid_candidates
            )

            dup_verdict = duplicate_res["verdict"]
            logger.info(f"[Checker] File '{filename}' -> Duplicate check: verdict={dup_verdict} ({duplicate_res.get('reason')})")

            if dup_verdict == "duplicate":
                decision = "duplicate"
                decision_reason = duplicate_res["reason"]
            elif dup_verdict == "possible_duplicate":
                decision = "needs_review"
                decision_reason = await rewrite_reason_with_llm(duplicate_res["reason"])
            else:
                # Unique and passed legitimacy
                decision = "keep"
                decision_reason = "Verified authentic, matching patient, and unique."

        logger.info(f"[Checker] Final verdict for '{filename}': [{decision.upper()}] - {decision_reason}")

        # Persist check results in candidate row
        await Repository.update_candidate_check(
            candidate_id=cand_id,
            legit_result=legit_res,
            duplicate_result=duplicate_res,
            decision=decision,
            decision_reason=decision_reason
        )

        await Repository.record_event(
            run_id, "Checker", "INFO" if decision in ("keep", "duplicate") else "WARNING",
            f"File '{filename}' evaluated as [{decision.upper()}]: {decision_reason}"
        )

        return {
            "candidate_id": cand_id,
            "filename": filename,
            "decision": decision,
            "decision_reason": decision_reason,
            "legit_result": legit_res,
            "duplicate_result": duplicate_res
        }
