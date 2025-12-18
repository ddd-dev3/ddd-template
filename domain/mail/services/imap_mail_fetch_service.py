"""IMAP 邮件收取服务接口"""

from abc import ABC, abstractmethod
from typing import List

from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mail.value_objects.parsed_email import ParsedEmail


class ImapMailFetchService(ABC):
    """
    IMAP 邮件收取服务接口

    定义通过 IMAP 协议收取邮件的契约。
    具体实现在基础设施层，负责：
    - IMAP SSL/TLS 连接管理
    - 未读邮件收取
    - 邮件内容解析
    - 自动重连逻辑
    """

    @abstractmethod
    def fetch_new_emails(self, mailbox: MailboxAccount) -> List[ParsedEmail]:
        """
        收取指定邮箱的新邮件

        连接到邮箱的 IMAP 服务器，获取所有未读邮件，
        解析邮件内容，并将邮件标记为已读。

        Args:
            mailbox: 邮箱账号实体（包含 IMAP 配置和加密密码）

        Returns:
            解析后的邮件列表

        Raises:
            ImapConnectionError: IMAP 连接失败
            ImapAuthenticationError: IMAP 认证失败
        """
        raise NotImplementedError

    @abstractmethod
    def test_connection(self, mailbox: MailboxAccount) -> bool:
        """
        测试邮箱的 IMAP 连接

        尝试连接到 IMAP 服务器并进行身份验证，
        用于验证邮箱配置是否正确。

        Args:
            mailbox: 邮箱账号实体

        Returns:
            True 如果连接成功，False 如果失败
        """
        raise NotImplementedError


class ImapConnectionError(Exception):
    """IMAP 连接错误"""

    def __init__(self, server: str, port: int, message: str):
        self.server = server
        self.port = port
        super().__init__(f"Failed to connect to {server}:{port} - {message}")


class ImapAuthenticationError(Exception):
    """IMAP 认证错误"""

    def __init__(self, username: str, message: str):
        self.username = username
        super().__init__(f"Authentication failed for {username} - {message}")
