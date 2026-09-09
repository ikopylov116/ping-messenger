"""Persistent Ed25519 identity keys used to authenticate peer handshakes."""

from __future__ import annotations

import hashlib
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class IdentityKey:
    """A persistent Ed25519 identity with a stable SHA-256 fingerprint."""

    def __init__(self, private_key: ed25519.Ed25519PrivateKey) -> None:
        self._private_key = private_key

    @classmethod
    def generate(cls) -> "IdentityKey":
        return cls(ed25519.Ed25519PrivateKey.generate())

    @classmethod
    def load_or_create(cls, path: str | Path) -> "IdentityKey":
        path = Path(path)
        if path.exists():
            key = serialization.load_pem_private_key(path.read_bytes(), password=None)
            if not isinstance(key, ed25519.Ed25519PrivateKey):
                raise ValueError("Identity file does not contain an Ed25519 private key")
            return cls(key)

        identity = cls.generate()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            identity._private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return identity

    @property
    def public_key_bytes(self) -> bytes:
        return self._private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )

    @property
    def fingerprint(self) -> str:
        digest = hashlib.sha256(self.public_key_bytes).hexdigest().upper()
        return ":".join(digest[i:i + 4] for i in range(0, len(digest), 4))

    def sign(self, data: bytes) -> bytes:
        return self._private_key.sign(data)

    @staticmethod
    def verify(public_key_bytes: bytes, signature: bytes, data: bytes) -> None:
        key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        key.verify(signature, data)
