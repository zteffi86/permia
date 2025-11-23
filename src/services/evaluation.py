import uuid
import hashlib
import json
from typing import Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..db.models import ApplicationFact, DecisionSnapshot, Application


class EvaluationEngine:
    """Rule evaluation engine for permit decisions"""

    def __init__(self):
        self.rules: dict[str, Any] = {}

    async def evaluate(self, application_id: str, facts: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluate rules for an application

        Args:
            application_id: Application identifier
            facts: Dictionary of facts to evaluate

        Returns:
            Evaluation result with outcomes
        """
        # TODO: Implement actual rule evaluation logic
        # For Phase 1, this is a placeholder that returns a basic evaluation
        rule_outcomes = []

        # Example placeholder rules
        if facts:
            rule_outcomes.append({
                "rule_id": "facts_present",
                "rule_name": "Facts Present Check",
                "outcome": "passed",
                "message": f"{len(facts)} facts provided"
            })

        # Determine overall recommendation
        overall_recommendation = "approved" if facts else "insufficient_data"

        return {
            "application_id": application_id,
            "overall_recommendation": overall_recommendation,
            "rule_outcomes": rule_outcomes,
        }


class EvaluationExecutor:
    """Executor for running evaluations and creating snapshots"""

    def __init__(self, db: Session):
        self.db = db
        self.engine = EvaluationEngine()

    async def execute_evaluation(
        self,
        application_id: str,
        trigger_type: str,
        trigger_metadata: Optional[dict[str, Any]] = None,
        rule_ids: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Execute evaluation and create snapshot

        Args:
            application_id: Application to evaluate
            trigger_type: How evaluation was triggered
            trigger_metadata: Additional metadata about the trigger
            rule_ids: Specific rules to evaluate (None = all)

        Returns:
            Evaluation result with snapshot ID
        """
        # Fetch all facts for the application
        facts = self.db.query(ApplicationFact).filter_by(
            application_id=application_id
        ).all()

        # Convert facts to dictionary
        facts_dict = {
            fact.fact_name: {
                "value": fact.fact_value.get("value"),
                "type": fact.fact_type,
                "evidence_id": fact.supporting_evidence_id,
                "confidence": fact.extraction_confidence
            }
            for fact in facts
        }

        # Run evaluation
        eval_result = await self.engine.evaluate(application_id, facts_dict)

        # Create snapshot
        snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"

        # Compute hash of facts snapshot
        facts_json = json.dumps(facts_dict, sort_keys=True)
        snapshot_hash = hashlib.sha256(facts_json.encode()).hexdigest()

        snapshot = DecisionSnapshot(
            snapshot_id=snapshot_id,
            application_id=application_id,
            snapshot_version=1,
            trigger_type=trigger_type,
            trigger_metadata=trigger_metadata,
            facts_snapshot=facts_dict,
            rule_outcomes=eval_result["rule_outcomes"],
            overall_recommendation=eval_result["overall_recommendation"],
            snapshot_hash=snapshot_hash,
            signature=None  # TODO: Implement digital signature
        )

        self.db.add(snapshot)

        # Update application's latest_snapshot_id
        application = self.db.query(Application).filter_by(
            application_id=application_id
        ).first()

        if application:
            application.latest_snapshot_id = snapshot_id

        self.db.commit()
        self.db.refresh(snapshot)

        # Return result
        return {
            "snapshot_id": snapshot_id,
            "application_id": application_id,
            "overall_recommendation": eval_result["overall_recommendation"],
            "rule_outcomes": eval_result["rule_outcomes"],
            "facts_count": len(facts_dict),
            "rules_evaluated": len(eval_result["rule_outcomes"]),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def create_evaluation_executor(db: Session) -> EvaluationExecutor:
    """Factory function to create an evaluation executor"""
    return EvaluationExecutor(db)


# Singleton instance (legacy)
evaluation_engine = EvaluationEngine()
