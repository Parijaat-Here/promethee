# tests/test_crypto.py
import pytest

try:
    from core import crypto
    CRYPTO_AVAILABLE = crypto._CRYPTO_OK
except Exception:
    CRYPTO_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not CRYPTO_AVAILABLE,
    reason="'cryptography' non installee"
)

PASSPHRASE = "passphrase-de-test-2026"
PLAINTEXT  = "Ceci est un texte confidentiel."

class TestEncryptDecrypt:
    def test_encrypt_returns_string(self):
        result = crypto.encrypt(PLAINTEXT, PASSPHRASE)
        assert isinstance(result, str) and result != PLAINTEXT

    def test_decrypt_recovers_plaintext(self):
        assert crypto.decrypt(crypto.encrypt(PLAINTEXT, PASSPHRASE), PASSPHRASE) == PLAINTEXT

    def test_wrong_passphrase_raises(self):
        encrypted = crypto.encrypt(PLAINTEXT, PASSPHRASE)
        with pytest.raises(Exception):
            crypto.decrypt(encrypted, "mauvaise")

    def test_two_encryptions_differ(self):
        assert crypto.encrypt(PLAINTEXT, PASSPHRASE) != crypto.encrypt(PLAINTEXT, PASSPHRASE)

    def test_decrypt_plain_returns_as_is(self):
        assert crypto.decrypt(PLAINTEXT, PASSPHRASE) == PLAINTEXT

    def test_encrypt_empty_string(self):
        assert crypto.decrypt(crypto.encrypt("", PASSPHRASE), PASSPHRASE) == ""

class TestIsEncrypted:
    def test_encrypted_detected(self):
        assert crypto.is_encrypted(crypto.encrypt(PLAINTEXT, PASSPHRASE)) is True

    def test_plain_not_detected(self):
        assert crypto.is_encrypted(PLAINTEXT) is False

class TestSentinel:
    def test_create_and_verify(self):
        sentinel = crypto.create_sentinel(PASSPHRASE)
        assert crypto.verify_passphrase(PASSPHRASE, sentinel) is True

    def test_wrong_passphrase_fails(self):
        sentinel = crypto.create_sentinel(PASSPHRASE)
        assert crypto.verify_passphrase("mauvaise", sentinel) is False


class TestClearKeyCache:
    def test_clear_cache_no_error(self):
        # Doit s'exécuter sans lever d'exception
        crypto.clear_key_cache()

    def test_encrypt_after_cache_clear(self):
        # Le chiffrement doit continuer à fonctionner après purge du cache
        crypto.clear_key_cache()
        result = crypto.decrypt(crypto.encrypt(PLAINTEXT, PASSPHRASE), PASSPHRASE)
        assert result == PLAINTEXT


class TestIsEncryptedEdgeCases:
    def test_empty_string_not_encrypted(self):
        assert crypto.is_encrypted("") is False

    def test_random_string_not_encrypted(self):
        assert crypto.is_encrypted("ceci n'est pas chiffré") is False

    def test_partial_base85_not_encrypted(self):
        assert crypto.is_encrypted("abc") is False


class TestEncryptLongText:
    def test_long_text_roundtrip(self):
        long_text = "A" * 10000
        assert crypto.decrypt(crypto.encrypt(long_text, PASSPHRASE), PASSPHRASE) == long_text

    def test_unicode_roundtrip(self):
        text = "Prométhée — éàü ñ 中文 🔥"
        assert crypto.decrypt(crypto.encrypt(text, PASSPHRASE), PASSPHRASE) == text
