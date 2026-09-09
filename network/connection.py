"""Encrypted TCP connection with authenticated ECDH key exchange."""

from __future__ import annotations

import base64
import json
import os
import socket
from pathlib import Path

from network.protocol import recv_frame, send_frame
from security.encryption import EncryptionSession
from security.identity import IdentityKey

MAX_HANDSHAKE_SIZE = 16 * 1024
MAX_PUBLIC_KEY_SIZE = 4096


class EncryptedConnection:
    """Framed TCP connection with authenticated ECDH and persistent identities."""

    def __init__(self, sock: socket.socket, identity: IdentityKey | None = None,
                 expected_peer_identity: bytes | None = None) -> None:
        self.socket = sock
        if identity is None:
            identity_path = os.environ.get("PING_IDENTITY_FILE")
            identity = IdentityKey.load_or_create(
                identity_path or Path.home() / ".ping_messenger_identity.pem"
            )
        self.session = EncryptionSession(identity)
        self.expected_peer_identity = expected_peer_identity
        self.peer_key_path = Path(
            os.environ.get("PING_TRUSTED_PEER_FILE")
            or Path.home() / ".ping_messenger_peer.key"
        )
        self.closed = False

    @staticmethod
    def _bundle(public_key: bytes, identity_key: bytes) -> bytes:
        return json.dumps({
            "public_key": base64.b64encode(public_key).decode("ascii"),
            "identity_key": base64.b64encode(identity_key).decode("ascii"),
        }, separators=(",", ":")).encode("ascii")

    @staticmethod
    def _parse_bundle(data: bytes) -> tuple[bytes, bytes]:
        if len(data) > MAX_HANDSHAKE_SIZE:
            raise ValueError("Handshake message is too large")
        try:
            obj = json.loads(data.decode("ascii"))
            public_key = base64.b64decode(obj["public_key"], validate=True)
            identity_key = base64.b64decode(obj["identity_key"], validate=True)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid handshake key bundle") from exc
        if not 1 <= len(public_key) <= MAX_PUBLIC_KEY_SIZE:
            raise ValueError("Invalid peer public key size")
        if len(identity_key) != 32:
            raise ValueError("Invalid peer identity key")
        return public_key, identity_key

    def _check_peer_identity(self, peer_identity: bytes) -> None:
        if self.expected_peer_identity is not None:
            if peer_identity != self.expected_peer_identity:
                raise ValueError("Peer identity does not match the trusted key")
            return
        if self.peer_key_path.exists():
            stored = self.peer_key_path.read_bytes()
            if len(stored) != 32 or stored != peer_identity:
                raise ValueError("Peer identity changed: possible MITM attack")
            return
        self.peer_key_path.parent.mkdir(parents=True, exist_ok=True)
        self.peer_key_path.write_bytes(peer_identity)
        try:
            self.peer_key_path.chmod(0o600)
        except OSError:
            pass

    def establish_encryption(self, is_server: bool) -> None:
        public_key = self.session.public_key_bytes
        identity_key = self.session.identity_public_key_bytes
        if len(public_key) > MAX_PUBLIC_KEY_SIZE:
            raise ValueError("Public key is unexpectedly large")

        send_frame(self.socket, self._bundle(public_key, identity_key))
        peer_public_key, peer_identity_key = self._parse_bundle(recv_frame(self.socket))
        self._check_peer_identity(peer_identity_key)

        signature = self.session.handshake_signature(peer_public_key)
        if len(signature) != 64:
            raise ValueError("Invalid local handshake signature")
        send_frame(self.socket, json.dumps({
            "signature": base64.b64encode(signature).decode("ascii")
        }, separators=(",", ":")).encode("ascii"))

        signature_data = recv_frame(self.socket)
        if len(signature_data) > MAX_HANDSHAKE_SIZE:
            raise ValueError("Handshake signature message is too large")
        try:
            peer_signature = base64.b64decode(
                json.loads(signature_data.decode("ascii"))["signature"], validate=True
            )
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid handshake signature") from exc
        if len(peer_signature) != 64:
            raise ValueError("Invalid peer handshake signature")
        self.session.establish(peer_public_key, peer_identity_key, peer_signature)

    def send_encrypted(self, payload: bytes) -> None:
        send_frame(self.socket, self.session.encrypt(payload))

    def recv_encrypted(self) -> bytes:
        return self.session.decrypt(recv_frame(self.socket))

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self.socket.close()
