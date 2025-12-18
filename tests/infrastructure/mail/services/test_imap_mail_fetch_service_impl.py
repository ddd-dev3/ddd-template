"""ImapMailFetchServiceImpl 单元测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4
import imaplib

from infrastructure.mail.services.imap_mail_fetch_service_impl import (
    ImapMailFetchServiceImpl,
)
from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mailbox.value_objects.imap_config import ImapConfig
from domain.mailbox.value_objects.encrypted_password import EncryptedPassword
from domain.mailbox.value_objects.mailbox_enums import MailboxType, MailboxStatus
from domain.mail.services.imap_mail_fetch_service import (
    ImapConnectionError,
    ImapAuthenticationError,
)


# 测试用的加密密钥 (有效的 Fernet 密钥)
# 使用 Fernet.generate_key() 生成
TEST_ENCRYPTION_KEY = "xiJ-vQsN3KaewjOgc0qvuNE831TgyRAPSs-8X14qHes="


def create_test_mailbox(
    username: str = "test@example.com",
    password: str = "test_password",
    server: str = "imap.example.com",
    port: int = 993,
) -> MailboxAccount:
    """创建测试用的邮箱账号"""
    return MailboxAccount.create_hotmail(
        username=username,
        imap_config=ImapConfig(server=server, port=port),
        password=password,
        encryption_key=TEST_ENCRYPTION_KEY,
    )


def create_mock_email_data(
    message_id: str = "<test@example.com>",
    from_address: str = "sender@example.com",
    subject: str = "Test Subject",
    body_text: str = "Test body content",
) -> bytes:
    """创建模拟的原始邮件数据"""
    email_content = f"""From: {from_address}
To: recipient@example.com
Subject: {subject}
Message-ID: {message_id}
Date: Mon, 16 Dec 2024 10:00:00 +0000
Content-Type: text/plain; charset="utf-8"

