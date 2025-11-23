from pydantic import BaseModel, Field
from typing import Optional, Any


class EvaluationRequest(BaseModel):
    """Request to trigger evaluation"""

    force: bool = Field(default=False, description="Force re-evaluation even if recent snapshot exists")
    rule_ids: Optional[list[str]] = Field(default=None, description="Specific rules to evaluate (None = all rules)")


class EvaluationResponse(BaseModel):
    """Response from evaluation execution"""

    snapshot_id: str
    application_id: str
    overall_recommendation: str
    rule_outcomes: list[dict[str, Any]]
    facts_count: int
    rules_evaluated: int
    timestamp: str
