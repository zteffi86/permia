"""
Export service for creating and signing evidence packages
"""
import io
import zipfile
import json
import logging
from jose import jwt
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.models import Evidence, Export
from .storage import storage_service


logger = logging.getLogger(__name__)


class ExportService:
    """Service for creating signed export packages"""

    def __init__(self):
        self.private_key = self._load_private_key()
        self.public_key = self._load_public_key()

    def _load_private_key(self) -> str:
        """Load RSA private key for signing"""
        key_path = Path(settings.EXPORT_PRIVATE_KEY_PATH)
        if key_path.exists():
            return key_path.read_text()
        else:
            logger.warning("Export private key not found, using stub")
            return "STUB_PRIVATE_KEY"

    def _load_public_key(self) -> str:
        """Load RSA public key for verification"""
        key_path = Path(settings.EXPORT_PUBLIC_KEY_PATH)
        if key_path.exists():
            return key_path.read_text()
        else:
            return "STUB_PUBLIC_KEY"

    def create_export_package(
        self,
        db: Session,
        export_id: str,
        application_id: str,
        tenant_id: str,
        include_metadata: bool = True,
        sign_package: bool = True,
    ) -> Tuple[bytes, int, Optional[str]]:
        """
        Create a ZIP export package with evidence files

        Args:
            db: Database session
            export_id: Export ID
            application_id: Application ID
            tenant_id: Tenant ID for isolation
            include_metadata: Include manifest.json
            sign_package: Sign the manifest

        Returns:
            Tuple of (zip_bytes, file_count, signature)
        """
        # Get all evidence for application (tenant-scoped)
        evidence_list = (
            db.query(Evidence)
            .filter(
                Evidence.application_id == application_id,
                Evidence.tenant_id == tenant_id,
            )
            .order_by(Evidence.created_at)
            .all()
        )

        if not evidence_list:
            raise ValueError(f"No evidence found for application {application_id}")

        # Create ZIP in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add README
            readme_content = self._generate_readme(application_id, export_id)
            zip_file.writestr("README.txt", readme_content)

            # Add each evidence file
            evidence_metadata = []
            for idx, evidence in enumerate(evidence_list, 1):
                try:
                    # Download from blob storage
                    blob_client = storage_service.client.get_blob_client(
                        container=storage_service.container_name,
                        blob=evidence.storage_path,
                    )
                    file_bytes = blob_client.download_blob().readall()

                    # Determine file extension from MIME type
                    ext = self._get_extension_from_mime(evidence.mime_type)
                    filename = f"evidence/{idx:03d}_{evidence.evidence_id}{ext}"

                    # Add to ZIP
                    zip_file.writestr(filename, file_bytes)

                    # Collect metadata
                    evidence_metadata.append({
                        "evidence_id": evidence.evidence_id,
                        "filename": filename,
                        "evidence_type": evidence.evidence_type,
                        "mime_type": evidence.mime_type,
                        "file_size_bytes": evidence.file_size_bytes,
                        "sha256_hash": evidence.sha256_hash_server,
                        "captured_at": evidence.captured_at_device.isoformat(),
                        "gps_latitude": evidence.gps_latitude,
                        "gps_longitude": evidence.gps_longitude,
                        "integrity_passed": evidence.integrity_passed,
                        "uploader_role": evidence.uploader_role,
                    })

                except Exception as e:
                    logger.error(f"Failed to add evidence {evidence.evidence_id}: {e}")
                    # Continue with other files

            # Generate manifest
            manifest = {
                "export_id": export_id,
                "application_id": application_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "evidence_count": len(evidence_metadata),
                "evidence": evidence_metadata,
            }

            # Sign manifest if requested
            signature = None
            if sign_package:
                signature = self._sign_manifest(manifest)
                zip_file.writestr("signature.txt", signature)

            # Add manifest
            if include_metadata:
                zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))

            # Add public key for verification
            if sign_package and self.public_key != "STUB_PUBLIC_KEY":
                zip_file.writestr("public_key.pem", self.public_key)

        zip_bytes = zip_buffer.getvalue()
        return zip_bytes, len(evidence_list), signature

    def _generate_readme(self, application_id: str, export_id: str) -> str:
        """Generate README for export package"""
        return f"""Permía Evidence Export Package
================================

Application ID: {application_id}
Export ID: {export_id}
Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

This package contains evidence files and metadata for the specified application.

Contents:
---------
- evidence/          Evidence files (numbered by upload order)
- manifest.json      Detailed metadata for all evidence
- signature.txt      Digital signature (RS256) of the manifest
- public_key.pem     Public key for signature verification
- README.txt         This file

Verification:
-------------
The manifest.json file is digitally signed using RSA-4096.
You can verify the signature using the included public_key.pem.

For verification instructions, see: https://docs.permia.is/exports/verification

---
Generated by Permía (https://permia.is)
"""

    def _get_extension_from_mime(self, mime_type: str) -> str:
        """Get file extension from MIME type"""
        mime_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/heic": ".heic",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "application/pdf": ".pdf",
        }
        return mime_map.get(mime_type, ".bin")

    def _sign_manifest(self, manifest: dict) -> str:
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
            return f"UNSIGNED_DEV_MODE:{json.dumps(payload)}"

        # Production: sign with RSA
        return jwt.encode(payload, self.private_key, algorithm="RS256")


# Singleton
export_service = ExportService()
