"""TCP server transport for Ping Messenger.

This module owns socket lifecycle and encrypted transport setup. The GUI layer
supplies callbacks instead of knowing about socket details.
"""

import socket
import threading
from typing import Callable, Optional

from .connection import EncryptedConnection


class MessengerServer:
    """Accept one client and expose an :class:`EncryptedConnection`."""

    def __init__(
        self,
        host: str,
        port: int,
        on_log: Optional[Callable[[str], None]] = None,
        on_connected: Optional[Callable[[EncryptedConnection, tuple], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        self.host = host
        self.port = port
        self.on_log = on_log
        self.on_connected = on_connected
        self.on_error = on_error
        self.server_socket: Optional[socket.socket] = None
        self.connection: Optional[EncryptedConnection] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(1)
            self.server_socket = server
            self._log(f"Server listening on {self.host}:{self.port}")

            client, address = server.accept()
            if self._stop_event.is_set():
                client.close()
                return

            connection = EncryptedConnection(client)
            self.connection = connection
            self._log(f"Client connected: {address[0]}:{address[1]}")
            connection.establish_encryption(is_server=True)

            if self.on_connected:
                self.on_connected(connection, address)
        except Exception as exc:
            if not self._stop_event.is_set() and self.on_error:
                self.on_error(exc)
        finally:
            if self.server_socket:
                try:
                    self.server_socket.close()
                except OSError:
                    pass
                self.server_socket = None

    def stop(self) -> None:
        self._stop_event.set()
        if self.connection:
            self.connection.close()
            self.connection = None
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

    def _log(self, message: str) -> None:
        if self.on_log:
            self.on_log(message)
