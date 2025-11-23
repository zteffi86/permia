from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Any


class FactSubmission(BaseModel):
    """Schema for submitting a fact"""

    fact_name: str = Field(..., min_length=1, max_length=255)
    fact_value: Any
    fact_type: str = Field(..., min_length=1, max_length=50)  # string, number, boolean, date, etc.
    supporting_evidence_id: Optional[str] = None
    extractor_id: Optional[str] = None
    extraction_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class FactResponse(BaseModel):
    """Response schema for a fact"""

    model_config = ConfigDict(from_attributes=True)

    fact_id: str
    application_id: str
    fact_name: str
    fact_value: dict[str, Any]  # {value: ..., type: ...}
    fact_type: str
    supporting_evidence_id: Optional[str] = None
    extractor_id: Optional[str] = None
    extraction_confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class FactBatchSubmission(BaseModel):
    """Schema for batch fact submission"""

    facts: list[FactSubmission]


class FactList(BaseModel):
    """List of facts"""

    facts: list[FactResponse]
    total: int
