import hashlib
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import AzureError
from ..core.config import settings


class StorageService:
    """Azure Blob Storage service for evidence files"""

    def __init__(self):
        self.client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self.container_name = settings.AZURE_STORAGE_CONTAINER_NAME
        self._ensure_container()

    def _ensure_container(self) -> None:
        """Create container if it doesn't exist"""
        try:
            container_client = self.client.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container()
        except AzureError as e:
            print(f"Warning: Could not verify/create container: {e}")

    def upload_file(
        self,
        file_content: bytes,
        sha256_hex: str,
        mime_type: str,
    ) -> str:
        """
        Upload file to blob storage using hash-based key

        Args:
            file_content: File bytes
            sha256_hex: SHA-256 hash (64 char hex)
            mime_type: MIME type

        Returns:
            Storage path (blob name)
        """
        # Hash-based path: evidence/{first-2-chars}/{full-hash}
        blob_name = f"evidence/{sha256_hex[:2]}/{sha256_hex}"

        blob_client = self.client.get_blob_client(
            container=self.container_name,
            blob=blob_name,
        )

        # Check if already exists (idempotent)
        if not blob_client.exists():
            content_settings = ContentSettings(content_type=mime_type)
            blob_client.upload_blob(
                file_content,
                overwrite=False,
                content_settings=content_settings,
            )

        return blob_name

    def delete_file(self, blob_path: str) -> None:
        """Delete blob (for compensation on DB failure)"""
        try:
            blob_client = self.client.get_blob_client(
                container=self.container_name,
                blob=blob_path,
            )
            blob_client.delete_blob()
        except AzureError:
            pass  # Best effort

    def compute_hash_streaming(self, file_bytes: bytes) -> str:
        """Compute SHA-256 hash"""
        return hashlib.sha256(file_bytes).hexdigest()

    def generate_presigned_url(self, blob_path: str, expires_in_seconds: int = 3600) -> str:
        """
        Generate a presigned URL for blob access

        Args:
            blob_path: The blob name (storage path)
            expires_in_seconds: URL expiry time in seconds (default 1 hour)

        Returns:
            Presigned URL string
        """
        try:
            blob_client = self.client.get_blob_client(
                container=self.container_name,
                blob=blob_path,
            )

            # Parse account key from connection string
            conn_parts = dict(
                part.split("=", 1) for part in settings.AZURE_STORAGE_CONNECTION_STRING.split(";") if "=" in part
            )
            account_key = conn_parts.get("AccountKey")

            if not account_key:
                # Fallback: return blob URL without SAS (works for public containers)
                return blob_client.url

            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=blob_client.account_name,
                container_name=self.container_name,
                blob_name=blob_path,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(seconds=expires_in_seconds),
            )

            # Return full URL with SAS token
            return f"{blob_client.url}?{sas_token}"

        except Exception as e:
            # Fallback: return base URL
            blob_client = self.client.get_blob_client(
                container=self.container_name,
                blob=blob_path,
            )
            return blob_client.url

    def check_health(self) -> bool:
        """Check if storage is accessible"""
        try:
            container_client = self.client.get_container_client(self.container_name)
            return container_client.exists()
        except:
            return False


# Singleton instance
storage_service = StorageService()
