"""
Facts API - Submit and manage application facts
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..db.models import Application, ApplicationFact
from ..schemas.facts import FactSubmission, FactBatchSubmission, FactResponse, FactList
from ..core.auth import get_current_user, AuthContext

router = APIRouter(prefix="/api/v1/applications/{application_id}/facts", tags=["facts"])


def upsert_fact(
    db: Session,
    application_id: str,
    fact_data: FactSubmission
) -> ApplicationFact:
    """
    Helper function to upsert a fact (create or update).

    Returns the created or updated fact without committing.
    Caller is responsible for db.commit().
    """
    # Check if fact already exists
    existing_fact = db.query(ApplicationFact).filter_by(
        application_id=application_id,
        fact_name=fact_data.fact_name
    ).first()

    if existing_fact:
        # Update existing fact
        existing_fact.fact_value = {
            "value": fact_data.fact_value,
            "type": fact_data.fact_type
        }
        existing_fact.fact_type = fact_data.fact_type
        existing_fact.supporting_evidence_id = fact_data.supporting_evidence_id
        existing_fact.extractor_id = fact_data.extractor_id
        existing_fact.extraction_confidence = fact_data.extraction_confidence
        return existing_fact

    # Create new fact
    fact = ApplicationFact(
        fact_id=f"fact_{uuid.uuid4().hex[:12]}",
        application_id=application_id,
        fact_name=fact_data.fact_name,
        fact_value={
            "value": fact_data.fact_value,
            "type": fact_data.fact_type
        },
        fact_type=fact_data.fact_type,
        supporting_evidence_id=fact_data.supporting_evidence_id,
        extractor_id=fact_data.extractor_id,
        extraction_confidence=fact_data.extraction_confidence
    )
    db.add(fact)
    return fact


@router.post("", response_model=FactResponse, status_code=status.HTTP_201_CREATED)
async def submit_fact(
    application_id: str,
    fact_data: FactSubmission,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
):
    """
    Submit a single fact for an application.

    Fact value is stored as JSONB with type information.
    """
    # Verify application exists and belongs to tenant
    application = db.query(Application).filter_by(
        application_id=application_id,
        tenant_id=auth.tenant_id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application not found: {application_id}"
        )

    # Upsert the fact
    fact = upsert_fact(db, application_id, fact_data)
    db.commit()
    db.refresh(fact)

    return fact


@router.post("/batch", response_model=FactList, status_code=status.HTTP_201_CREATED)
async def submit_facts_batch(
    application_id: str,
    batch_data: FactBatchSubmission,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
):
    """
    Submit multiple facts in a single request.

    More efficient than submitting facts one at a time.
    """
    # Verify application exists
    application = db.query(Application).filter_by(
        application_id=application_id,
        tenant_id=auth.tenant_id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application not found: {application_id}"
        )
    
    created_facts = []

    for fact_data in batch_data.facts:
        fact = upsert_fact(db, application_id, fact_data)
        created_facts.append(fact)
    
    db.commit()
    
    # Refresh all facts
    for fact in created_facts:
        db.refresh(fact)
    
    return FactList(
        facts=created_facts,
        total=len(created_facts)
    )


@router.get("", response_model=FactList)
async def list_facts(
    application_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
):
    """
    List all facts for an application.
    """
    # Verify application exists
    application = db.query(Application).filter_by(
        application_id=application_id,
        tenant_id=auth.tenant_id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application not found: {application_id}"
        )
    
    facts = db.query(ApplicationFact).filter_by(
        application_id=application_id
    ).all()
    
    return FactList(
        facts=facts,
        total=len(facts)
    )


@router.delete("/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fact(
    application_id: str,
    fact_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
):
    """
    Delete a fact from an application.
    """
    # Verify application exists
    application = db.query(Application).filter_by(
        application_id=application_id,
        tenant_id=auth.tenant_id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application not found: {application_id}"
        )
    
    # Find and delete fact
    fact = db.query(ApplicationFact).filter_by(
        fact_id=fact_id,
        application_id=application_id
    ).first()
    
    if not fact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fact not found: {fact_id}"
        )
    
    db.delete(fact)
    db.commit()
    
    return None
