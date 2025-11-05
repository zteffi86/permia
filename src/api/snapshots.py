"""
Snapshots API - Retrieve decision snapshots
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import DecisionSnapshot
from src.schemas.snapshots import SnapshotResponse, SnapshotSummary
from src.middleware.auth import get_current_user, get_tenant_id

router = APIRouter(prefix="/api/v1/snapshots", tags=["snapshots"])


@router.get("/{snapshot_id}", response_model=SnapshotResponse)
async def get_snapshot(
    snapshot_id: str,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Get full decision snapshot by ID.
    
    Includes complete facts snapshot and all rule outcomes.
    Only accessible to users in the same tenant as the application.
    """
    # Get snapshot
    snapshot = db.query(DecisionSnapshot).filter_by(
        snapshot_id=snapshot_id
    ).first()
    
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot not found: {snapshot_id}"
        )
    
    # Verify tenant access via application
    from src.db.models import Application
    application = db.query(Application).filter_by(
        application_id=snapshot.application_id
    ).first()
    
    if not application or application.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return snapshot


@router.get("/{snapshot_id}/summary", response_model=SnapshotSummary)
async def get_snapshot_summary(
    snapshot_id: str,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Get snapshot summary (counts only, no facts/outcomes).
    
    Lighter response for listing/overview purposes.
    """
    snapshot = db.query(DecisionSnapshot).filter_by(
        snapshot_id=snapshot_id
    ).first()
    
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot not found: {snapshot_id}"
        )
    
    # Verify tenant access
    from src.db.models import Application
    application = db.query(Application).filter_by(
        application_id=snapshot.application_id
    ).first()
    
    if not application or application.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return snapshot
