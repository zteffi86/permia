from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Any


class SnapshotResponse(BaseModel):
    """Full snapshot response with all data"""

    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    application_id: str
    snapshot_version: int
    trigger_type: str
    trigger_metadata: Optional[dict[str, Any]] = None
    facts_snapshot: dict[str, Any]
    rule_outcomes: list[dict[str, Any]]
    overall_recommendation: str
    snapshot_hash: str
    signature: Optional[str] = None
    created_at: datetime


class SnapshotSummary(BaseModel):
    """Lightweight snapshot summary (no facts/outcomes)"""

    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    application_id: str
    snapshot_version: int
    trigger_type: str
    overall_recommendation: str
    created_at: datetime
