"""Cryptographic session helpers for Ping Messenger.

This module keeps cryptographic state out of the GUI/controller.  It preserves
the existing ECDH SECP384R1 + HKDF-SHA256 + Fernet design used by the app.
"""

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.fernet import Fernet


CURVE = ec.SECP384R1()
HKDF_INFO = b"ping_messenger_e2ee"
KEY_LENGTH = 32


class EncryptionSession:
    """Create and hold a Fernet cipher derived from an ECDH shared secret."""

    def __init__(self) -> None:
        self._private_key = ec.generate_private_key(CURVE)
        self.cipher: Fernet | None = None

    @property
    def public_key_bytes(self) -> bytes:
        """Return the public key in PEM SubjectPublicKeyInfo format."""
        return self._private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def establish(self, peer_public_key_bytes: bytes) -> Fernet:
        """Derive the session key from the peer's PEM public key."""
        peer_public_key = serialization.load_pem_public_key(peer_public_key_bytes)
        if not isinstance(peer_public_key, ec.EllipticCurvePublicKey):
            raise ValueError("Peer key is not an elliptic-curve public key")

        shared_secret = self._private_key.exchange(ec.ECDH(), peer_public_key)
        key = HKDF(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=None,
            info=HKDF_INFO,
        ).derive(shared_secret)
        self.cipher = Fernet(key)
        return self.cipher

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt bytes using the established session cipher."""
        if self.cipher is None:
            raise RuntimeError("Encryption session is not established")
        return self.cipher.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt bytes using the established session cipher."""
        if self.cipher is None:
            raise RuntimeError("Encryption session is not established")
        return self.cipher.decrypt(data)
