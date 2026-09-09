import base64
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ed25519

from security.trust import TrustStore


class TrustStoreTests(unittest.TestCase):
    def test_trust_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trusted.json"
            key = ed25519.Ed25519PrivateKey.generate().public_key().public_bytes_raw()
            store = TrustStore(path)

            fingerprint = store.trust(key)
            restored = TrustStore(path)

            self.assertTrue(store.is_trusted(key))
            self.assertEqual(restored.get_key(fingerprint), key)

    def test_rejects_corrupt_fingerprint_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trusted.json"
            key = ed25519.Ed25519PrivateKey.generate().public_key().public_bytes_raw()
            path.write_text(
                json.dumps({"00:00": base64.b64encode(key).decode("ascii")}),
                encoding="utf-8",
            )

            store = TrustStore(path)
            self.assertFalse(store.is_trusted(key))

    def test_rejects_invalid_key_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TrustStore(Path(tmp) / "trusted.json")
            with self.assertRaises(ValueError):
                store.trust(b"too-short")


if __name__ == "__main__":
    unittest.main()
