"""
Facts API - Submit and manage application facts
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import Application, ApplicationFact
from src.schemas.facts import FactSubmission, FactBatchSubmission, FactResponse, FactList
from src.middleware.auth import get_current_user, get_tenant_id

router = APIRouter(prefix="/api/v1/applications/{application_id}/facts", tags=["facts"])


@router.post("", response_model=FactResponse, status_code=status.HTTP_201_CREATED)
async def submit_fact(
    application_id: str,
    fact_data: FactSubmission,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Submit a single fact for an application.
    
    Fact value is stored as JSONB with type information.
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
    
    # Check if fact already exists (update if so)
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
        
        db.commit()
        db.refresh(existing_fact)
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
    db.commit()
    db.refresh(fact)
    
    return fact


@router.post("/batch", response_model=FactList, status_code=status.HTTP_201_CREATED)
async def submit_facts_batch(
    application_id: str,
    batch_data: FactBatchSubmission,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Submit multiple facts in a single request.
    
    More efficient than submitting facts one at a time.
    """
    # Verify application exists
    application = db.query(Application).filter_by(
        application_id=application_id,
        tenant_id=tenant_id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application not found: {application_id}"
        )
    
    created_facts = []
    
    for fact_data in batch_data.facts:
        # Check if fact exists (upsert)
        existing_fact = db.query(ApplicationFact).filter_by(
            application_id=application_id,
            fact_name=fact_data.fact_name
        ).first()
        
        if existing_fact:
            # Update
            existing_fact.fact_value = {
                "value": fact_data.fact_value,
                "type": fact_data.fact_type
            }
            existing_fact.fact_type = fact_data.fact_type
            existing_fact.supporting_evidence_id = fact_data.supporting_evidence_id
            existing_fact.extractor_id = fact_data.extractor_id
            existing_fact.extraction_confidence = fact_data.extraction_confidence
            created_facts.append(existing_fact)
        else:
            # Create
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
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    List all facts for an application.
    """
    # Verify application exists
    application = db.query(Application).filter_by(
        application_id=application_id,
        tenant_id=tenant_id
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
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Delete a fact from an application.
    """
    # Verify application exists
    application = db.query(Application).filter_by(
        application_id=application_id,
        tenant_id=tenant_id
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
