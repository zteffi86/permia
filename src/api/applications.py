"""
Applications API - Create and manage restaurant permit applications
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import Application
from src.schemas.applications import ApplicationCreate, ApplicationResponse, ApplicationList
from src.middleware.auth import get_current_user, get_tenant_id

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    application_data: ApplicationCreate,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Create a new restaurant permit application.
    
    Requires authentication. Application is automatically linked to the
    authenticated user's tenant.
    """
    # Create application
    application = Application(
        application_id=f"app_{uuid.uuid4().hex[:12]}",
        tenant_id=tenant_id,
        applicant_id=current_user["user_id"],
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
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Get application by ID.
    
    Only accessible by users in the same tenant.
    """
    application = db.query(Application).filter_by(
        application_id=application_id,
        tenant_id=tenant_id
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
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    List applications for current tenant.
    
    Optional filtering by status.
    Paginated with limit/offset.
    """
    query = db.query(Application).filter_by(tenant_id=tenant_id)
    
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
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
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
        tenant_id=tenant_id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application not found: {application_id}"
        )
    
    # Update status
    application.status = new_status
    
    if new_status == "submitted":
        from datetime import datetime
        application.submitted_at = datetime.utcnow()
    elif new_status == "under_review":
        from datetime import datetime
        application.reviewed_at = datetime.utcnow()
    elif new_status in ["approved", "rejected", "conditional"]:
        from datetime import datetime
        application.decided_at = datetime.utcnow()
    
    db.commit()
    db.refresh(application)
    
    return application
