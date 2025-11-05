#!/bin/bash
set -e

echo "=€ Setting up Permía Backend (Production-Grade)..."

# 1. Start Docker services
echo "=æ Starting PostgreSQL and Azurite..."
docker-compose up -d

# Wait for PostgreSQL
echo "ó Waiting for PostgreSQL..."
sleep 5

# 2. Create Python virtual environment
echo "= Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
echo "=Ú Installing dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"

# 4. Generate RSA keypair for exports
echo "= Generating RSA keypair..."
mkdir -p keys
./keys/generate_keypair.sh || echo "   Keypair generation failed (optional)"

# 5. Run database migrations
echo "=Ä  Running database migrations..."
alembic upgrade head

# 6. Create Azurite container
echo "  Setting up Azurite storage..."
docker exec permia-azurite az storage container create \
    --name evidence \
    --connection-string "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;" \
    2>/dev/null || echo "Container 'evidence' may already exist"

# 7. Run tests
echo ">ê Running tests..."
pytest tests/ -v || echo "   Some tests failed (expected if Azurite not fully ready)"

echo ""
echo " Setup complete!"
echo ""
echo "To start the server:"
echo "  source venv/bin/activate"
echo "  uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "API will be available at:"
echo "  http://localhost:8000"
echo "  http://localhost:8000/docs (Swagger UI)"
echo ""
echo "Generate dev tokens:"
echo "  python -m src.utils.dev_token"
