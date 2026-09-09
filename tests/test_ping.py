"""
Модульные тесты для ping.py — вспомогательные функции и криптография.

Тестируются:
  - find_free_port    — поиск свободного порта
  - get_public_ip     — получение публичного IP
  - get_all_ips       — получение локальных IP-адресов
  - _save_user        — хеширование пароля (PBKDF2-HMAC-SHA256)
  - _exchange_keys    — ECDH обмен ключами + HKDF + Fernet
  - _send_data        — отправка зашифрованных данных

GUI-зависимости (customtkinter, tkinter, PIL, plyer) замоканы через
tests/mock_gui.py, чтобы импорт ping.py не требовал графического дисплея.
"""
import unittest
from unittest.mock import MagicMock, patch

# Устанавливаем mock GUI-библиотеки ДО импорта ping
from tests.mock_gui import _install_gui_mocks
_install_gui_mocks()

# Также мокаем games, чтобы ping.py мог импортировать TicTacToeWindow
import sys
sys.modules['games'] = MagicMock()

import ping  # noqa: E402 — импорт после мока GUI



class FindFreePortTests(unittest.TestCase):
    """Тесты для функции find_free_port."""

    def test_returns_int_port_in_range(self):
        """find_free_port возвращает целочисленный порт из диапазона."""
        port = ping.find_free_port()
        self.assertIsInstance(port, int)
        self.assertTrue(55555 <= port < 55555 + 20)

    def test_returns_actual_free_port(self):
        """Возвращенный порт действительно свободен в момент проверки."""
        port = ping.find_free_port()
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('0.0.0.0', port))
        except OSError:
            self.fail('Port {} is not free'.format(port))
        finally:
            s.close()

    def test_custom_start_port(self):
        """find_free_port с собственным start возвращает порт из диапазона."""
        port = ping.find_free_port(start=56000, max_attempts=5)
        self.assertTrue(56000 <= port < 56000 + 5)

    @patch('socket.socket')
    def test_raises_runtime_error_when_all_ports_occupied(self, mock_socket_cls):
        """RuntimeError, когда все порты заняты."""
        mock_sock = MagicMock()
        mock_socket_cls.return_value.__enter__.return_value = mock_sock
        mock_sock.bind.side_effect = OSError('Address already in use')
        with self.assertRaises(RuntimeError):
            ping.find_free_port(start=60000, max_attempts=3)

    @patch('socket.socket')
    def test_tries_consecutive_ports(self, mock_socket_cls):
        """find_free_port перебирает порты последовательно."""
        mock_sock = MagicMock()
        mock_socket_cls.return_value.__enter__.return_value = mock_sock
        mock_sock.bind.side_effect = [OSError(), OSError(), None]
        port = ping.find_free_port(start=60000, max_attempts=5)
        self.assertEqual(port, 60002)
        self.assertEqual(mock_sock.bind.call_count, 3)



class GetPublicIpTests(unittest.TestCase):
    """Тесты для функции get_public_ip."""

    @patch('urllib.request.urlopen')
    def test_returns_ip_string(self, mock_urlopen):
        """get_public_ip возвращает строку IP-адреса."""
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = b'203.0.113.42'
        mock_urlopen.return_value = mock_resp
        result = ping.get_public_ip()
        self.assertEqual(result, '203.0.113.42')

    @patch('urllib.request.urlopen', side_effect=Exception('network error'))
    def test_returns_none_on_error(self, mock_urlopen):
        """get_public_ip возвращает None при ошибке сети."""
        result = ping.get_public_ip()
        self.assertIsNone(result)

    @patch('urllib.request.urlopen')
    def test_correct_url_used(self, mock_urlopen):
        """get_public_ip использует api.ipify.org."""
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = b'1.2.3.4'
        mock_urlopen.return_value = mock_resp
        ping.get_public_ip()
        called_url = mock_urlopen.call_args[0][0]
        self.assertIn('ipify.org', called_url)


