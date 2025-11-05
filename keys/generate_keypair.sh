#!/bin/bash

# Generate RSA keypair for export signing

mkdir -p keys

openssl genrsa -out keys/export_private_key.pem 2048
openssl rsa -in keys/export_private_key.pem -pubout -out keys/export_public_key.pem

chmod 600 keys/export_private_key.pem
chmod 644 keys/export_public_key.pem

echo "✅ RSA keypair generated:"
echo "  Private: keys/export_private_key.pem"
echo "  Public:  keys/export_public_key.pem"
