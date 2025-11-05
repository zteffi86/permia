"""Development JWT token generator"""
from jose import jwt
from datetime import datetime, timedelta, timezone
from ..core.config import settings


def generate_dev_token(
    user_id: str = "dev_user_001",
    tenant_id: str = "tenant_reykjavik",
    role: str = "applicant_owner",
    email: str = "dev@permia.is",
) -> str:
    """
    Generate development JWT token

    Usage:
        token = generate_dev_token(role="inspector")
        headers = {"Authorization": f"Bearer {token}"}
    """
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


if __name__ == "__main__":
    print("Development tokens:\n")
    for role in ["applicant_owner", "inspector", "supervisor", "admin"]:
        token = generate_dev_token(role=role)
        print(f"{role}:")
        print(f"  {token}\n")
