"""IMAP 配置值对象"""

from dataclasses import dataclass

from domain.common.base_value_object import BaseValueObject
from domain.common.exceptions import InvalidValueObjectException


@dataclass(frozen=True)
class ImapConfig(BaseValueObject):
    """
    IMAP 服务器配置值对象

    封装 IMAP 服务器连接所需的配置信息。

    Attributes:
        server: IMAP 服务器地址
        port: IMAP 服务器端口，默认 993 (SSL/TLS)
        use_ssl: 是否使用 SSL/TLS 加密，默认 True
    """

    server: str
    port: int = 993
    use_ssl: bool = True

    def validate(self) -> None:
        """验证 IMAP 配置的有效性"""
        if not self.server or not self.server.strip():
            raise InvalidValueObjectException(
                value_object_type="ImapConfig",
                value=self.server,
                reason="IMAP server cannot be empty"
            )

        if not 1 <= self.port <= 65535:
            raise InvalidValueObjectException(
                value_object_type="ImapConfig",
                value=self.port,
                reason=f"Invalid port number: {self.port}. Must be between 1 and 65535"
            )

    @property
    def connection_string(self) -> str:
        """返回连接字符串格式"""
        protocol = "imaps" if self.use_ssl else "imap"
        return f"{protocol}://{self.server}:{self.port}"
