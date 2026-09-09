"""Transport framing and JSON protocol helpers for Ping Messenger.

The wire format is deliberately small and independent from the GUI:
    [4-byte big-endian payload length][payload bytes]

Encryption is handled by ``security.encryption``; this module only deals with
framing and JSON serialization.
"""

import json
import socket
import struct
from typing import Any


HEADER_SIZE = 4
MAX_FRAME_SIZE = 8 * 1024 * 1024


def encode_message(message: dict[str, Any]) -> bytes:
    """Serialize a protocol message to UTF-8 JSON bytes."""
    return json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def decode_message(payload: bytes) -> dict[str, Any]:
    """Deserialize a UTF-8 JSON protocol message."""
    message = json.loads(payload.decode("utf-8"))
    if not isinstance(message, dict):
        raise ValueError("Protocol message must be a JSON object")
    return message


def pack_frame(payload: bytes) -> bytes:
    """Add the network length prefix to an already serialized payload."""
    if len(payload) > MAX_FRAME_SIZE:
        raise ValueError(f"Frame is too large: {len(payload)} bytes")
    return struct.pack(">I", len(payload)) + payload


def send_frame(sock: socket.socket, payload: bytes) -> None:
    """Send one complete framed payload."""
    sock.sendall(pack_frame(payload))


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    """Receive exactly ``size`` bytes or raise ConnectionError on EOF."""
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(min(4096, size - len(chunks)))
        if not chunk:
            raise ConnectionError("Connection closed while receiving data")
        chunks.extend(chunk)
    return bytes(chunks)


def recv_frame(sock: socket.socket) -> bytes:
    """Receive one complete frame with a bounded payload size."""
    header = _recv_exact(sock, HEADER_SIZE)
    (length,) = struct.unpack(">I", header)
    if length > MAX_FRAME_SIZE:
        raise ValueError(f"Frame is too large: {length} bytes")
    return _recv_exact(sock, length)


def send_message(sock: socket.socket, message: dict[str, Any]) -> None:
    """Serialize and send a protocol message."""
    send_frame(sock, encode_message(message))


def recv_message(sock: socket.socket) -> dict[str, Any]:
    """Receive and deserialize one protocol message."""
    return decode_message(recv_frame(sock))
