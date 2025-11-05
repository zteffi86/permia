"""
Pydantic schemas for export API
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal


class ExportCreateRequest(BaseModel):
    """Request to create an export package"""
    application_id: str = Field(..., description="Application ID to export")
    format: Literal["zip"] = Field(default="zip", description="Export format (currently only ZIP)")
    include_metadata: bool = Field(default=True, description="Include manifest.json with metadata")
    sign_package: bool = Field(default=True, description="Digitally sign the export package")


class ExportStatusResponse(BaseModel):
    """Export status response"""
    export_id: str
    application_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    file_count: Optional[int] = None
    total_size_bytes: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ExportDownloadResponse(BaseModel):
    """Export download URL response"""
    export_id: str
    download_url: str
    expires_in_seconds: int
    file_size_bytes: int


class ExportListItem(BaseModel):
    """Export list item"""
    export_id: str
    application_id: str
    status: str
    file_count: Optional[int] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
