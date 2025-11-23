from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional, Callable
from .config import settings

security = HTTPBearer(auto_error=False)


class AuthContext:
    """Authenticated request context"""

    def __init__(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        email: Optional[str] = None,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role
        self.email = email

    @property
    def is_applicant(self) -> bool:
        return self.role == "applicant_owner"

    @property
    def is_inspector(self) -> bool:
        return self.role == "inspector"

    @property
    def is_supervisor(self) -> bool:
        return self.role == "supervisor"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def decode_jwt(token: str) -> dict:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[AuthContext]:
    """
    Extract authenticated user from JWT token

    Optional dependency - returns None if no token present
    For dev/testing without OIDC
    """
    if not credentials:
        return None

    payload = decode_jwt(credentials.credentials)

    # Extract claims
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    role = payload.get("role")
    email = payload.get("email")

    if not user_id or not tenant_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    # Validate role
    valid_roles = {"applicant_owner", "inspector", "supervisor", "admin"}
    if role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid role: {role}",
        )

    return AuthContext(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        email=email,
    )


async def require_auth(
    auth: Optional[AuthContext] = Depends(get_current_user),
) -> AuthContext:
    """Require authentication - raises 401 if not authenticated"""
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth


async def require_role(
    *allowed_roles: str,
) -> Callable:
    """Factory for role-based authorization"""

    async def _check_role(auth: AuthContext = Depends(require_auth)) -> AuthContext:
        if auth.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{auth.role}' not authorized for this operation",
            )
        return auth

    return _check_role
