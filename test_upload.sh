#!/bin/bash

echo "Creating test PDF..."
echo "%PDF-1.4
Test Evidence Document - $(date)" > test_file.pdf

# Compute SHA-256
HASH=$(sha256sum test_file.pdf | awk '{print $1}')
echo "File hash: $HASH"

# Create evidence JSON
cat > evidence.json <<EOF
{
  "evidence_id": "ev_test_$(date +%s)",
  "application_id": "app_test_001",
  "evidence_type": "document",
  "sha256_hash_device": "$HASH",
  "captured_at_device": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "gps_coordinates": {
    "latitude": 64.1466,
    "longitude": -21.9426,
    "accuracy_meters": 10.0
  },
  "uploader_role": "applicant_owner",
  "mime_type": "application/pdf",
  "file_size_bytes": $(wc -c < test_file.pdf)
}
EOF

# Upload
echo "Uploading evidence..."
curl -X POST http://localhost:8000/api/v1/evidence \
  -F "file=@test_file.pdf" \
  -F "evidence_json=$(cat evidence.json)" \
  | jq .

echo ""
echo "Test complete!"

# Cleanup
rm test_file.pdf evidence.json
