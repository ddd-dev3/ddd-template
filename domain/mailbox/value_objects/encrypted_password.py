"""加密密码值对象"""

from dataclasses import dataclass
from typing import Union

from cryptography.fernet import Fernet, InvalidToken

from domain.common.base_value_object import BaseValueObject
from domain.common.exceptions import InvalidValueObjectException


@dataclass(frozen=True)
class EncryptedPassword(BaseValueObject):
    """
    加密密码值对象

    使用 Fernet 对称加密算法安全存储密码。

    Attributes:
        encrypted_value: 加密后的密码字节
    """

    encrypted_value: bytes

    def validate(self) -> None:
        """验证加密密码的有效性"""
        if not self.encrypted_value:
            raise InvalidValueObjectException(
                value_object_type="EncryptedPassword",
                value=None,
                reason="Encrypted password cannot be empty"
            )

    @classmethod
    def from_plain(
        cls,
        plain_password: str,
        encryption_key: Union[str, bytes]
    ) -> "EncryptedPassword":
        """
        从明文密码创建加密密码值对象

        Args:
            plain_password: 明文密码
            encryption_key: Fernet 加密密钥（32 字节 base64 编码）

        Returns:
            EncryptedPassword 实例

        Raises:
            InvalidValueObjectException: 如果密码为空或加密失败
        """
        if not plain_password:
            raise InvalidValueObjectException(
                value_object_type="EncryptedPassword",
                value=None,
                reason="Password cannot be empty"
            )

        try:
            key = encryption_key if isinstance(encryption_key, bytes) else encryption_key.encode()
            fernet = Fernet(key)
            encrypted = fernet.encrypt(plain_password.encode("utf-8"))
            return cls(encrypted_value=encrypted)
        except Exception as e:
            raise InvalidValueObjectException(
                value_object_type="EncryptedPassword",
                value="[REDACTED]",
                reason=f"Failed to encrypt password: {e}"
            )

    def decrypt(self, encryption_key: Union[str, bytes]) -> str:
        """
        解密获取明文密码

        Args:
            encryption_key: Fernet 加密密钥

        Returns:
            明文密码

        Raises:
            InvalidValueObjectException: 如果解密失败
        """
        try:
            key = encryption_key if isinstance(encryption_key, bytes) else encryption_key.encode()
            fernet = Fernet(key)
            decrypted = fernet.decrypt(self.encrypted_value)
            return decrypted.decode("utf-8")
        except InvalidToken:
            raise InvalidValueObjectException(
                value_object_type="EncryptedPassword",
                value="[ENCRYPTED]",
                reason="Failed to decrypt password: invalid key or corrupted data"
            )
        except Exception as e:
            raise InvalidValueObjectException(
                value_object_type="EncryptedPassword",
                value="[ENCRYPTED]",
                reason=f"Failed to decrypt password: {e}"
            )

    def __repr__(self) -> str:
        """安全的字符串表示，不暴露加密值"""
        return "EncryptedPassword([ENCRYPTED])"

    def __str__(self) -> str:
        """安全的字符串表示"""
        return "[ENCRYPTED]"
