"""
Snapshots API - Retrieve decision snapshots
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..db.models import DecisionSnapshot
from ..schemas.snapshots import SnapshotResponse, SnapshotSummary
from ..core.auth import get_current_user, AuthContext

router = APIRouter(prefix="/api/v1/snapshots", tags=["snapshots"])


@router.get("/{snapshot_id}", response_model=SnapshotResponse)
async def get_snapshot(
    snapshot_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
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
    from ..db.models import Application
    application = db.query(Application).filter_by(
        application_id=snapshot.application_id
    ).first()

    if not application or application.tenant_id != auth.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return snapshot


@router.get("/{snapshot_id}/summary", response_model=SnapshotSummary)
async def get_snapshot_summary(
    snapshot_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
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
    from ..db.models import Application
    application = db.query(Application).filter_by(
        application_id=snapshot.application_id
    ).first()

    if not application or application.tenant_id != auth.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return snapshot
