from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


class ApplicationCreate(BaseModel):
    """Schema for creating a new application"""

    application_type: str = Field(..., min_length=1, max_length=255)
    business_name: str = Field(..., min_length=1, max_length=500)
    business_address: str = Field(..., min_length=1, max_length=1000)


class ApplicationResponse(BaseModel):
    """Response schema for application"""

    model_config = ConfigDict(from_attributes=True)

    application_id: str
    tenant_id: str
    applicant_id: str
    application_type: str
    business_name: str
    business_address: str
    status: str
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    latest_snapshot_id: Optional[str] = None


class ApplicationList(BaseModel):
    """List of applications with pagination"""

    applications: list[ApplicationResponse]
    total: int
