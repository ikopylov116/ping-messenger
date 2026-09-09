"""TCP client transport for Ping Messenger."""

import socket
import threading
from typing import Callable, Optional

from .connection import EncryptedConnection


class MessengerClient:
    """Connect to a peer and establish encrypted transport."""

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 10.0,
        on_log: Optional[Callable[[str], None]] = None,
        on_connected: Optional[Callable[[EncryptedConnection], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.on_log = on_log
        self.on_connected = on_connected
        self.on_error = on_error
        self.connection: Optional[EncryptedConnection] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def connect(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        sock: Optional[socket.socket] = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            sock.settimeout(None)

            if self._stop_event.is_set():
                sock.close()
                return

            connection = EncryptedConnection(sock)
            self.connection = connection
            self._log(f"Connected to {self.host}:{self.port}")
            connection.establish_encryption(is_server=False)

            if self.on_connected:
                self.on_connected(connection)
        except Exception as exc:
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass
            if not self._stop_event.is_set() and self.on_error:
                self.on_error(exc)

    def close(self) -> None:
        self._stop_event.set()
        if self.connection:
            self.connection.close()
            self.connection = None

    def _log(self, message: str) -> None:
        if self.on_log:
            self.on_log(message)
