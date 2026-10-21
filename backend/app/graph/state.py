"""LangGraph workflow state definition.

Strict constraint: The state is small and holds only IDs, counts, approved status,
and human overrides. NEVER put file bytes or passwords in state or checkpoints!
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class HealthRecordGraphState(BaseModel):
    run_id: str
    patient_name: str
    patient_id: Optional[str] = None
    patient_key: str
    date_from: str  # ISO date string
    date_to: str    # ISO date string
    labs: List[str] = Field(default_factory=list)

    # Summaries (IDs and counts only)
    fetch_summaries: Dict[str, int] = Field(default_factory=dict) # lab -> staged_count
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
