# Permia Backend

**Deterministic enforcement infrastructure for regulated industries.**

Production-grade backend with evidence upload, integrity validation, audit logging, and multi-tenant support.

## Features

 Evidence upload with cryptographic integrity validation
 SHA-256 hash verification (server-side)
 GPS accuracy & time drift validation
 EXIF metadata extraction & cross-validation
 MIME type sniffing with per-type whitelists
 Per-type size limits (photo 10MB, video 50MB, doc 25MB)
 30-day duplicate content detection
 Azure Blob Storage integration (hash-addressed keys)
 PostgreSQL persistence with audit logging
 Multi-tenant isolation
 JWT authentication (optional in dev)
 Idempotency via Idempotency-Key header
 RFC 7807 Problem Details errors
 Correlation IDs for request tracing
 Database migrations (Alembic)
 OpenAPI documentation

## Tech Stack

- **Framework:** FastAPI 0.109+
- **Database:** PostgreSQL 15
- **Storage:** Azure Blob Storage (Azurite for local dev)
- **ORM:** SQLAlchemy 2.0
- **Migrations:** Alembic
- **Python:** 3.11+

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Setup

```bash
# Clone repository
git clone <repo-url>
cd permia-backend

# Run setup script
chmod +x SETUP.sh
./SETUP.sh
```

### Run Server

```bash
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

API available at: `http://localhost:8000`
Docs available at: `http://localhost:8000/docs`

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Upload Evidence (with auth)
```bash
# Generate dev token
python -m src.utils.dev_token

# Upload
curl -X POST http://localhost:8000/api/v1/evidence \
  -H "Authorization: Bearer <token>" \
  -F "file=@image.jpg" \
  -F 'evidence_json={"evidence_id":"ev_001",...}'
```

### Get Evidence
```bash
curl http://localhost:8000/api/v1/evidence/ev_001
```

### List Evidence for Application
```bash
curl http://localhost:8000/api/v1/evidence/application/app_001
```

## Development

### Run Tests
```bash
pytest
```

### Format Code
```bash
black src/
ruff check src/ --fix
```

### Create Migration
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Generate Dev Token
```bash
python -m src.utils.dev_token
```

## Database Schema

### Evidence Table
- Cryptographic integrity validation
- Server-extracted EXIF metadata
- GPS coordinates & accuracy
- Time drift tracking
- Hash-based storage paths
- Multi-tenant isolation

### Audit Log
- Append-only event log
- Correlation IDs
- Actor tracking
- Tenant isolation

### Idempotency Cache
- Request deduplication
- 31-day TTL

## Scheduled Tasks

```bash
# Cleanup idempotency cache (run daily)
python -m src.tasks.cleanup
```

## Configuration

See `.env.example` for all configuration options.

Key settings:
- `AUTH_REQUIRED`: Enable/disable JWT auth (false in dev)
- `REPLAY_WINDOW_DAYS`: Duplicate content detection window (30 days)
- `MAX_TIME_DRIFT_SECONDS`: Maximum device/server time difference (30s)
- `MIN_GPS_ACCURACY_METERS`: Required GPS accuracy (50m)

## Security

- JWT authentication with role-based access
- Multi-tenant data isolation
- Server-side hash verification (zero trust)
- MIME type validation (whitelist-based)
- EXIF extraction & cross-validation
- Audit logging with correlation IDs
- Hash-addressed blob storage

## License

Proprietary - Svala Solutions ehf. (kt: 440425-0540)
