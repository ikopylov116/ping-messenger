import socket
import unittest

from network.protocol import decode_message, encode_message, pack_frame, recv_frame, send_message


class ProtocolTests(unittest.TestCase):
    def test_json_round_trip(self):
        message = {"type": "text", "sender": "Иван", "data": "Привет"}
        self.assertEqual(decode_message(encode_message(message)), message)

    def test_pack_frame_contains_big_endian_length(self):
        payload = b"hello"
        frame = pack_frame(payload)
        self.assertEqual(frame[:4], b"\x00\x00\x00\x05")
        self.assertEqual(frame[4:], payload)

    def test_send_and_receive_message(self):
        left, right = socket.socketpair()
        try:
            send_message(left, {"type": "typing", "data": True})
            self.assertEqual(
                recv_frame(right),
                encode_message({"type": "typing", "data": True}),
            )
        finally:
            left.close()
            right.close()

    def test_oversized_frame_is_rejected(self):
        from network.protocol import MAX_FRAME_SIZE
        with self.assertRaises(ValueError):
            pack_frame(b"x" * (MAX_FRAME_SIZE + 1))


if __name__ == "__main__":
    unittest.main()
