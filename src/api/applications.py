"""
Applications API - Create and manage restaurant permit applications
"""

import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..db.models import Application
from ..schemas.applications import ApplicationCreate, ApplicationResponse, ApplicationList
from ..core.auth import get_current_user, AuthContext

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    application_data: ApplicationCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
):
    """
    Create a new restaurant permit application.

    Requires authentication. Application is automatically linked to the
    authenticated user's tenant.
    """
    # Create application
    application = Application(
        application_id=f"app_{uuid.uuid4().hex[:12]}",
        tenant_id=auth.tenant_id,
        applicant_id=auth.user_id,
        application_type=application_data.application_type,
        business_name=application_data.business_name,
        business_address=application_data.business_address,
        status="draft"
    )
    
    db.add(application)
    db.commit()
    db.refresh(application)
    
    return application


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
):
    """
    Get application by ID.

    Only accessible by users in the same tenant.
    """
    application = db.query(Application).filter_by(
        application_id=application_id,
        tenant_id=auth.tenant_id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application not found: {application_id}"
        )
    
    return application


@router.get("", response_model=ApplicationList)
async def list_applications(
    status_filter: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
):
    """
    List applications for current tenant.

    Optional filtering by status.
    Paginated with limit/offset.
    """
    query = db.query(Application).filter_by(tenant_id=auth.tenant_id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    total = query.count()
    applications = query.offset(offset).limit(limit).all()
    
    return ApplicationList(
        applications=applications,
        total=total
    )


@router.patch("/{application_id}/status")
async def update_application_status(
    application_id: str,
    new_status: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
):
    """
    Update application status.

    Valid transitions:
    - draft → submitted
    - submitted → under_review
    - under_review → approved | rejected | conditional
    """
    application = db.query(Application).filter_by(
        application_id=application_id,
        tenant_id=auth.tenant_id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application not found: {application_id}"
        )
    
    # Update status
    application.status = new_status

    if new_status == "submitted":
        application.submitted_at = datetime.now(timezone.utc)
    elif new_status == "under_review":
        application.reviewed_at = datetime.now(timezone.utc)
    elif new_status in ["approved", "rejected", "conditional"]:
        application.decided_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(application)
    
    return application
