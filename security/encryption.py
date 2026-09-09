"""Cryptographic session helpers for Ping Messenger.

ECDH provides forward secrecy for the session key. Ed25519 signatures bind
that ephemeral ECDH key to a persistent peer identity and prevent MITM when
the peer identity is verified/pinned by the application.
"""

from __future__ import annotations

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .identity import IdentityKey


CURVE = ec.SECP384R1()
HKDF_INFO = b"ping_messenger_e2ee_v2"
KEY_LENGTH = 32
AUTH_DOMAIN = b"ping-messenger-handshake-v2"


class EncryptionSession:
    """ECDH session authenticated by a persistent Ed25519 identity."""

    def __init__(self, identity: IdentityKey | None = None) -> None:
        self._private_key = ec.generate_private_key(CURVE)
        self.identity = identity or IdentityKey.generate()
        self.cipher: Fernet | None = None
        self.peer_identity_public_key: bytes | None = None

    @property
    def public_key_bytes(self) -> bytes:
        return self._private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    @property
    def identity_public_key_bytes(self) -> bytes:
        return self.identity.public_key_bytes

    def handshake_signature(self, peer_public_key_bytes: bytes) -> bytes:
        """Sign both ephemeral public keys so neither side can silently swap one."""
        own = self.public_key_bytes
        material = AUTH_DOMAIN + len(own).to_bytes(4, "big") + own
        material += len(peer_public_key_bytes).to_bytes(4, "big") + peer_public_key_bytes
        return self.identity.sign(material)

    def establish(
        self,
        peer_public_key_bytes: bytes,
        peer_identity_public_key: bytes | None = None,
        peer_signature: bytes | None = None,
    ) -> Fernet:
        """Derive the session key and verify the peer's identity signature."""
        peer_public_key = serialization.load_pem_public_key(peer_public_key_bytes)
        if not isinstance(peer_public_key, ec.EllipticCurvePublicKey):
            raise ValueError("Peer key is not an elliptic-curve public key")
        if peer_public_key.curve.name != CURVE.name:
            raise ValueError("Peer key uses an unexpected elliptic curve")

        if peer_identity_public_key is None or peer_signature is None:
            raise ValueError("Authenticated handshake data is required")
        if len(peer_identity_public_key) != 32:
            raise ValueError("Invalid Ed25519 identity key length")

        own = self.public_key_bytes
        material = AUTH_DOMAIN + len(peer_public_key_bytes).to_bytes(4, "big") + peer_public_key_bytes
        material += len(own).to_bytes(4, "big") + own
        IdentityKey.verify(peer_identity_public_key, peer_signature, material)
        self.peer_identity_public_key = peer_identity_public_key

        shared_secret = self._private_key.exchange(ec.ECDH(), peer_public_key)
        # Bind both ephemeral keys and both identity keys into the KDF context.
        context = HKDF_INFO + self._canonical_transcript(
            own, peer_public_key_bytes, self.identity_public_key_bytes, peer_identity_public_key
        )
        key = HKDF(
            algorithm=hashes.SHA256(), length=KEY_LENGTH, salt=None, info=context
        ).derive(shared_secret)
        self.cipher = Fernet(key)
        return self.cipher

    @staticmethod
    def _canonical_transcript(a: bytes, b: bytes, ia: bytes, ib: bytes) -> bytes:
        pairs = sorted(((a, ia), (b, ib)), key=lambda item: item[0])
        return b"".join(len(value).to_bytes(4, "big") + value for pair in pairs for value in pair)

    def encrypt(self, data: bytes) -> bytes:
        if self.cipher is None:
            raise RuntimeError("Encryption session is not established")
        return self.cipher.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        if self.cipher is None:
            raise RuntimeError("Encryption session is not established")
        return self.cipher.decrypt(data)
