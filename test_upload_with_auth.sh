#!/bin/bash

echo "Generating dev token..."
TOKEN=$(python3 -c "from src.utils.dev_token import generate_dev_token; print(generate_dev_token(role='applicant_owner'))")

echo "Token: $TOKEN"
echo ""

# Create test file
echo "%PDF-1.4
Authenticated Test Evidence - $(date)" > test_file.pdf
HASH=$(sha256sum test_file.pdf | awk '{print $1}')

# Create evidence JSON
cat > evidence_auth.json <<EOF
{
  "evidence_id": "ev_auth_$(date +%s)",
  "application_id": "app_test_001",
  "evidence_type": "document",
  "sha256_hash_device": "$HASH",
  "captured_at_device": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "gps_coordinates": {
    "latitude": 64.1466,
    "longitude": -21.9426,
    "accuracy_meters": 10.0
  },
  "uploader_role": "inspector",
  "mime_type": "application/pdf",
  "file_size_bytes": $(wc -c < test_file.pdf)
}
EOF

echo "Uploading with authentication..."
curl -X POST http://localhost:8000/api/v1/evidence \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_file.pdf" \
  -F "evidence_json=$(cat evidence_auth.json)" \
  | jq .

rm test_file.pdf evidence_auth.json
