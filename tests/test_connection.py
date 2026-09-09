import socket
import threading
import unittest

from network.connection import EncryptedConnection


class EncryptedConnectionTests(unittest.TestCase):
    def test_two_peers_establish_and_exchange_payload(self):
        left, right = socket.socketpair()
        server = EncryptedConnection(left)
        client = EncryptedConnection(right)

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

        try:
            self.assertFalse(errors)
            payload = b'{"type":"text","data":"hello"}'
            server.send_encrypted(payload)
            self.assertEqual(client.recv_encrypted(), payload)

            response = b'{"type":"text","data":"world"}'
            client.send_encrypted(response)
            self.assertEqual(server.recv_encrypted(), response)
        finally:
            server.close()
            client.close()

    def test_close_is_idempotent(self):
        sock1, sock2 = socket.socketpair()
        connection = EncryptedConnection(sock1)
        connection.close()
        connection.close()
        sock2.close()


if __name__ == "__main__":
    unittest.main()
