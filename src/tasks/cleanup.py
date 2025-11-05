"""Cleanup tasks for cache and old records"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from ..db.models import IdempotencyCache
from ..core.database import SessionLocal


def cleanup_idempotency_cache(days: int = 31) -> int:
    """
    Delete idempotency cache entries older than N days

    Returns number of deleted entries
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        deleted = db.query(IdempotencyCache).filter(
            IdempotencyCache.created_at < cutoff
        ).delete()
        db.commit()
        return deleted
    finally:
        db.close()


if __name__ == "__main__":
    # Manual cleanup
    count = cleanup_idempotency_cache()
    print(f"Cleaned up {count} idempotency cache entries")
