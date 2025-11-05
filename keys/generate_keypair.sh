#!/bin/bash
set -e

# Generate RSA keypair for export signing
# Run this once during setup

KEYS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$KEYS_DIR/export_private_key.pem" ]; then
    echo "⚠️  Keys already exist. Skipping generation."
    echo "   To regenerate, delete existing keys first."
    exit 0
fi

echo "🔐 Generating RSA 4096-bit keypair for export signing..."

# Generate private key (RSA-4096 for production security)
openssl genrsa -out "$KEYS_DIR/export_private_key.pem" 4096

# Extract public key
openssl rsa -in "$KEYS_DIR/export_private_key.pem" -pubout -out "$KEYS_DIR/export_public_key.pem"

# Set proper permissions
chmod 600 "$KEYS_DIR/export_private_key.pem"
chmod 644 "$KEYS_DIR/export_public_key.pem"

echo "✅ RSA keypair generated successfully:"
echo "   Private: $KEYS_DIR/export_private_key.pem (permissions: 600)"
echo "   Public:  $KEYS_DIR/export_public_key.pem (permissions: 644)"
echo ""
echo "⚠️  IMPORTANT: Keep the private key secure!"
echo "   - Never commit to version control"
echo "   - Store in secure secrets management (e.g., Azure Key Vault)"
echo "   - Backup securely"
