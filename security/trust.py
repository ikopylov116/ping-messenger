"""Persistent trusted-peer identities for Ping Messenger."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from pathlib import Path


PUBLIC_KEY_SIZE = 32


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
            if not isinstance(data, dict):
                raise ValueError("Trust store must contain a JSON object")
            loaded: dict[str, str] = {}
            for fingerprint, encoded_key in data.items():
                if not isinstance(fingerprint, str) or not isinstance(encoded_key, str):
                    raise ValueError("Invalid trust store entry")
                key = base64.b64decode(encoded_key, validate=True)
                if len(key) != PUBLIC_KEY_SIZE:
                    raise ValueError("Invalid trusted public key length")
                if self.fingerprint(key) != fingerprint:
                    raise ValueError("Trust store fingerprint does not match key")
                loaded[fingerprint] = encoded_key
            self._keys = loaded
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # Never turn a corrupt file into implicit trust. The in-memory store
            # remains empty and the application will require first-contact approval.
            self._keys = {}

    def is_trusted(self, public_key: bytes) -> bool:
        self._validate_key(public_key)
        return self._keys.get(self.fingerprint(public_key)) == base64.b64encode(public_key).decode("ascii")

    def trust(self, public_key: bytes) -> str:
        self._validate_key(public_key)
        fingerprint = self.fingerprint(public_key)
        self._keys[fingerprint] = base64.b64encode(public_key).decode("ascii")
        self._save_atomic()
        return fingerprint

    def get_key(self, fingerprint: str) -> bytes | None:
        value = self._keys.get(fingerprint)
        if value is None:
            return None
        try:
            key = base64.b64decode(value, validate=True)
        except (ValueError, TypeError):
            return None
        if len(key) != PUBLIC_KEY_SIZE or self.fingerprint(key) != fingerprint:
            return None
        return key

    def _save_atomic(self) -> None:
        """Write the trust database atomically so a crash cannot truncate it."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(self._keys, indent=2, sort_keys=True))
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temp_name, 0o600)
            except OSError:
                pass
            os.replace(temp_name, self.path)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    @staticmethod
    def _validate_key(public_key: bytes) -> None:
        if not isinstance(public_key, bytes) or len(public_key) != PUBLIC_KEY_SIZE:
            raise ValueError("Ed25519 public key must be exactly 32 bytes")

    @staticmethod
    def fingerprint(public_key: bytes) -> str:
        TrustStore._validate_key(public_key)
        digest = hashlib.sha256(public_key).hexdigest().upper()
        return ":".join(digest[i:i + 4] for i in range(0, len(digest), 4))
