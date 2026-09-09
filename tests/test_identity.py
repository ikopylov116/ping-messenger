import tempfile
import unittest
from pathlib import Path

from security.identity import IdentityKey
from security.trust import TrustStore


class IdentityTests(unittest.TestCase):
    def test_fingerprint_is_stable_and_formatted(self):
        identity = IdentityKey.generate()
        fingerprint = identity.fingerprint
        self.assertEqual(len(fingerprint.split(":")), 16)
        self.assertTrue(all(len(part) == 4 for part in fingerprint.split(":")))
        self.assertEqual(fingerprint, IdentityKey(identity._private_key).fingerprint)

    def test_load_or_create_is_persistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "identity.pem"
            first = IdentityKey.load_or_create(path)
            second = IdentityKey.load_or_create(path)
            self.assertEqual(first.public_key_bytes, second.public_key_bytes)
            self.assertEqual(first.fingerprint, second.fingerprint)


class TrustStoreTests(unittest.TestCase):
    def test_trust_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TrustStore(Path(tmp) / "trusted.json")
            key = IdentityKey.generate().public_key_bytes
            fingerprint = store.trust(key)
            self.assertEqual(store.get_key(fingerprint), key)
            self.assertTrue(store.is_trusted(key))

            reloaded = TrustStore(Path(tmp) / "trusted.json")
            self.assertEqual(reloaded.get_key(fingerprint), key)
            self.assertTrue(reloaded.is_trusted(key))

    def test_different_key_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TrustStore(Path(tmp) / "trusted.json")
            trusted = IdentityKey.generate().public_key_bytes
            other = IdentityKey.generate().public_key_bytes
            store.trust(trusted)
            self.assertFalse(store.is_trusted(other))


if __name__ == "__main__":
    unittest.main()
