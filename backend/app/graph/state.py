"""LangGraph workflow state definition.

Strict constraint: The state is small and holds only IDs, counts, approved status,
and human overrides. NEVER put file bytes or passwords in state or checkpoints!
"""

from typing import Dict, Any, List, Optional, Annotated
from pydantic import BaseModel, Field, field_validator

def merge_summaries(a: Optional[Dict[str, int]], b: Optional[Dict[str, int]]) -> Dict[str, int]:
    """Combines parallel outputs from fetcher nodes."""
    res = dict(a or {})
    if b:
        res.update(b)
    return res

class HealthRecordGraphState(BaseModel):
    run_id: str
    patient_name: str
    patient_id: Optional[str] = None
    patient_key: str
    user_id: Optional[str] = None
    date_from: str  # ISO date string
    date_to: str    # ISO date string
    labs: List[str] = Field(default_factory=list)

    @field_validator("run_id", mode="before")
    @classmethod
    def coerce_run_id_to_str(cls, v):
        return str(v)

    @field_validator("user_id", "patient_id", mode="before")
    @classmethod
    def coerce_optional_id_to_str(cls, v):
        if v is None:
            return None
        return str(v)

    @field_validator("candidate_ids", mode="before")
    @classmethod
    def coerce_candidate_ids_to_str(cls, v):
        if isinstance(v, list):
            return [str(x) for x in v]
        return v

    # Summaries (IDs and counts only) - Annotated with reducer for parallel fan-in
    fetch_summaries: Annotated[Dict[str, int], merge_summaries] = Field(default_factory=dict)
    candidate_ids: List[str] = Field(default_factory=list)
    decision_counts: Dict[str, int] = Field(default_factory=lambda: {
        "keep": 0,
        "duplicate": 0,
        "exclude": 0,
        "reject": 0,
        "needs_review": 0
    })

    # Human Approval
    approved: Optional[bool] = None
    overrides: Dict[str, str] = Field(default_factory=dict) # candidate_id -> "keep" | "skip"

    # Post-approval storage and recheck
    stored_count: int = 0
    rechecked_count: int = 0
    recheck_failures: int = 0

    # Overall execution status
    status: str = "pending"
    error: Optional[str] = None
