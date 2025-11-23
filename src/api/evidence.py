from fastapi import APIRouter, UploadFile, File, Form, Depends, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional
import hashlib

from ..schemas.evidence import (
    EvidenceUploadRequest,
    EvidenceResponse,
    EvidenceDetailResponse,
)
from ..db.models import Evidence, IdempotencyCache
from ..core.database import get_db
from ..core.errors import problem_response
from ..core.auth import get_current_user, AuthContext
from ..core.config import settings
from ..services.storage import storage_service
from ..services.integrity import integrity_service
from ..services.exif_extractor import exif_extractor
from ..services.audit import audit_service

router = APIRouter()


@router.post("/", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    request: Request,
    file: Annotated[UploadFile, File(description="Evidence file")],
    evidence_json: Annotated[str, Form(description="EvidenceUploadRequest JSON")],
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_current_user),
) -> EvidenceResponse:
    """
    Upload evidence file with cryptographic integrity validation

    **Authentication:**
    - Optional in dev mode (AUTH_REQUIRED=false)
    - Required in production
    - Role from JWT overrides client payload

    **Security features:**
    - Server-side hash computation (streaming)
    - Server-side EXIF extraction & GPS/time cross-validation
    - Server-side MIME sniffing with per-type whitelists
    - Per-type size limits (photo 10MB, video 50MB, doc 25MB)
    - 30-day replay window for duplicate detection
    - Tenant isolation
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    # Enforce auth in production
    if settings.AUTH_REQUIRED and not auth:
        return problem_response(
            request=request,
            status=status.HTTP_401_UNAUTHORIZED,
            code="AUTHENTICATION_REQUIRED",
            title="Authentication Required",
            detail="This endpoint requires authentication in production mode",
        )

    # Use dev defaults if no auth
    tenant_id = auth.tenant_id if auth else "dev_tenant"
    uploader_id = auth.user_id if auth else "dev_user"
    uploader_role = auth.role if auth else "applicant_owner"

    # Content-Length precheck
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            size = int(content_length)
            # Use max across all types (50 MB for video)
            if size > 50 * 1024 * 1024:
                audit_service.log(
                    db=db,
                    correlation_id=correlation_id,
                    tenant_id=tenant_id,
                    actor_id=uploader_id,
                    actor_role=uploader_role,
                    action="evidence.upload",
                    resource_type="evidence",
                    resource_id="precheck",
                    result="rejected",
                    metadata={"reason": "content_length_exceeds_limit", "size": size},
                )
                db.commit()
                return problem_response(
                    request=request,
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    code="FILE_TOO_LARGE",
                    title="File Size Exceeds Limit",
                    detail=f"Content-Length {size} exceeds maximum 50MB",
                )
        except ValueError:
            pass

    # ========== 1. IDEMPOTENCY CHECK ==========
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key:
        cached = (
            db.query(IdempotencyCache)
            .filter(
                IdempotencyCache.idempotency_key == idempotency_key,
                IdempotencyCache.tenant_id == tenant_id,
            )
            .first()
        )

        if cached:
            return EvidenceResponse.model_validate_json(cached.response_json)

    # ========== 2. PARSE EVIDENCE METADATA ==========
    try:
        evidence = EvidenceUploadRequest.model_validate_json(evidence_json)
    except Exception as e:
        audit_service.log(
            db=db,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            actor_id=uploader_id,
            actor_role=uploader_role,
            action="evidence.upload",
            resource_type="evidence",
            resource_id=evidence_json[:50] if evidence_json else "unknown",
            result="failure",
            metadata={"error": "invalid_json", "detail": str(e)},
        )
        db.commit()
        return problem_response(
            request=request,
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="INVALID_EVIDENCE_JSON",
            title="Invalid Evidence Metadata",
            detail=str(e),
        )

    # ========== 3. CHECK DUPLICATE EVIDENCE_ID (tenant-scoped) ==========
    existing = (
        db.query(Evidence)
        .filter(
            Evidence.evidence_id == evidence.evidence_id,
            Evidence.tenant_id == tenant_id,
        )
        .first()
    )

    if existing:
        audit_service.log(
            db=db,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            actor_id=uploader_id,
            actor_role=uploader_role,
            action="evidence.upload",
            resource_type="evidence",
            resource_id=evidence.evidence_id,
            result="rejected",
            metadata={"reason": "duplicate_evidence_id"},
        )
        db.commit()
        return problem_response(
            request=request,
            status=status.HTTP_409_CONFLICT,
            code="DUPLICATE_EVIDENCE_ID",
            title="Evidence ID Already Exists",
            detail=f"Evidence {evidence.evidence_id} already exists",
        )

    # ========== 4. STREAMING HASH + SIZE ENFORCEMENT ==========
    hasher = hashlib.sha256()
    file_size = 0
    chunks = []
    chunk_size = 65536

    # Per-type limit
    from ..core.mime_config import get_policy

    policy = get_policy(evidence.evidence_type.value)
    max_size = policy.max_size_mb * 1024 * 1024

    try:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break

            file_size += len(chunk)

            if file_size > max_size:
                audit_service.log(
                    db=db,
                    correlation_id=correlation_id,
                    tenant_id=tenant_id,
                    actor_id=uploader_id,
                    actor_role=uploader_role,
                    action="evidence.upload",
                    resource_type="evidence",
                    resource_id=evidence.evidence_id,
                    result="rejected",
                    metadata={
                        "reason": "file_too_large",
                        "size": file_size,
                        "limit": max_size,
                        "type": evidence.evidence_type.value,
                    },
                )
                db.commit()
                return problem_response(
                    request=request,
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    code="FILE_TOO_LARGE",
                    title="File Size Exceeds Limit",
                    detail=f"{evidence.evidence_type.value} limit: {policy.max_size_mb}MB",
                )

            hasher.update(chunk)
            chunks.append(chunk)

        file_bytes = b"".join(chunks)
        server_hash = hasher.hexdigest()

    except Exception as e:
        audit_service.log(
            db=db,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            actor_id=uploader_id,
            actor_role=uploader_role,
            action="evidence.upload",
            resource_type="evidence",
            resource_id=evidence.evidence_id,
            result="failure",
            metadata={"error": "file_read_error", "detail": str(e)},
        )
        db.commit()
        return problem_response(
            request=request,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="FILE_READ_ERROR",
            title="Failed to Read File",
            detail=str(e),
        )

    # ========== 5. DUPLICATE CONTENT (tenant + replay window) ==========
    replay_cutoff = datetime.now(timezone.utc) - timedelta(days=settings.REPLAY_WINDOW_DAYS)
    existing_hash = (
        db.query(Evidence)
        .filter(
            Evidence.tenant_id == tenant_id,
            Evidence.sha256_hash_server == server_hash,
            Evidence.created_at >= replay_cutoff,
        )
        .first()
    )

    if existing_hash:
        audit_service.log(
            db=db,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            actor_id=uploader_id,
            actor_role=uploader_role,
            action="evidence.upload",
            resource_type="evidence",
            resource_id=evidence.evidence_id,
            result="rejected",
            metadata={
                "reason": "duplicate_content",
                "original_evidence_id": existing_hash.evidence_id,
                "hash": server_hash,
            },
        )
        db.commit()
        return problem_response(
            request=request,
            status=status.HTTP_409_CONFLICT,
            code="DUPLICATE_CONTENT",
            title="Duplicate Content Detected",
            detail={
                "message": f"This file was already uploaded within {settings.REPLAY_WINDOW_DAYS} days",
                "original_evidence_id": existing_hash.evidence_id,
                "uploaded_at": existing_hash.created_at.isoformat(),
            },
        )

    # ========== 6. EXTRACT EXIF ==========
    exif_data = {}
    if evidence.evidence_type == "photo":
        exif_data = exif_extractor.extract(file_bytes)

    # ========== 7. INTEGRITY VALIDATION ==========
    integrity_check, detected_mime = integrity_service.validate(
        evidence=evidence,
        server_hash=server_hash,
        file_size=file_size,
        file_bytes=file_bytes,
        exif_data=exif_data,
    )

    if not integrity_check.integrity_passed:
        audit_service.log(
            db=db,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            actor_id=uploader_id,
            actor_role=uploader_role,
            action="evidence.upload",
            resource_type="evidence",
            resource_id=evidence.evidence_id,
            result="rejected",
            metadata={
                "reason": "integrity_failed",
                "issues": integrity_check.issues,
            },
        )
        db.commit()
        return problem_response(
            request=request,
            status=status.HTTP_400_BAD_REQUEST,
            code="INTEGRITY_VALIDATION_FAILED",
            title="Integrity Validation Failed",
            detail={"integrity_check": integrity_check.model_dump()},
        )

    # ========== 8. UPLOAD TO STORAGE ==========
    try:
        storage_path = storage_service.upload_file(
            file_content=file_bytes,
            sha256_hex=server_hash,
            mime_type=detected_mime,
        )
    except Exception as e:
        audit_service.log(
            db=db,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            actor_id=uploader_id,
            actor_role=uploader_role,
            action="evidence.upload",
            resource_type="evidence",
            resource_id=evidence.evidence_id,
            result="failure",
            metadata={"error": "storage_upload_failed", "detail": str(e)},
        )
        db.commit()
        return problem_response(
            request=request,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="STORAGE_UPLOAD_FAILED",
            title="Failed to Upload to Storage",
            detail=str(e),
        )

    # ========== 9. CALCULATE TIME DRIFT ==========
    server_time = datetime.now(timezone.utc)
    device_time = evidence.captured_at_device
    if device_time.tzinfo is None:
        device_time = device_time.replace(tzinfo=timezone.utc)
    time_drift_seconds = abs((server_time - device_time).total_seconds())

    # ========== 10. PERSIST TO DATABASE ==========
    db_evidence = Evidence(
        evidence_id=evidence.evidence_id,
        application_id=evidence.application_id,
        tenant_id=tenant_id,
        evidence_type=evidence.evidence_type.value,
        mime_type=evidence.mime_type,
        mime_type_detected=detected_mime,
        file_size_bytes=file_size,
        sha256_hash_device=evidence.sha256_hash_device,
        sha256_hash_server=server_hash,
        captured_at_device=device_time,
        captured_at_server=server_time,
        time_drift_seconds=time_drift_seconds,
        gps_latitude=evidence.gps_coordinates.latitude,
        gps_longitude=evidence.gps_coordinates.longitude,
        gps_accuracy_meters=evidence.gps_coordinates.accuracy_meters,
        exif_present=exif_data.get("has_exif", False),
        exif_data=exif_data.get("raw") if exif_data.get("has_exif") else None,
        exif_gps_latitude=exif_data.get("gps_latitude"),
        exif_gps_longitude=exif_data.get("gps_longitude"),
        exif_datetime=exif_data.get("datetime"),
        uploader_role=uploader_role,
        uploader_id=uploader_id,
        storage_path=storage_path,
        integrity_passed=integrity_check.integrity_passed,
        integrity_issues=integrity_check.issues if integrity_check.issues else None,
        correlation_id=correlation_id,
    )

    try:
        db.add(db_evidence)

        audit_service.log(
            db=db,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            actor_id=uploader_id,
            actor_role=uploader_role,
            action="evidence.upload",
            resource_type="evidence",
            resource_id=evidence.evidence_id,
            result="success",
            metadata={
                "application_id": evidence.application_id,
                "hash": server_hash,
                "size": file_size,
                "type": evidence.evidence_type.value,
            },
        )

        db.commit()
        db.refresh(db_evidence)

    except Exception as e:
        db.rollback()

        try:
            storage_service.delete_file(storage_path)
        except Exception:
            # Log but ignore cleanup failures - primary error is more important
            pass

        return problem_response(
            request=request,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="DATABASE_WRITE_FAILED",
            title="Failed to Save Evidence",
            detail=str(e),
        )

    # ========== 11. CACHE IDEMPOTENCY ==========
    # Generate presigned URL for client access
    storage_uri = storage_service.generate_presigned_url(
        blob_path=db_evidence.storage_path,
        expires_in_seconds=3600
    )

    response = EvidenceResponse(
        evidence_id=db_evidence.evidence_id,
        application_id=db_evidence.application_id,
        storage_uri=storage_uri,
        integrity_passed=db_evidence.integrity_passed,
        integrity_check=integrity_check,
        created_at=db_evidence.created_at,
    )

    if idempotency_key:
        try:
            cache_entry = IdempotencyCache(
                idempotency_key=idempotency_key,
                tenant_id=tenant_id,
                response_json=response.model_dump_json(),
            )
            db.add(cache_entry)
            db.commit()
        except Exception:
            # Ignore idempotency cache failures - response is already successful
            pass

    return response


@router.get("/{evidence_id}", response_model=EvidenceDetailResponse)
async def get_evidence(
    request: Request,
    evidence_id: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_current_user),
) -> EvidenceDetailResponse:
    """Retrieve evidence record by ID (tenant-scoped)"""
    tenant_id = auth.tenant_id if auth else "dev_tenant"

    evidence = (
        db.query(Evidence)
        .filter(
            Evidence.evidence_id == evidence_id,
            Evidence.tenant_id == tenant_id,
        )
        .first()
    )

    if not evidence:
        return problem_response(
            request=request,
            status=status.HTTP_404_NOT_FOUND,
            code="EVIDENCE_NOT_FOUND",
            title="Evidence Not Found",
            detail=f"Evidence {evidence_id} not found",
        )

    # Generate presigned URL for client access
    storage_uri = storage_service.generate_presigned_url(
        blob_path=evidence.storage_path,
        expires_in_seconds=3600
    )

    return EvidenceDetailResponse(
        evidence_id=evidence.evidence_id,
        application_id=evidence.application_id,
        evidence_type=evidence.evidence_type,
        mime_type=evidence.mime_type,
        file_size_bytes=evidence.file_size_bytes,
        sha256_hash_device=evidence.sha256_hash_device,
        sha256_hash_server=evidence.sha256_hash_server,
        captured_at_device=evidence.captured_at_device,
        captured_at_server=evidence.captured_at_server,
        time_drift_seconds=evidence.time_drift_seconds,
        gps_latitude=evidence.gps_latitude,
        gps_longitude=evidence.gps_longitude,
        gps_accuracy_meters=evidence.gps_accuracy_meters,
        exif_data=evidence.exif_data,
        uploader_role=evidence.uploader_role,
        storage_uri=storage_uri,
        integrity_passed=evidence.integrity_passed,
        integrity_issues=evidence.integrity_issues,
        created_at=evidence.created_at,
        updated_at=evidence.updated_at,
    )


@router.get("/application/{application_id}", response_model=list[EvidenceDetailResponse])
async def list_evidence_for_application(
    application_id: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_current_user),
) -> list[EvidenceDetailResponse]:
    """List all evidence for application (tenant-scoped)"""
    tenant_id = auth.tenant_id if auth else "dev_tenant"

    evidence_list = (
        db.query(Evidence)
        .filter(
            Evidence.application_id == application_id,
            Evidence.tenant_id == tenant_id,
        )
        .order_by(Evidence.created_at.desc())
        .all()
    )

    # Build response list with presigned URLs
    response_list = []
    for e in evidence_list:
        # Generate presigned URL for each evidence item
        storage_uri = storage_service.generate_presigned_url(
            blob_path=e.storage_path,
            expires_in_seconds=3600
        )

        response_list.append(
            EvidenceDetailResponse(
                evidence_id=e.evidence_id,
                application_id=e.application_id,
                evidence_type=e.evidence_type,
                mime_type=e.mime_type,
                file_size_bytes=e.file_size_bytes,
                sha256_hash_device=e.sha256_hash_device,
                sha256_hash_server=e.sha256_hash_server,
                captured_at_device=e.captured_at_device,
                captured_at_server=e.captured_at_server,
                time_drift_seconds=e.time_drift_seconds,
                gps_latitude=e.gps_latitude,
                gps_longitude=e.gps_longitude,
                gps_accuracy_meters=e.gps_accuracy_meters,
                exif_data=e.exif_data,
                uploader_role=e.uploader_role,
                storage_uri=storage_uri,
                integrity_passed=e.integrity_passed,
                integrity_issues=e.integrity_issues,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
        )

    return response_list
