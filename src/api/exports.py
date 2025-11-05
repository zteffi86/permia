"""
Export API endpoints for creating and downloading evidence packages
"""
import logging
import uuid
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional

from ..schemas.exports import (
    ExportCreateRequest,
    ExportStatusResponse,
    ExportDownloadResponse,
    ExportListItem,
)
from ..db.models import Export
from ..core.database import get_db
from ..core.errors import problem_response
from ..core.auth import get_current_user, AuthContext
from ..core.config import settings
from ..services.exports import export_service
from ..services.storage import storage_service
from ..services.audit import audit_service


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/applications/{application_id}", response_model=ExportStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    request: Request,
    application_id: str,
    export_request: ExportCreateRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_current_user),
):
    """
    Create a new export package for an application

    Returns immediately with export ID and status "pending".
    Client should poll GET /exports/{export_id} for completion.
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    tenant_id = auth.tenant_id if auth else "dev_tenant"
    user_id = auth.user_id if auth else "dev_user"

    # Generate export ID
    export_id = f"export_{uuid.uuid4().hex[:16]}"

    # Create export record
    db_export = Export(
        export_id=export_id,
        application_id=application_id,
        tenant_id=tenant_id,
        format=export_request.format,
        include_metadata=export_request.include_metadata,
        sign_package=export_request.sign_package,
        status="pending",
        created_by=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.EXPORT_RETENTION_DAYS),
        correlation_id=correlation_id,
    )

    try:
        db.add(db_export)
        db.commit()
        db.refresh(db_export)

        # Log export creation
        audit_service.log(
            db=db,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            actor_id=user_id,
            actor_role=auth.role if auth else "dev",
            action="export.create",
            resource_type="export",
            resource_id=export_id,
            result="success",
            metadata={"application_id": application_id},
        )

        # Process export immediately (in production, this would be async/background task)
        try:
            _process_export(db, db_export, tenant_id)
        except Exception as e:
            logger.error(f"Failed to process export {export_id}: {e}")
            db_export.status = "failed"
            db_export.error_message = str(e)
            db.commit()

        db.refresh(db_export)

    except Exception as e:
        db.rollback()
        return problem_response(
            request=request,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="EXPORT_CREATION_FAILED",
            title="Failed to Create Export",
            detail=str(e),
        )

    return ExportStatusResponse(
        export_id=db_export.export_id,
        application_id=db_export.application_id,
        status=db_export.status,
        file_count=db_export.file_count,
        total_size_bytes=db_export.total_size_bytes,
        created_at=db_export.created_at,
        completed_at=db_export.completed_at,
        expires_at=db_export.expires_at,
        error_message=db_export.error_message,
    )


def _process_export(db: Session, db_export: Export, tenant_id: str):
    """
    Process export (synchronous for MVP, should be async in production)
    """
    try:
        # Update status
        db_export.status = "processing"
        db.commit()

        # Create export package
        zip_bytes, file_count, signature = export_service.create_export_package(
            db=db,
            export_id=db_export.export_id,
            application_id=db_export.application_id,
            tenant_id=tenant_id,
            include_metadata=db_export.include_metadata,
            sign_package=db_export.sign_package,
        )

        # Upload to storage
        storage_path = f"{settings.EXPORT_STORAGE_PREFIX}{db_export.export_id}.zip"
        blob_client = storage_service.client.get_blob_client(
            container=storage_service.container_name,
            blob=storage_path,
        )
        blob_client.upload_blob(zip_bytes, overwrite=True, content_settings={"content_type": "application/zip"})

        # Update export record
        db_export.status = "completed"
        db_export.storage_path = storage_path
        db_export.file_count = file_count
        db_export.total_size_bytes = len(zip_bytes)
        db_export.signature = signature
        db_export.completed_at = datetime.now(timezone.utc)

        db.commit()

    except Exception as e:
        logger.error(f"Export processing failed: {e}")
        db_export.status = "failed"
        db_export.error_message = str(e)
        db.commit()
        raise


@router.get("/{export_id}", response_model=ExportStatusResponse)
async def get_export_status(
    request: Request,
    export_id: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_current_user),
):
    """
    Get export status

    Poll this endpoint until status is "completed" or "failed"
    """
    tenant_id = auth.tenant_id if auth else "dev_tenant"

    export = (
        db.query(Export)
        .filter(
            Export.export_id == export_id,
            Export.tenant_id == tenant_id,
        )
        .first()
    )

    if not export:
        return problem_response(
            request=request,
            status=status.HTTP_404_NOT_FOUND,
            code="EXPORT_NOT_FOUND",
            title="Export Not Found",
            detail=f"Export {export_id} not found",
        )

    return ExportStatusResponse(
        export_id=export.export_id,
        application_id=export.application_id,
        status=export.status,
        file_count=export.file_count,
        total_size_bytes=export.total_size_bytes,
        created_at=export.created_at,
        completed_at=export.completed_at,
        expires_at=export.expires_at,
        error_message=export.error_message,
    )


@router.get("/{export_id}/download", response_model=ExportDownloadResponse)
async def get_export_download_url(
    request: Request,
    export_id: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_current_user),
):
    """
    Get presigned download URL for completed export

    URL expires in 1 hour
    """
    tenant_id = auth.tenant_id if auth else "dev_tenant"

    export = (
        db.query(Export)
        .filter(
            Export.export_id == export_id,
            Export.tenant_id == tenant_id,
        )
        .first()
    )

    if not export:
        return problem_response(
            request=request,
            status=status.HTTP_404_NOT_FOUND,
            code="EXPORT_NOT_FOUND",
            title="Export Not Found",
            detail=f"Export {export_id} not found",
        )

    if export.status != "completed":
        return problem_response(
            request=request,
            status=status.HTTP_409_CONFLICT,
            code="EXPORT_NOT_READY",
            title="Export Not Ready",
            detail=f"Export status is '{export.status}', must be 'completed'",
        )

    # Check if expired
    if export.expires_at and export.expires_at < datetime.now(timezone.utc):
        return problem_response(
            request=request,
            status=status.HTTP_410_GONE,
            code="EXPORT_EXPIRED",
            title="Export Expired",
            detail=f"Export expired at {export.expires_at.isoformat()}",
        )

    # Generate presigned URL
    download_url = storage_service.generate_presigned_url(
        blob_path=export.storage_path,
        expires_in_seconds=3600,  # 1 hour
    )

    return ExportDownloadResponse(
        export_id=export.export_id,
        download_url=download_url,
        expires_in_seconds=3600,
        file_size_bytes=export.total_size_bytes,
    )


@router.get("/applications/{application_id}/list", response_model=list[ExportListItem])
async def list_exports_for_application(
    request: Request,
    application_id: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_current_user),
):
    """
    List all exports for an application (tenant-scoped)
    """
    tenant_id = auth.tenant_id if auth else "dev_tenant"

    exports = (
        db.query(Export)
        .filter(
            Export.application_id == application_id,
            Export.tenant_id == tenant_id,
        )
        .order_by(Export.created_at.desc())
        .all()
    )

    return [
        ExportListItem(
            export_id=e.export_id,
            application_id=e.application_id,
            status=e.status,
            file_count=e.file_count,
            created_at=e.created_at,
            expires_at=e.expires_at,
        )
        for e in exports
    ]
