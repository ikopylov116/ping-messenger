"""Persistent trusted-peer identities for Ping Messenger."""

from __future__ import annotations

import base64
import json
from pathlib import Path


class TrustStore:
    """Store trusted Ed25519 peer public keys by fingerprint."""

    def __init__(self, path: str | Path = "trusted_peers.json") -> None:
        self.path = Path(path)
        self._keys: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._keys = {str(k): str(v) for k, v in data.items()}
        except (OSError, ValueError, TypeError):
            self._keys = {}

    def is_trusted(self, public_key: bytes) -> bool:
        return self._keys.get(self.fingerprint(public_key)) == base64.b64encode(public_key).decode("ascii")

    def trust(self, public_key: bytes) -> str:
        fingerprint = self.fingerprint(public_key)
        self._keys[fingerprint] = base64.b64encode(public_key).decode("ascii")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._keys, indent=2), encoding="utf-8")
        try:
            self.path.chmod(0o600)
        except OSError:
            pass
        return fingerprint

    def get_key(self, fingerprint: str) -> bytes | None:
        value = self._keys.get(fingerprint)
        if value is None:
            return None
        try:
            return base64.b64decode(value, validate=True)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def fingerprint(public_key: bytes) -> str:
        import hashlib
        digest = hashlib.sha256(public_key).hexdigest().upper()
        return ":".join(digest[i:i + 4] for i in range(0, len(digest), 4))
