"""
Evaluation API - Trigger rule evaluation for applications
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import Application
from src.schemas.evaluation import EvaluationRequest, EvaluationResponse
from src.middleware.auth import get_current_user, get_tenant_id
from src.services.evaluation import create_evaluation_executor

router = APIRouter(prefix="/api/v1/applications/{application_id}", tags=["evaluation"])


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_application(
    application_id: str,
    eval_request: EvaluationRequest = EvaluationRequest(),
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Trigger on-demand evaluation of an application.
    
    Evaluates all rules (or specified subset) against current facts.
    Generates signed decision snapshot.
    Updates application.latest_snapshot_id.
    
    Returns evaluation results immediately (synchronous for MVP).
    """
    # Verify application exists and belongs to tenant
    application = db.query(Application).filter_by(
        application_id=application_id,
        tenant_id=tenant_id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application not found: {application_id}"
        )
    
    # Create evaluation executor
    executor = create_evaluation_executor(db)
    
    try:
        # Execute evaluation
        result = await executor.execute_evaluation(
            application_id=application_id,
            trigger_type="on_demand",
            trigger_metadata={
                "triggered_by": current_user["user_id"],
                "force": eval_request.force
            },
            rule_ids=eval_request.rule_ids
        )
        
        return EvaluationResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )
