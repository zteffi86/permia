from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from enum import Enum
from typing import Optional


class EvidenceType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"


class UploaderRole(str, Enum):
    APPLICANT_OWNER = "applicant_owner"
    INSPECTOR = "inspector"
    SUPERVISOR = "supervisor"


class GpsCoordinates(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_meters: float = Field(..., gt=0)


class EvidenceUploadRequest(BaseModel):
    """Schema for evidence upload request"""

    evidence_id: str = Field(..., min_length=1, max_length=255)
    application_id: str = Field(..., min_length=1, max_length=255)
    evidence_type: EvidenceType
    sha256_hash_device: str = Field(..., min_length=64, max_length=64)
    captured_at_device: datetime
    gps_coordinates: GpsCoordinates
    uploader_role: UploaderRole
    mime_type: str = Field(..., min_length=1, max_length=255)
    file_size_bytes: int = Field(..., gt=0)
    exif_data: Optional[dict[str, str]] = None

    @field_validator("sha256_hash_device")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        """Ensure hash is lowercase hex"""
        if not all(c in "0123456789abcdef" for c in v):
            raise ValueError("Hash must be lowercase hexadecimal")
        return v


class IntegrityCheckResult(BaseModel):
    """Result of integrity validation"""

    hash_match: bool
    exif_present: bool
    gps_accuracy_ok: bool
    time_drift_ok: bool
    file_size_ok: bool
    integrity_passed: bool
    issues: list[str] = []


class EvidenceResponse(BaseModel):
    """Response after evidence upload"""

    model_config = ConfigDict(from_attributes=True)

    evidence_id: str
    application_id: str
    storage_uri: Optional[str]
    integrity_passed: bool
    integrity_check: IntegrityCheckResult
    created_at: datetime


class EvidenceDetailResponse(BaseModel):
    """Detailed evidence information"""

    model_config = ConfigDict(from_attributes=True)

    evidence_id: str
    application_id: str
    evidence_type: str
    mime_type: str
    file_size_bytes: int
    sha256_hash_device: str
    sha256_hash_server: Optional[str]
    captured_at_device: datetime
    captured_at_server: Optional[datetime]
    time_drift_seconds: Optional[float]
    gps_latitude: float
    gps_longitude: float
    gps_accuracy_meters: float
    exif_data: Optional[dict]
    uploader_role: str
    storage_uri: Optional[str]
    integrity_passed: bool
    integrity_issues: Optional[list[str]]
    created_at: datetime
    updated_at: datetime
