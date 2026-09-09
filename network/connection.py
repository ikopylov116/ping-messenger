"""Encrypted TCP connection with authenticated ECDH key exchange."""

from __future__ import annotations

import base64
import json
import socket

from network.protocol import recv_frame, send_frame
from security.encryption import EncryptionSession
from security.identity import IdentityKey

MAX_HANDSHAKE_SIZE = 16 * 1024
HANDSHAKE_TIMEOUT = 15.0
ED25519_PUBLIC_KEY_SIZE = 32
ED25519_SIGNATURE_SIZE = 64
ECDH_PUBLIC_KEY_MIN_SIZE = 65
ECDH_PUBLIC_KEY_MAX_SIZE = 128
MAX_PAYLOAD_SIZE = 4 * 1024 * 1024
SEQUENCE_SIZE = 8


class EncryptedConnection:
    """Framed TCP connection with authenticated ECDH and replay protection."""

    def __init__(self, sock: socket.socket, identity: IdentityKey | None = None, expected_peer_identity: bytes | None = None) -> None:
        self.socket = sock
        self.session = EncryptionSession(identity)
        self.expected_peer_identity = expected_peer_identity
        self.closed = False
        self._send_sequence = 0
        self._receive_sequence = 0

    @staticmethod
    def _bundle(public_key: bytes, identity_key: bytes) -> bytes:
        return json.dumps({"public_key": base64.b64encode(public_key).decode("ascii"), "identity_key": base64.b64encode(identity_key).decode("ascii")}, separators=(",", ":")).encode("ascii")

    @staticmethod
    def _parse_bundle(data: bytes) -> tuple[bytes, bytes]:
        if len(data) > MAX_HANDSHAKE_SIZE:
            raise ValueError("Handshake message is too large")
        try:
            obj = json.loads(data.decode("ascii"))
            if not isinstance(obj, dict):
                raise ValueError("Handshake bundle must be an object")
            public_key = base64.b64decode(obj["public_key"], validate=True)
            identity_key = base64.b64decode(obj["identity_key"], validate=True)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid handshake key bundle") from exc
        if not ECDH_PUBLIC_KEY_MIN_SIZE <= len(public_key) <= ECDH_PUBLIC_KEY_MAX_SIZE:
            raise ValueError("Invalid peer ECDH public key size")
        if len(identity_key) != ED25519_PUBLIC_KEY_SIZE:
            raise ValueError("Invalid peer identity key")
        return public_key, identity_key

    @staticmethod
    def _parse_signature(data: bytes) -> bytes:
        if len(data) > MAX_HANDSHAKE_SIZE:
            raise ValueError("Handshake signature message is too large")
        try:
            obj = json.loads(data.decode("ascii"))
            if not isinstance(obj, dict):
                raise ValueError("Handshake signature must be an object")
            signature = base64.b64decode(obj["signature"], validate=True)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid handshake signature") from exc
        if len(signature) != ED25519_SIGNATURE_SIZE:
            raise ValueError("Invalid peer handshake signature")
        return signature

    def _check_expected_identity(self, peer_identity: bytes) -> None:
        if self.expected_peer_identity is not None and peer_identity != self.expected_peer_identity:
            raise ValueError("Peer identity does not match the trusted key")

    def establish_encryption(self, is_server: bool) -> None:
        """Perform a mutually authenticated ephemeral ECDH exchange."""
        del is_server
        previous_timeout = self.socket.gettimeout()
        self.socket.settimeout(HANDSHAKE_TIMEOUT)
        try:
            public_key = self.session.public_key_bytes
            identity_key = self.session.identity_public_key_bytes
            if not ECDH_PUBLIC_KEY_MIN_SIZE <= len(public_key) <= ECDH_PUBLIC_KEY_MAX_SIZE:
                raise ValueError("Invalid local ECDH public key size")
            if len(identity_key) != ED25519_PUBLIC_KEY_SIZE:
                raise ValueError("Invalid local identity key")
            send_frame(self.socket, self._bundle(public_key, identity_key))
            peer_public_key, peer_identity_key = self._parse_bundle(recv_frame(self.socket))
            signature = self.session.handshake_signature(peer_public_key)
            if len(signature) != ED25519_SIGNATURE_SIZE:
                raise ValueError("Invalid local handshake signature")
            send_frame(self.socket, json.dumps({"signature": base64.b64encode(signature).decode("ascii")}, separators=(",", ":")).encode("ascii"))
            peer_signature = self._parse_signature(recv_frame(self.socket))
            self.session.establish(peer_public_key, peer_identity_key, peer_signature)
            self._check_expected_identity(peer_identity_key)
        finally:
            self.socket.settimeout(previous_timeout)

    def send_encrypted(self, payload: bytes) -> None:
        """Encrypt and send one bounded, monotonically sequenced payload."""
        if not isinstance(payload, bytes):
            raise TypeError("Encrypted payload must be bytes")
        if len(payload) > MAX_PAYLOAD_SIZE:
            raise ValueError(f"Payload is too large: {len(payload)} bytes")
        if self._send_sequence == 0xFFFFFFFFFFFFFFFF:
            raise OverflowError("Message sequence exhausted")
        sequence = self._send_sequence
        encrypted = self.session.encrypt(payload)
        send_frame(self.socket, sequence.to_bytes(SEQUENCE_SIZE, "big") + encrypted)
        self._send_sequence += 1

    def recv_encrypted(self) -> bytes:
        """Receive one payload and reject duplicates or reordered messages."""
        frame = recv_frame(self.socket)
        if len(frame) <= SEQUENCE_SIZE:
            raise ValueError("Invalid encrypted message envelope")
        sequence = int.from_bytes(frame[:SEQUENCE_SIZE], "big")
        if sequence != self._receive_sequence:
            raise ValueError(f"Unexpected message sequence: expected {self._receive_sequence}, got {sequence}")
        payload = self.session.decrypt(frame[SEQUENCE_SIZE:])
        if len(payload) > MAX_PAYLOAD_SIZE:
            raise ValueError("Decrypted payload is too large")
        self._receive_sequence += 1
        return payload

    def close(self) -> None:
        """Close the socket once."""
        if self.closed:
            return
        self.closed = True
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self.socket.close()
