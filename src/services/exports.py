from jose import jwt
from datetime import datetime, timezone
from pathlib import Path
from ..core.config import settings


class ExportService:
    """Service for signing case exports (RS256 JWS)"""

    def __init__(self):
        self.private_key = self._load_private_key()
        self.public_key = self._load_public_key()

    def _load_private_key(self) -> str:
        """Load RSA private key for signing"""
        key_path = Path(settings.EXPORT_PRIVATE_KEY_PATH)
        if key_path.exists():
            return key_path.read_text()
        else:
            print("Warning: Export private key not found, using stub")
            return "STUB_PRIVATE_KEY"

    def _load_public_key(self) -> str:
        """Load RSA public key for verification"""
        key_path = Path(settings.EXPORT_PUBLIC_KEY_PATH)
        if key_path.exists():
            return key_path.read_text()
        else:
            return "STUB_PUBLIC_KEY"

    def sign_export(self, manifest: dict) -> str:
        """
        Sign export manifest with RS256

        Args:
            manifest: Export manifest dictionary

        Returns:
            JWS compact serialization string
        """
        payload = {
            **manifest,
            "signed_at": datetime.now(timezone.utc).isoformat(),
            "issuer": "permia.is",
        }

        if self.private_key == "STUB_PRIVATE_KEY":
            # Dev mode: return unsigned JSON
            return f"UNSIGNED:{payload}"

        # Production: sign with RSA
        return jwt.encode(payload, self.private_key, algorithm="RS256")


# Singleton
export_service = ExportService()
