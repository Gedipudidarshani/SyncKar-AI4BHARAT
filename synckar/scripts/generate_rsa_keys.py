"""
Generate RSA key pair for audit ledger signing (BSA 2023 compliance).
AGENTS.md §11: every audit row is RSA-signed for tamper evidence.
Keys are stored in ./keys/ directory.

Usage:
    python scripts/generate_rsa_keys.py
"""

import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def generate_rsa_keys(key_dir: str = "./keys", key_size: int = 2048) -> None:
    """Generate RSA private/public key pair and write to PEM files."""
    os.makedirs(key_dir, exist_ok=True)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )

    # Write private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    private_path = os.path.join(key_dir, "private.pem")
    with open(private_path, "wb") as f:
        f.write(private_pem)

    # Write public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_path = os.path.join(key_dir, "public.pem")
    with open(public_path, "wb") as f:
        f.write(public_pem)

    print(f"RSA key pair generated:")
    print(f"  Private key: {private_path}")
    print(f"  Public key:  {public_path}")


if __name__ == "__main__":
    generate_rsa_keys()
