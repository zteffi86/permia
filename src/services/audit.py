from sqlalchemy.orm import Session
from ..db.models import AuditLog


class AuditService:
    """Append-only audit logging"""

    def log(
        self,
        db: Session,
        correlation_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        action: str,
        resource_type: str,
        resource_id: str,
        result: str,
        metadata: dict | None = None,
    ) -> None:
        """
        Write audit log entry

        Args:
            db: Database session
            correlation_id: Request correlation ID
            tenant_id: Tenant identifier
            actor_id: Actor identifier (user ID, JWT sub)
            actor_role: Actor role
            action: Action performed (e.g., "evidence.upload")
            resource_type: Resource type (e.g., "evidence")
            resource_id: Resource identifier
            result: Outcome (success, failure, rejected)
            metadata: Additional metadata
        """
        entry = AuditLog(
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            metadata=metadata,
        )
        db.add(entry)
        # Commit is handled by caller


# Singleton
audit_service = AuditService()
