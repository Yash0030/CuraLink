"""Extractor Agent.

Reads staged PDF files and extracts:
- Patient Name (x_name)
- Patient ID (x_patient_id)
- Report ID (x_report_id)
- Date (x_date)
- Test / Investigation Name (x_test)

Strategy:
1. High-precision regex extraction tuned for known layouts (labA, labB, labC).
2. LLM fallback ONLY when name or date is missing.
3. Anti-hallucination guardrail: LLM values are strictly validated against raw text.
   Invented values not found in the raw text are dropped.
"""

import re
import json
import logging
from datetime import date, datetime
from typing import Dict, Any, Optional, Tuple
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq

from app.config import settings
from app.tools.pdf_tools import read_pdf_text
from app.db.repository import Repository

logger = logging.getLogger(__name__)

# Regex patterns for the three lab layouts
PATTERNS = {
    "report_id": [
        # Standard hackathon report ID format: A-20260121-001-2
        re.compile(r"\b([A-C]-\d{8}-\d{3,4}-\d+)\b", re.IGNORECASE),
        re.compile(r"(?:Report ID|Report No|Scan ID|Sample ID|Report Ref|Accession #?)\s*[:\-]\s*([A-Za-z0-9\-]+)", re.IGNORECASE),
    ],
    "patient_id": [
        re.compile(r"(?:Patient ID|PID|MRN|UHID|Patient Number)\s*[:\-]\s*([A-Za-z0-9\-]+)", re.IGNORECASE),
        re.compile(r"\b(pt\d{3,6})\b", re.IGNORECASE),
    ],
    "name": [
        re.compile(r"(?:Patient Name|PATIENT NAME|Client|Customer|Name)\s*[:\-]\s*([A-Za-z,\s\-'.]+?)(?=\s*(?:\n|Patient ID|PID|MRN|UHID|Age|Gender|DOB|Date|Report|Test|\Z))", re.IGNORECASE),
        re.compile(r"PATIENT\s*[:\-]\s*([A-Za-z,\s\-'.]+?)(?=\s*(?:\n|ID|PID|MRN|UHID|Age|Gender|DOB|Date|Report|Test|\Z))", re.IGNORECASE),
    ],
    "date": [
        re.compile(r"(?:Date of Report|Report Date|Exam Date|Collection Date|Date of Scan|Date)\s*[:\-]\s*([0-9]{4}[-/][0-9]{2}[-/][0-9]{2})", re.IGNORECASE),
        re.compile(r"(?:Date of Report|Report Date|Exam Date|Collection Date|Date of Scan|Date)\s*[:\-]\s*([0-9]{2}[-/][0-9]{2}[-/][0-9]{4})", re.IGNORECASE),
        re.compile(r"(?:Date of Report|Report Date|Exam Date|Collection Date|Date of Scan|Date)\s*[:\-]\s*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})", re.IGNORECASE),
        re.compile(r"\b([0-9]{4}-[0-9]{2}-[0-9]{2})\b"),
    ],
    "test": [
        re.compile(r"(?:Test Name|Test / Examination|Study / Procedure|Test Panel|Test|Investigation|Procedure)\s*[:\-]\s*([A-Za-z0-9\s()/,+_-]+?)(?=\s*(?:\n|Result|Units|Normal|Reference|Method|Impression|\Z))", re.IGNORECASE),
    ]
}

def parse_iso_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%b %d, %Y", "%B %d, %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

def extract_with_regex(raw_text: str) -> Dict[str, Any]:
    """Applies high-precision regex extraction across the text."""
    results = {
        "name": None,
        "patient_id": None,
        "report_id": None,
        "date": None,
        "test": None
    }

    # Extract Report ID
    for pat in PATTERNS["report_id"]:
        match = pat.search(raw_text)
        if match:
            results["report_id"] = match.group(1).strip()
            break

    # Extract Patient ID
    for pat in PATTERNS["patient_id"]:
        match = pat.search(raw_text)
        if match:
            results["patient_id"] = match.group(1).strip()
            break

    # Extract Name
    for pat in PATTERNS["name"]:
        match = pat.search(raw_text)
        if match:
            clean_name = match.group(1).strip()
            if len(clean_name) >= 2 and not clean_name.isdigit():
                results["name"] = clean_name
                break

    # Extract Date
    for pat in PATTERNS["date"]:
        match = pat.search(raw_text)
        if match:
            parsed_d = parse_iso_date(match.group(1).strip())
            if parsed_d:
                results["date"] = parsed_d
                break

    # Extract Test
    for pat in PATTERNS["test"]:
        match = pat.search(raw_text)
        if match:
            test_val = match.group(1).strip()
            if len(test_val) >= 2:
                results["test"] = test_val
                break

    return results