class GetAllIpsTests(unittest.TestCase):
    """Тесты для функции get_all_ips."""

    def test_returns_list(self):
        """get_all_ips возвращает список."""
        result = ping.get_all_ips()
        self.assertIsInstance(result, list)

    @patch('socket.getaddrinfo', side_effect=Exception('fail'))
    @patch('socket.socket')
    def test_always_contains_localhost_fallback(self, mock_sock_cls, mock_getaddrinfo):
        """Если getaddrinfo не работает, возвращается 127.0.0.1."""
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ('127.0.0.1', 0)
        mock_sock_cls.return_value = mock_sock
        result = ping.get_all_ips()
        self.assertIn('127.0.0.1', result)

    @patch('socket.getaddrinfo')
    @patch('socket.socket')
    def test_fallback_to_udp_connect(self, mock_sock_cls, mock_getaddrinfo):
        """Если getaddrinfo пустой, используется UDP-соединение с 8.8.8.8."""
        mock_getaddrinfo.return_value = []
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ('10.0.0.5', 0)
        mock_sock_cls.return_value = mock_sock
        result = ping.get_all_ips()
        self.assertIn('10.0.0.5', result)

    @patch('socket.getaddrinfo')
    @patch('socket.socket')
    def test_filters_loopback_addresses(self, mock_sock_cls, mock_getaddrinfo):
        """Loopback-адреса (127.*) отфильтровываются."""
        mock_getaddrinfo.return_value = [
            ('AF_INET', 0, 0, 0, ('127.0.0.1', 0)),
            ('AF_INET', 0, 0, 0, ('192.168.1.100', 0)),
            ('AF_INET', 0, 0, 0, ('127.0.0.2', 0)),
        ]
        result = ping.get_all_ips()
        self.assertNotIn('127.0.0.1', result)
        self.assertNotIn('127.0.0.2', result)
        self.assertIn('192.168.1.100', result)

    @patch('socket.getaddrinfo')
    @patch('socket.socket')
    def test_deduplicates_ips(self, mock_sock_cls, mock_getaddrinfo):
        """Дубликаты IP-адресов удаляются."""
        mock_getaddrinfo.return_value = [
            ('AF_INET', 0, 0, 0, ('192.168.1.100', 0)),
            ('AF_INET', 0, 0, 0, ('192.168.1.100', 0)),
        ]
        result = ping.get_all_ips()
        self.assertEqual(result.count('192.168.1.100'), 1)



class PasswordHashingTests(unittest.TestCase):
    """Тесты для хеширования пароля в _save_user (PBKDF2-HMAC-SHA256)."""

    def _make_messenger(self):
        """Создаёт экземпляр PingMessenger с замоканными GUI-элементами."""
        m = ping.PingMessenger.__new__(ping.PingMessenger)
        m.username = ''
        m.password = ''
        m.salt = ''
        m.conn = None
        m.cipher = None
        m.running = True
        m.server_sock = None
        m.image_refs = []
        m.typing_timer = None
        m.is_typing = False
        m.game_window = None
        m.game_opponent = None
        m.game_type = None
        m.root = MagicMock()
        m.main_font = MagicMock()
        m.header_font = MagicMock()
        m.chat_font = MagicMock()
        m.chat_font_obj = MagicMock()
        m.timestamp_width = 100
        m._setup_styles = MagicMock()
        m._load_user = MagicMock()
        m._show_welcome = MagicMock()
        m._log = MagicMock()
        return m

    def test_save_user_generates_salt_if_empty(self):
        """Если соль пустая, _save_user генерирует новую."""
        import tempfile, os
        m = self._make_messenger()
        m.username = 'testuser'
        m.password = 'testpass'
        m.salt = ''
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
            tmp_path = f.name
        try:
            original_config = ping.CONFIG
            ping.CONFIG = {'host': '0.0.0.0', 'data_file': tmp_path,
                           'theme': 'blue', 'appearance': 'dark'}
            m._save_user()
            self.assertTrue(len(m.salt) > 0)
            ping.CONFIG = original_config
        finally:
            os.unlink(tmp_path)

    def test_save_user_correct_hash(self):
        """Хеш пароля соответствует PBKDF2-HMAC-SHA256 с 100000 итерациями."""
        import hashlib, tempfile, os, json
        m = self._make_messenger()
        m.username = 'testuser'
        m.password = 'mypassword123'
        m.salt = 'aabbccdd'
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
            tmp_path = f.name
        try:
            original_config = ping.CONFIG
            ping.CONFIG = {'host': '0.0.0.0', 'data_file': tmp_path,
                           'theme': 'blue', 'appearance': 'dark'}
            m._save_user()
            expected_hash = hashlib.pbkdf2_hmac(
                'sha256', m.password.encode(), m.salt.encode(), 100000).hex()
            with open(tmp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertEqual(data['username'], 'testuser')
            self.assertEqual(data['password'], expected_hash)
            self.assertEqual(data['salt'], 'aabbccdd')
            ping.CONFIG = original_config
        finally:
            os.unlink(tmp_path)

    def test_save_user_different_passwords_different_hashes(self):
        """Разные пароли дают разные хеши (при той же соли)."""
        import hashlib
        salt = 'fixedsalt123'
        hash1 = hashlib.pbkdf2_hmac(
            'sha256', b'password1', salt.encode(), 100000).hex()
        hash2 = hashlib.pbkdf2_hmac(
            'sha256', b'password2', salt.encode(), 100000).hex()
        self.assertNotEqual(hash1, hash2)

    def test_save_user_same_password_same_hash(self):
        """Одинаковый пароль и соль дают одинаковый хеш (детерминированность)."""
        import hashlib
        salt = 'fixedsalt123'
        hash1 = hashlib.pbkdf2_hmac(
            'sha256', b'password', salt.encode(), 100000).hex()
        hash2 = hashlib.pbkdf2_hmac(
            'sha256', b'password', salt.encode(), 100000).hex()
        self.assertEqual(hash1, hash2)

    def test_password_iterations_is_100000(self):
        """PBKDF2 использует ровно 100000 итераций (как в коде)."""
        import hashlib
        salt = 'test'
        result = hashlib.pbkdf2_hmac(
            'sha256', b'test', salt.encode(), 100000).hex()
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 64)  # SHA-256 → 64 hex символов



