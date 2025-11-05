"""Test configuration and fixtures"""
import os
import pytest

# Set up test environment variables before importing any application code
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only-min-32-chars")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;")
os.environ.setdefault("AZURE_STORAGE_CONTAINER_NAME", "evidence")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ENABLE_DOCS", "false")
os.environ.setdefault("LOG_LEVEL", "ERROR")