async def extract_with_llm(raw_text: str) -> Dict[str, Any]:
    """LLM fallback extraction using ChatGroq when regex misses name or date."""
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_your_groq"):
        return {}

    try:
        llm = ChatGroq(
            model=settings.GROQ_MODEL,
            groq_api_key=settings.GROQ_API_KEY,
            temperature=0.0
        )
        prompt = (
            "You are a medical document metadata extractor. "
            "Extract the following 5 fields from the provided document text:\n"
            "- name: patient full name\n"
            "- patient_id: patient ID or MRN\n"
            "- report_id: report or accession ID\n"
            "- date: report or collection date (format YYYY-MM-DD)\n"
            "- test: test or investigation name\n\n"
            "Return ONLY a valid JSON object with keys: name, patient_id, report_id, date, test. "
            "If a value is not in the text, use null.\n\n"
            f"DOCUMENT TEXT:\n{raw_text[:2000]}"
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        # Clean JSON markdown if wrapped
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        parsed = json.loads(content.strip())
        return parsed
    except Exception as e:
        logger.warning(f"LLM fallback extraction error: {e}")
        return {}

def validate_against_raw_text(llm_val: Optional[str], raw_text: str) -> Optional[str]:
    """Drops invented / hallucinated values not present in the raw text."""
    if not llm_val:
        return None
    llm_val_str = str(llm_val).strip()
    if not llm_val_str:
        return None

    # Check case-insensitive presence of value or major tokens in raw text
    val_lower = llm_val_str.lower()
    raw_lower = raw_text.lower()

    if val_lower in raw_lower:
        return llm_val_str

    # Token-level presence check
    tokens = [t for t in re.split(r"\W+", val_lower) if len(t) > 2]
    if tokens and all(t in raw_lower for t in tokens):
        return llm_val_str

    logger.warning(f"Guardrail: Dropped hallucinated value '{llm_val_str}' not found in raw text.")
    return None

class ExtractorAgent:
    @staticmethod
    async def process_candidate(candidate: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """Extracts metadata from staged candidate PDF."""
        file_bytes = candidate.get("file_bytes")
        filename = candidate.get("filename", "")
        cand_id = candidate["id"]

        # Tool 4: read_pdf_text
        read_res = read_pdf_text(file_bytes)
        if not read_res["readable"]:
            await Repository.update_candidate_extraction(
                candidate_id=cand_id,
                extract_ok=False,
                extract_note=read_res["reason"],
                extract_source="failed",
                x_name=None,
                x_patient_id=None,
                x_report_id=candidate.get("portal_report_id"),
                x_date=candidate.get("portal_date"),
                x_test=candidate.get("listing_title")
            )
            await Repository.record_event(
                run_id, "Extractor", "WARNING",
                f"File '{filename}' unreadable: {read_res['reason']}"
            )
            return {"extract_ok": False, "reason": read_res["reason"]}

        raw_text = read_res["text"]

        # Step 1: Regex extraction
        regex_res = extract_with_regex(raw_text)
        extract_source = "regex"
        extract_note = "Extracted via template regex"

        name = regex_res["name"]
        patient_id = regex_res["patient_id"]
        report_id = regex_res["report_id"] or candidate.get("portal_report_id")
        doc_date = regex_res["date"]
        test = regex_res["test"] or candidate.get("listing_title")

        # Step 2: LLM fallback ONLY when name or date is missing
        if not name or not doc_date:
            logger.info(f"Regex missed name ({name}) or date ({doc_date}) for {filename}. Calling LLM fallback...")
            llm_res = await extract_with_llm(raw_text)
            if llm_res:
                extract_source = "regex+llm"
                # Step 3: Guardrail - check LLM output against raw text
                if not name and llm_res.get("name"):
                    validated_name = validate_against_raw_text(llm_res.get("name"), raw_text)
                    if validated_name:
                        name = validated_name
                    else:
                        extract_note += " | Dropped invented name from LLM"

                if not doc_date and llm_res.get("date"):
                    date_candidate = parse_iso_date(llm_res.get("date"))
                    if date_candidate:
                        # Check if date string or components appear in text
                        if str(date_candidate) in raw_text or str(date_candidate.year) in raw_text:
                            doc_date = date_candidate
                        else:
                            extract_note += " | Dropped invented date from LLM"

                if not patient_id and llm_res.get("patient_id"):
                    patient_id = validate_against_raw_text(llm_res.get("patient_id"), raw_text)

                if not test and llm_res.get("test"):
                    test = validate_against_raw_text(llm_res.get("test"), raw_text)

        extract_ok = bool(name and doc_date)

        # Update candidate row
        await Repository.update_candidate_extraction(
            candidate_id=cand_id,
            extract_ok=extract_ok,
            extract_note=extract_note,
            extract_source=extract_source,
            x_name=name,
            x_patient_id=patient_id,
            x_report_id=report_id,
            x_date=doc_date,
            x_test=test
        )

        await Repository.record_event(
            run_id, "Extractor", "INFO",
            f"Extracted '{filename}': Name='{name}', Date='{doc_date}', ID='{report_id}', Test='{test}' ({extract_source})."
        )

        return {
            "extract_ok": extract_ok,
            "x_name": name,
            "x_patient_id": patient_id,
            "x_report_id": report_id,
            "x_date": doc_date,
            "x_test": test
        }
