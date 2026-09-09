import unittest

from cryptography.fernet import Fernet

from security.encryption import EncryptionSession
from security.identity import IdentityKey


class EncryptionSessionTests(unittest.TestCase):
    def _establish_pair(self):
        server_identity = IdentityKey.generate()
        client_identity = IdentityKey.generate()
        server = EncryptionSession(server_identity)
        client = EncryptionSession(client_identity)

        server_sig = server.handshake_signature(client.public_key_bytes)
        client_sig = client.handshake_signature(server.public_key_bytes)
        server.establish(client.public_key_bytes, client.identity_public_key_bytes, client_sig)
        client.establish(server.public_key_bytes, server.identity_public_key_bytes, server_sig)
        return server, client

    def test_two_sessions_derive_compatible_ciphers(self):
        server, client = self._establish_pair()

        self.assertIsInstance(server.cipher, Fernet)
        self.assertIsInstance(client.cipher, Fernet)
        self.assertEqual(server.peer_identity_public_key, client.identity_public_key_bytes)
        self.assertEqual(client.peer_identity_public_key, server.identity_public_key_bytes)

        message = b"end-to-end test"
        self.assertEqual(client.decrypt(server.encrypt(message)), message)
        self.assertEqual(server.decrypt(client.encrypt(message)), message)

    def test_encrypt_before_establish_fails(self):
        session = EncryptionSession()
        with self.assertRaises(RuntimeError):
            session.encrypt(b"data")

    def test_invalid_peer_key_is_rejected(self):
        session = EncryptionSession()
        with self.assertRaises(ValueError):
            session.establish(b"not a public key")

    def test_missing_authentication_is_rejected(self):
        session = EncryptionSession()
        peer = EncryptionSession()
        with self.assertRaises(ValueError):
            session.establish(peer.public_key_bytes)

    def test_tampered_signature_is_rejected(self):
        server = EncryptionSession(IdentityKey.generate())
        client = EncryptionSession(IdentityKey.generate())
        signature = client.handshake_signature(server.public_key_bytes)
        tampered = signature[:-1] + bytes([signature[-1] ^ 1])
        with self.assertRaises(Exception):
            server.establish(client.public_key_bytes, client.identity_public_key_bytes, tampered)


if __name__ == "__main__":
    unittest.main()
