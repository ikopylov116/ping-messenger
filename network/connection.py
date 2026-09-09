"""Encrypted TCP connection used by the messenger.

This class owns socket framing and the ECDH session.  GUI code should only
send and receive Python dictionaries through this boundary.
"""

import socket

from network.protocol import recv_frame, send_frame
from security.encryption import EncryptionSession


MAX_PUBLIC_KEY_SIZE = 4096


class EncryptedConnection:
    """A TCP connection with authenticated framing and a derived Fernet key."""

    def __init__(self, sock: socket.socket) -> None:
        self.socket = sock
        self.session = EncryptionSession()
        self.closed = False

    def establish_encryption(self, is_server: bool) -> None:
        """Exchange public keys using a framed message and derive the cipher.

        The previous implementation used raw ``recv(2048)`` for PEM keys,
        which is unsafe because TCP does not preserve message boundaries.
        Framing makes the key exchange deterministic even when packets are
        split or coalesced by the OS.
        """
        public_key = self.session.public_key_bytes
        if len(public_key) > MAX_PUBLIC_KEY_SIZE:
            raise ValueError("Public key is unexpectedly large")

        if is_server:
            send_frame(self.socket, public_key)
            peer_key = recv_frame(self.socket)
        else:
            peer_key = recv_frame(self.socket)
            send_frame(self.socket, public_key)

        if len(peer_key) > MAX_PUBLIC_KEY_SIZE:
            raise ValueError("Peer public key is unexpectedly large")

        self.session.establish(peer_key)

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