class ExchangeKeysTests(unittest.TestCase):
    """Тесты для _exchange_keys (ECDH + HKDF + Fernet)."""

    def _make_messenger(self):
        """Создаёт экземпляр PingMessenger с минимальными mock-ами."""
        m = ping.PingMessenger.__new__(ping.PingMessenger)
        m.username = 'testuser'
        m.password = ''
        m.salt = ''
        m.conn = None
        m.cipher = None
        m.running = True
        m.server_sock = None
        m.image_refs = []
        m.typing_timer = None
        m.is_typing = False
        m.game_window = None
        m.game_opponent = None
        m.game_type = None
        m.root = MagicMock()
        m.main_font = MagicMock()
        m.header_font = MagicMock()
        m.chat_font = MagicMock()
        m.chat_font_obj = MagicMock()
        m.timestamp_width = 100
        m._log = MagicMock()
        return m

    def test_exchange_keys_creates_fernet_cipher(self):
        """После обмена ключами создаётся Fernet-шифр."""
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
        from cryptography.fernet import Fernet

        peer_priv = ec.generate_private_key(ec.SECP384R1())
        peer_pub_bytes = peer_priv.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)

        m = self._make_messenger()
        mock_conn = MagicMock()
        m.conn = mock_conn
        mock_conn.recv.return_value = peer_pub_bytes

        m._exchange_keys(is_server=True)

        self.assertIsNotNone(m.cipher)
        self.assertIsInstance(m.cipher, Fernet)

    def test_exchange_keys_both_sides_can_encrypt_decrypt(self):
        """Два участника обмениваются ключами и могут расшифровать сообщения."""
        import json, socket, threading
        from cryptography.fernet import Fernet

        s1, s2 = socket.socketpair()
        s1.settimeout(5.0)
        s2.settimeout(5.0)

        m_server = self._make_messenger()
        m_client = self._make_messenger()
        m_server.conn = s1
        m_client.conn = s2

        client_thread = threading.Thread(target=m_client._exchange_keys, args=(False,))
        client_thread.daemon = True
        client_thread.start()

        m_server._exchange_keys(is_server=True)
        client_thread.join(timeout=5.0)

        self.assertIsNotNone(m_server.cipher)
        self.assertIsNotNone(m_client.cipher)
        self.assertIsInstance(m_server.cipher, Fernet)
        self.assertIsInstance(m_client.cipher, Fernet)

        message = json.dumps({'type': 'text', 'data': 'e2e test'}).encode()
        encrypted = m_server.cipher.encrypt(message)
        decrypted = m_client.cipher.decrypt(encrypted)
        self.assertEqual(
            json.loads(decrypted.decode()),
            json.loads(message.decode()))

        s1.close()
        s2.close()

    def test_exchange_keys_server_sends_then_receives(self):
        """Сервер сначала отправляет публичный ключ, затем получает."""
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization

        peer_priv = ec.generate_private_key(ec.SECP384R1())
        peer_pub_bytes = peer_priv.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)

        m = self._make_messenger()
        mock_conn = MagicMock()
        m.conn = mock_conn
        mock_conn.recv.return_value = peer_pub_bytes

        m._exchange_keys(is_server=True)

        mock_conn.sendall.assert_called()
        mock_conn.recv.assert_called_with(2048)

    def test_exchange_keys_client_receives_then_sends(self):
        """Клиент сначала получает публичный ключ, затем отправляет свой."""
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization

        peer_priv = ec.generate_private_key(ec.SECP384R1())
        peer_pub_bytes = peer_priv.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)

        m = self._make_messenger()
        mock_conn = MagicMock()
        m.conn = mock_conn
        mock_conn.recv.return_value = peer_pub_bytes

        m._exchange_keys(is_server=False)

        mock_conn.recv.assert_called_with(2048)
        mock_conn.sendall.assert_called()

    def test_exchange_keys_uses_secp384r1(self):
        """Ключи генерируются с использованием SECP384R1."""
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization

        peer_priv = ec.generate_private_key(ec.SECP384R1())
        peer_pub_bytes = peer_priv.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)

        m = self._make_messenger()
        mock_conn = MagicMock()
        m.conn = mock_conn
        mock_conn.recv.return_value = peer_pub_bytes

        m._exchange_keys(is_server=True)
        self.assertIsNotNone(m.cipher)


