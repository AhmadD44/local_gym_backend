"""Generates an RS256 keypair for JWT signing into ./secrets/.
Run once per environment: python -m scripts.generate_jwt_keys
"""

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

OUT_DIR = Path("secrets")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    private_path = OUT_DIR / "jwt_private.pem"
    public_path = OUT_DIR / "jwt_public.pem"

    if private_path.exists() or public_path.exists():
        print("Key files already exist in ./secrets — refusing to overwrite.")
        return

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private_bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path.write_bytes(private_bytes)
    public_path.write_bytes(public_bytes)
    print(f"Wrote {private_path} and {public_path}")
    print("Keep jwt_private.pem secret and out of version control.")


if __name__ == "__main__":
    main()
