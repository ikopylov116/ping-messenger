"""Tests for Ping Messenger helpers that do not require a real GUI."""

import hashlib
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from tests.mock_gui import _install_gui_mocks

_install_gui_mocks()

import sys
sys.modules['games'] = MagicMock()

import ping  # noqa: E402


class FindFreePortTests(unittest.TestCase):
    def test_returns_port_in_range(self):
        port = ping.find_free_port()
        self.assertIsInstance(port, int)
        self.assertTrue(55555 <= port < 55575)

    @patch('socket.socket')
    def test_raises_when_all_ports_are_busy(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_socket_cls.return_value.__enter__.return_value = mock_sock
        mock_sock.bind.side_effect = OSError('Address already in use')
        with self.assertRaises(RuntimeError):
            ping.find_free_port(start=60000, max_attempts=3)


class PublicIpTests(unittest.TestCase):
    @patch('urllib.request.urlopen')
    def test_returns_ip(self, mock_urlopen):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'203.0.113.42'
        mock_urlopen.return_value = response
        self.assertEqual(ping.get_public_ip(), '203.0.113.42')

    @patch('urllib.request.urlopen', side_effect=OSError('network error'))
    def test_returns_none_on_error(self, _):
        self.assertIsNone(ping.get_public_ip())


class AllIpsTests(unittest.TestCase):
    @patch('socket.getaddrinfo')
    def test_filters_loopback_and_deduplicates(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            ('AF_INET', 0, 0, 0, ('127.0.0.1', 0)),
            ('AF_INET', 0, 0, 0, ('192.168.1.100', 0)),
            ('AF_INET', 0, 0, 0, ('192.168.1.100', 0)),
        ]
        result = ping.get_all_ips()
        self.assertEqual(result, ['192.168.1.100'])

    @patch('socket.getaddrinfo', return_value=[])
    @patch('socket.socket')
    def test_uses_udp_fallback(self, mock_socket_cls, _):
        sock = MagicMock()
        sock.getsockname.return_value = ('10.0.0.5', 0)
        mock_socket_cls.return_value = sock
        self.assertEqual(ping.get_all_ips(), ['10.0.0.5'])
        sock.connect.assert_called_once_with(('8.8.8.8', 80))


class PasswordHashingTests(unittest.TestCase):
    def _make_messenger(self):
        messenger = ping.PingMessenger.__new__(ping.PingMessenger)
        messenger.username = 'testuser'
        messenger.password = 'testpass'
        messenger.salt = 'aabbccdd'
        return messenger

    def test_save_user_writes_pbkdf2_hash(self):
        messenger = self._make_messenger()
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        try:
            original = ping.CONFIG
            ping.CONFIG = {'data_file': path}
            messenger._save_user()
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            expected = hashlib.pbkdf2_hmac(
                'sha256', b'testpass', b'aabbccdd', 100000
            ).hex()
            self.assertEqual(data['password'], expected)
            self.assertEqual(data['username'], 'testuser')
            self.assertEqual(data['salt'], 'aabbccdd')
        finally:
            ping.CONFIG = original
            os.unlink(path)

    def test_save_user_generates_salt(self):
        messenger = self._make_messenger()
        messenger.salt = ''
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        try:
            original = ping.CONFIG
            ping.CONFIG = {'data_file': path}
            messenger._save_user()
            self.assertTrue(messenger.salt)
            self.assertEqual(len(messenger.salt), 32)
        finally:
            ping.CONFIG = original
            os.unlink(path)


class SendDataTests(unittest.TestCase):
    def test_send_data_uses_secure_connection(self):
        messenger = ping.PingMessenger.__new__(ping.PingMessenger)
        messenger.secure_connection = MagicMock()
        messenger._log = MagicMock()
        payload = b'{"type":"text","data":"hello"}'
        self.assertTrue(messenger._send_data(payload))
        messenger.secure_connection.send_encrypted.assert_called_once_with(payload)

    def test_send_data_without_secure_connection_returns_false(self):
        messenger = ping.PingMessenger.__new__(ping.PingMessenger)
        messenger.secure_connection = None
        self.assertFalse(messenger._send_data(b'test'))

    def test_send_data_reports_network_error(self):
        messenger = ping.PingMessenger.__new__(ping.PingMessenger)
        messenger.secure_connection = MagicMock()
        messenger.secure_connection.send_encrypted.side_effect = OSError('connection reset')
        messenger._log = MagicMock()
        self.assertFalse(messenger._send_data(b'test'))
        messenger._log.assert_called_once()


if __name__ == '__main__':
    unittest.main()