{body_text}
"""
    return email_content.encode("utf-8")


class TestImapMailFetchServiceImplInit:
    """初始化测试"""

    def test_init_with_encryption_key(self):
        """测试使用加密密钥初始化"""
        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)
        assert service._encryption_key == TEST_ENCRYPTION_KEY

    def test_init_with_custom_logger(self):
        """测试使用自定义 logger 初始化"""
        mock_logger = Mock()
        service = ImapMailFetchServiceImpl(
            encryption_key=TEST_ENCRYPTION_KEY,
            logger=mock_logger,
        )
        assert service._logger == mock_logger


class TestImapMailFetchServiceImplConnect:
    """连接测试"""

    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.imaplib.IMAP4_SSL")
    def test_connect_success(self, mock_imap_class):
        """测试成功连接 IMAP 服务器"""
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [b"Logged in"])
        mock_imap_class.return_value = mock_imap

        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)
        mailbox = create_test_mailbox()

        result = service._connect(mailbox)

        assert result == mock_imap
        mock_imap_class.assert_called_once()
        mock_imap.login.assert_called_once_with("test@example.com", "test_password")

    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.imaplib.IMAP4_SSL")
    def test_connect_failure_raises_connection_error(self, mock_imap_class):
        """测试连接失败抛出 ImapConnectionError"""
        mock_imap_class.side_effect = Exception("Connection refused")

        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)
        mailbox = create_test_mailbox()

        with pytest.raises(ImapConnectionError) as exc_info:
            service._connect(mailbox)

        assert "imap.example.com:993" in str(exc_info.value)

    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.imaplib.IMAP4_SSL")
    def test_connect_auth_failure_raises_auth_error(self, mock_imap_class):
        """测试认证失败抛出 ImapAuthenticationError"""
        mock_imap = MagicMock()
        mock_imap.login.side_effect = imaplib.IMAP4.error("Invalid credentials")
        mock_imap_class.return_value = mock_imap

        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)
        mailbox = create_test_mailbox()

        with pytest.raises(ImapAuthenticationError) as exc_info:
            service._connect(mailbox)

        assert "test@example.com" in str(exc_info.value)


class TestImapMailFetchServiceImplRetry:
    """重连逻辑测试"""

    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.time.sleep")
    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.imaplib.IMAP4_SSL")
    def test_connect_with_retry_success_on_second_attempt(
        self, mock_imap_class, mock_sleep
    ):
        """测试第二次尝试成功连接"""
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [b"Logged in"])

        # 第一次失败，第二次成功
        mock_imap_class.side_effect = [Exception("Temporary failure"), mock_imap]

        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)
        mailbox = create_test_mailbox()

        result = service._connect_with_retry(mailbox)

        assert result == mock_imap
        assert mock_imap_class.call_count == 2
        mock_sleep.assert_called_once_with(1)  # 第一次重试延迟 1 秒

    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.time.sleep")
    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.imaplib.IMAP4_SSL")
    def test_connect_with_retry_all_attempts_fail(self, mock_imap_class, mock_sleep):
        """测试所有重试都失败"""
        mock_imap_class.side_effect = Exception("Persistent failure")

        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)
        mailbox = create_test_mailbox()

        result = service._connect_with_retry(mailbox)

        assert result is None
        assert mock_imap_class.call_count == 3  # MAX_RETRIES = 3
        assert mock_sleep.call_count == 2  # 最后一次失败后不再 sleep


class TestImapMailFetchServiceImplFetchEmails:
    """收取邮件测试"""

    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.imaplib.IMAP4_SSL")
    def test_fetch_new_emails_success(self, mock_imap_class):
        """测试成功收取新邮件"""
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [b"Logged in"])
        mock_imap.select.return_value = ("OK", [b"1"])
        mock_imap.search.return_value = ("OK", [b"1 2"])
        mock_imap.fetch.return_value = ("OK", [(b"1", create_mock_email_data())])
        mock_imap.store.return_value = ("OK", [b""])
        mock_imap_class.return_value = mock_imap

        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)
        mailbox = create_test_mailbox()

        emails = service.fetch_new_emails(mailbox)

        assert len(emails) >= 1
        mock_imap.select.assert_called_once_with("INBOX")
        mock_imap.search.assert_called_once_with(None, "UNSEEN")

    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.imaplib.IMAP4_SSL")
    def test_fetch_new_emails_no_unread(self, mock_imap_class):
        """测试没有未读邮件"""
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [b"Logged in"])
        mock_imap.select.return_value = ("OK", [b"0"])
        mock_imap.search.return_value = ("OK", [b""])  # 无未读邮件
        mock_imap_class.return_value = mock_imap

        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)
        mailbox = create_test_mailbox()

        emails = service.fetch_new_emails(mailbox)

        assert emails == []

    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.time.sleep")
    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.imaplib.IMAP4_SSL")
    def test_fetch_new_emails_connection_failure(self, mock_imap_class, mock_sleep):
        """测试连接失败时返回空列表"""
        mock_imap_class.side_effect = Exception("Connection failed")

        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)
        mailbox = create_test_mailbox()

        emails = service.fetch_new_emails(mailbox)

        assert emails == []


class TestImapMailFetchServiceImplTestConnection:
    """连接测试功能测试"""

    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.imaplib.IMAP4_SSL")
    def test_test_connection_success(self, mock_imap_class):
        """测试连接测试成功"""
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [b"Logged in"])
        mock_imap_class.return_value = mock_imap

        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)
        mailbox = create_test_mailbox()

        result = service.test_connection(mailbox)

        assert result is True

    @patch("infrastructure.mail.services.imap_mail_fetch_service_impl.imaplib.IMAP4_SSL")
    def test_test_connection_failure(self, mock_imap_class):
        """测试连接测试失败"""
        mock_imap_class.side_effect = Exception("Connection failed")

        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)
        mailbox = create_test_mailbox()

        result = service.test_connection(mailbox)

        assert result is False


class TestEmailParsing:
    """邮件解析测试"""

    def test_decode_header_value_plain_text(self):
        """测试解码普通文本头部"""
        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)

        result = service._decode_header_value("Simple Subject")

        assert result == "Simple Subject"

    def test_decode_header_value_encoded(self):
        """测试解码编码的头部"""
        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)

        # Base64 编码的 "测试" (中文)
        encoded = "=?utf-8?b?5rWL6K+V?="
        result = service._decode_header_value(encoded)

        assert result == "测试"

    def test_decode_header_value_none(self):
        """测试解码 None 值"""
        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)

        result = service._decode_header_value(None)

        assert result == ""

    def test_parse_date_valid(self):
        """测试解析有效日期"""
        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)

        result = service._parse_date("Mon, 16 Dec 2024 10:00:00 +0000")

        assert result is not None
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 16

    def test_parse_date_invalid(self):
        """测试解析无效日期返回当前时间"""
        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)

        result = service._parse_date("invalid date")

        assert result is not None
        # 应该返回当前时间

    def test_parse_date_none(self):
        """测试解析 None 返回当前时间"""
        service = ImapMailFetchServiceImpl(encryption_key=TEST_ENCRYPTION_KEY)

        result = service._parse_date(None)

        assert result is not None
