import unittest

from cryptography.fernet import Fernet

from security.encryption import EncryptionSession


class EncryptionSessionTests(unittest.TestCase):
    def test_two_sessions_derive_compatible_ciphers(self):
        server = EncryptionSession()
        client = EncryptionSession()

        server.establish(client.public_key_bytes)
        client.establish(server.public_key_bytes)

        self.assertIsInstance(server.cipher, Fernet)
        self.assertIsInstance(client.cipher, Fernet)

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


if __name__ == "__main__":
    unittest.main()
