import base64
import json
import socket
import threading
import unittest

from network.connection import (
    ECDH_PUBLIC_KEY_MAX_SIZE,
    ECDH_PUBLIC_KEY_MIN_SIZE,
    ED25519_PUBLIC_KEY_SIZE,
    ED25519_SIGNATURE_SIZE,
    EncryptedConnection,
)
from security.identity import IdentityKey


class EncryptedConnectionTests(unittest.TestCase):
    def _make_pair(self, expected_server_key=None):
        left, right = socket.socketpair()
        server_identity = IdentityKey.generate()
        client_identity = IdentityKey.generate()
        server = EncryptedConnection(left, identity=server_identity)
        client = EncryptedConnection(
            right,
            identity=client_identity,
            expected_peer_identity=expected_server_key,
        )
        return server, client, server_identity, client_identity

    def _establish(self, server, client):
        errors = []

        def establish_client():
            try:
                client.establish_encryption(is_server=False)
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=establish_client)
        thread.start()
        server.establish_encryption(is_server=True)
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive(), "client handshake did not finish")
        return errors

    def test_two_peers_establish_and_exchange_payload(self):
        server, client, server_identity, _ = self._make_pair()
        try:
            errors = self._establish(server, client)
            self.assertFalse(errors)
            self.assertEqual(
                server.session.peer_identity_public_key,
                client.session.identity_public_key_bytes,
            )
            self.assertEqual(
                client.session.peer_identity_public_key,
                server_identity.public_key_bytes,
            )

            payload = b'{"type":"text","data":"hello"}'
            server.send_encrypted(payload)
            self.assertEqual(client.recv_encrypted(), payload)

            response = b'{"type":"text","data":"world"}'
            client.send_encrypted(response)
            self.assertEqual(server.recv_encrypted(), response)
        finally:
            server.close()
            client.close()

    def test_expected_peer_identity_is_enforced_after_symmetric_handshake(self):
        wrong_key = IdentityKey.generate().public_key_bytes
        server, client, _, _ = self._make_pair(expected_server_key=wrong_key)
        try:
            errors = self._establish(server, client)
            self.assertTrue(errors)
            self.assertTrue(any("trusted key" in str(error) for error in errors))
        finally:
            server.close()
            client.close()

    def test_expected_peer_identity_accepts_trusted_key(self):
        server, client, server_identity, _ = self._make_pair()
        client.expected_peer_identity = server_identity.public_key_bytes
        try:
            errors = self._establish(server, client)
            self.assertFalse(errors)
        finally:
            server.close()
            client.close()

    def test_bundle_rejects_invalid_key_sizes(self):
        identity = base64.b64encode(b"x" * ED25519_PUBLIC_KEY_SIZE).decode("ascii")
        for size in (ECDH_PUBLIC_KEY_MIN_SIZE - 1, ECDH_PUBLIC_KEY_MAX_SIZE + 1):
            bundle = json.dumps(
                {
                    "public_key": base64.b64encode(b"x" * size).decode("ascii"),
                    "identity_key": identity,
                }
            ).encode("ascii")
            with self.subTest(size=size), self.assertRaises(ValueError):
                EncryptedConnection._parse_bundle(bundle)

    def test_signature_parser_requires_exact_ed25519_size(self):
        for size in (ED25519_SIGNATURE_SIZE - 1, ED25519_SIGNATURE_SIZE + 1):
            data = json.dumps(
                {"signature": base64.b64encode(b"x" * size).decode("ascii")}
            ).encode("ascii")
            with self.subTest(size=size), self.assertRaises(ValueError):
                EncryptedConnection._parse_signature(data)

    def test_close_is_idempotent(self):
        sock1, sock2 = socket.socketpair()
        connection = EncryptedConnection(sock1, identity=IdentityKey.generate())
        connection.close()
        connection.close()
        sock2.close()


if __name__ == "__main__":
    unittest.main()
