#!/bin/bash
set -e

# Generate RSA keypair for export signing
# Run this once during setup

KEYS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$KEYS_DIR/export_private_key.pem" ]; then
    echo "Keys already exist. Skipping generation."
    exit 0
fi

echo "Generating RSA 2048-bit keypair..."

# Generate private key
openssl genrsa -out "$KEYS_DIR/export_private_key.pem" 2048

# Extract public key
openssl rsa -in "$KEYS_DIR/export_private_key.pem" -pubout -out "$KEYS_DIR/export_public_key.pem"

echo " RSA keypair generated:"
echo "  Private: $KEYS_DIR/export_private_key.pem"
echo "  Public:  $KEYS_DIR/export_public_key.pem"
