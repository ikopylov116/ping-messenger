"""Encrypted TCP connection with authenticated ECDH key exchange."""

from __future__ import annotations

import base64
import json
import socket

from network.protocol import recv_frame, send_frame
from security.encryption import EncryptionSession
from security.identity import IdentityKey


MAX_HANDSHAKE_SIZE = 16 * 1024
MAX_PUBLIC_KEY_SIZE = 4096


class EncryptedConnection:
    """TCP connection using framed, authenticated ECDH encryption."""

    def __init__(self, sock: socket.socket, identity: IdentityKey | None = None) -> None:
        self.socket = sock
        self.session = EncryptionSession(identity)
        self.closed = False

    @staticmethod
    def _bundle(public_key: bytes, identity_key: bytes) -> bytes:
        return json.dumps(
            {
                "public_key": base64.b64encode(public_key).decode("ascii"),
                "identity_key": base64.b64encode(identity_key).decode("ascii"),
            },
            separators=(",", ":"),
        ).encode("ascii")

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
        if len(public_key) > MAX_PUBLIC_KEY_SIZE:
            raise ValueError("Peer public key is unexpectedly large")
        if len(identity_key) != 32:
            raise ValueError("Invalid peer identity key")
        return public_key, identity_key

    def establish_encryption(self, is_server: bool) -> None:
        """Perform a framed, mutually authenticated ephemeral ECDH exchange."""
        public_key = self.session.public_key_bytes
        identity_key = self.session.identity_public_key_bytes
        if len(public_key) > MAX_PUBLIC_KEY_SIZE:
            raise ValueError("Public key is unexpectedly large")

        # Both sides exchange ephemeral ECDH and persistent identity keys.
        send_frame(self.socket, self._bundle(public_key, identity_key))
        peer_bundle = recv_frame(self.socket)
        peer_public_key, peer_identity_key = self._parse_bundle(peer_bundle)

        # Sign the exact ephemeral-key transcript before deriving the session key.
        signature = self.session.handshake_signature(peer_public_key)
        signature_payload = json.dumps(
            {"signature": base64.b64encode(signature).decode("ascii")},
            separators=(",", ":"),
        ).encode("ascii")
        send_frame(self.socket, signature_payload)
        signature_data = recv_frame(self.socket)
        if len(signature_data) > MAX_HANDSHAKE_SIZE:
            raise ValueError("Handshake signature message is too large")
        try:
            peer_signature = base64.b64decode(
                json.loads(signature_data.decode("ascii"))["signature"], validate=True
            )
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid handshake signature") from exc

        self.session.establish(peer_public_key, peer_identity_key, peer_signature)

    def send_encrypted(self, payload: bytes) -> None:
        """Encrypt and send one payload."""
        send_frame(self.socket, self.session.encrypt(payload))

    def recv_encrypted(self) -> bytes:
        """Receive and decrypt one payload."""
        return self.session.decrypt(recv_frame(self.socket))

    def close(self) -> None:
        """Close the underlying socket once."""
        if self.closed:
            return
        self.closed = True
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self.socket.close()
