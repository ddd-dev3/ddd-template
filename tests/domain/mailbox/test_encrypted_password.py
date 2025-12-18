"""Tests for EncryptedPassword value object"""

import pytest
from cryptography.fernet import Fernet

from domain.mailbox.value_objects.encrypted_password import EncryptedPassword
from domain.common.exceptions import InvalidValueObjectException


class TestEncryptedPassword:
    """EncryptedPassword 值对象测试"""

    @pytest.fixture
    def encryption_key(self) -> bytes:
        """生成测试用加密密钥"""
        return Fernet.generate_key()

    def test_create_from_plain_password(self, encryption_key: bytes):
        """测试从明文密码创建"""
        password = EncryptedPassword.from_plain("my_secret_password", encryption_key)

        assert password.encrypted_value is not None
        assert len(password.encrypted_value) > 0
        # 加密后的值应该与原始密码不同
        assert password.encrypted_value != b"my_secret_password"

    def test_decrypt_password(self, encryption_key: bytes):
        """测试解密密码"""
        original_password = "my_secret_password"
        password = EncryptedPassword.from_plain(original_password, encryption_key)

        decrypted = password.decrypt(encryption_key)

        assert decrypted == original_password

    def test_create_with_string_key(self, encryption_key: bytes):
        """测试使用字符串密钥创建"""
        key_str = encryption_key.decode()
        password = EncryptedPassword.from_plain("my_secret_password", key_str)

        decrypted = password.decrypt(key_str)

        assert decrypted == "my_secret_password"

    def test_create_with_empty_password_raises_error(self, encryption_key: bytes):
        """测试空密码抛出异常"""
        with pytest.raises(InvalidValueObjectException) as exc_info:
            EncryptedPassword.from_plain("", encryption_key)

        assert "Password cannot be empty" in str(exc_info.value.message)

    def test_decrypt_with_wrong_key_raises_error(self, encryption_key: bytes):
        """测试使用错误密钥解密抛出异常"""
        password = EncryptedPassword.from_plain("my_secret_password", encryption_key)
        wrong_key = Fernet.generate_key()

        with pytest.raises(InvalidValueObjectException) as exc_info:
            password.decrypt(wrong_key)

        assert "Failed to decrypt password" in str(exc_info.value.message)

    def test_repr_does_not_expose_value(self, encryption_key: bytes):
        """测试 repr 不暴露加密值"""
        password = EncryptedPassword.from_plain("my_secret_password", encryption_key)

        repr_str = repr(password)

        assert "my_secret_password" not in repr_str
        assert "[ENCRYPTED]" in repr_str

    def test_str_does_not_expose_value(self, encryption_key: bytes):
        """测试 str 不暴露加密值"""
        password = EncryptedPassword.from_plain("my_secret_password", encryption_key)

        str_val = str(password)

        assert "my_secret_password" not in str_val
        assert "[ENCRYPTED]" in str_val

    def test_different_encryptions_produce_different_values(self, encryption_key: bytes):
        """测试同一密码两次加密产生不同的密文（Fernet 使用随机 IV）"""
        password1 = EncryptedPassword.from_plain("my_secret_password", encryption_key)
        password2 = EncryptedPassword.from_plain("my_secret_password", encryption_key)

        # 由于 Fernet 使用随机 IV，相同密码的两次加密结果应该不同
        assert password1.encrypted_value != password2.encrypted_value

        # 但解密后应该相同
        assert password1.decrypt(encryption_key) == password2.decrypt(encryption_key)

    def test_unicode_password(self, encryption_key: bytes):
        """测试 Unicode 密码"""
        original_password = "密码123!@#中文"
        password = EncryptedPassword.from_plain(original_password, encryption_key)

        decrypted = password.decrypt(encryption_key)

        assert decrypted == original_password