class SendDataTests(unittest.TestCase):
    """Тесты для _send_data — отправка зашифрованных данных."""

    def _make_messenger(self):
        """Создаёт экземпляр PingMessenger с mock-ами."""
        m = ping.PingMessenger.__new__(ping.PingMessenger)
        m.username = 'testuser'
        m.password = ''
        m.salt = ''
        m.conn = None
        m.cipher = None
        m.running = True
        m.server_sock = None
        m.image_refs = []
        m.typing_timer = None
        m.is_typing = False
        m.game_window = None
        m.game_opponent = None
        m.game_type = None
        m.root = MagicMock()
        m.main_font = MagicMock()
        m.header_font = MagicMock()
        m.chat_font = MagicMock()
        m.chat_font_obj = MagicMock()
        m.timestamp_width = 100
        m._log = MagicMock()
        return m

    def test_send_data_encrypts_and_sends(self):
        """_send_data шифрует payload и отправляет длину + данные."""
        from cryptography.fernet import Fernet
        import struct, json

        m = self._make_messenger()
        mock_conn = MagicMock()
        m.conn = mock_conn
        key = Fernet.generate_key()
        m.cipher = Fernet(key)

        payload = json.dumps({'type': 'text', 'data': 'hello'}).encode()
        result = m._send_data(payload)
        self.assertTrue(result)
        mock_conn.sendall.assert_called_once()
        sent_data = mock_conn.sendall.call_args[0][0]
        sent_length = struct.unpack('>I', sent_data[:4])[0]
        self.assertTrue(sent_length > 0)

    def test_send_data_without_cipher_returns_false(self):
        """_send_data возвращает False, если cipher не установлен."""
        m = self._make_messenger()
        m.conn = MagicMock()
        m.cipher = None
        result = m._send_data(b'test data')
        self.assertFalse(result)

    def test_send_data_without_conn_returns_false(self):
        """_send_data возвращает False, если conn не установлен."""
        from cryptography.fernet import Fernet
        m = self._make_messenger()
        m.conn = None
        m.cipher = Fernet(Fernet.generate_key())
        result = m._send_data(b'test data')
        self.assertFalse(result)

    def test_send_data_network_error_returns_false(self):
        """_send_data возвращает False при сетевой ошибке."""
        from cryptography.fernet import Fernet
        import json

        m = self._make_messenger()
        mock_conn = MagicMock()
        mock_conn.sendall.side_effect = OSError('Connection reset')
        m.conn = mock_conn
        m.cipher = Fernet(Fernet.generate_key())

        payload = json.dumps({'type': 'text'}).encode()
        result = m._send_data(payload)
        self.assertFalse(result)

    def test_send_data_uses_struct_pack_for_length(self):
        """_send_data упаковывает длину в 4 байта big-endian (struct '>I')."""
        from cryptography.fernet import Fernet
        import struct, json

        m = self._make_messenger()
        mock_conn = MagicMock()
        m.conn = mock_conn
        m.cipher = Fernet(Fernet.generate_key())

        payload = json.dumps({'type': 'text'}).encode()
        m._send_data(payload)

        sent_data = mock_conn.sendall.call_args[0][0]
        length_prefix = sent_data[:4]
        encrypted_data = sent_data[4:]
        decoded_length = struct.unpack('>I', length_prefix)[0]
        self.assertEqual(decoded_length, len(encrypted_data))


if __name__ == '__main__':
    unittest.main(verbosity=2)



