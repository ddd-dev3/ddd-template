"""Tests for MailboxAccount aggregate root"""

import pytest
from uuid import UUID
from cryptography.fernet import Fernet

from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mailbox.value_objects.mailbox_enums import MailboxType, MailboxStatus
from domain.mailbox.value_objects.imap_config import ImapConfig
from domain.common.exceptions import (
    InvalidOperationException,
    InvalidStateTransitionException,
)


class TestMailboxAccountCreation:
    """MailboxAccount 创建测试"""

    @pytest.fixture
    def encryption_key(self) -> bytes:
        """生成测试用加密密钥"""
        return Fernet.generate_key()

    @pytest.fixture
    def imap_config(self) -> ImapConfig:
        """创建测试用 IMAP 配置"""
        return ImapConfig(server="imap.example.com", port=993, use_ssl=True)

    def test_create_domain_catchall_mailbox(
        self, encryption_key: bytes, imap_config: ImapConfig
    ):
        """测试创建域名 Catch-All 邮箱"""
        mailbox = MailboxAccount.create_domain_catchall(
            username="admin@example.com",
            domain="example.com",
            imap_config=imap_config,
            password="secret123",
            encryption_key=encryption_key,
        )

        assert mailbox.username == "admin@example.com"
        assert mailbox.mailbox_type == MailboxType.DOMAIN_CATCHALL
        assert mailbox.domain == "example.com"
        assert mailbox.imap_config == imap_config
        assert mailbox.status == MailboxStatus.AVAILABLE
        assert mailbox.encrypted_password is not None
        assert mailbox.id is not None

    def test_create_domain_catchall_with_custom_id(
        self, encryption_key: bytes, imap_config: ImapConfig
    ):
        """测试使用自定义 ID 创建域名 Catch-All 邮箱"""
        custom_id = UUID("12345678-1234-5678-1234-567812345678")
        mailbox = MailboxAccount.create_domain_catchall(
            username="admin@example.com",
            domain="example.com",
            imap_config=imap_config,
            password="secret123",
            encryption_key=encryption_key,
            id=custom_id,
        )

        assert mailbox.id == custom_id

    def test_create_hotmail_mailbox(
        self, encryption_key: bytes, imap_config: ImapConfig
    ):
        """测试创建 Hotmail 邮箱"""
        mailbox = MailboxAccount.create_hotmail(
            username="user@hotmail.com",
            imap_config=imap_config,
            password="secret123",
            encryption_key=encryption_key,
        )

        assert mailbox.username == "user@hotmail.com"
        assert mailbox.mailbox_type == MailboxType.HOTMAIL
        assert mailbox.domain is None
        assert mailbox.status == MailboxStatus.AVAILABLE

    def test_create_without_username_raises_error(
        self, encryption_key: bytes, imap_config: ImapConfig
    ):
        """测试没有用户名创建抛出异常"""
        with pytest.raises(InvalidOperationException) as exc_info:
            MailboxAccount(
                username="",
                mailbox_type=MailboxType.DOMAIN_CATCHALL,
                imap_config=imap_config,
                domain="example.com",
            )

        assert "Username cannot be empty" in str(exc_info.value.message)

    def test_create_domain_catchall_without_domain_raises_error(
        self, encryption_key: bytes, imap_config: ImapConfig
    ):
        """测试创建域名 Catch-All 邮箱没有域名抛出异常"""
        with pytest.raises(InvalidOperationException) as exc_info:
            MailboxAccount(
                username="admin@example.com",
                mailbox_type=MailboxType.DOMAIN_CATCHALL,
                imap_config=imap_config,
                domain=None,
            )

        assert "Domain is required for domain_catchall" in str(exc_info.value.message)


class TestMailboxAccountStatus:
    """MailboxAccount 状态管理测试"""

    @pytest.fixture
    def encryption_key(self) -> bytes:
        """生成测试用加密密钥"""
        return Fernet.generate_key()

    @pytest.fixture
    def available_mailbox(self, encryption_key: bytes) -> MailboxAccount:
        """创建可用状态的邮箱"""
        return MailboxAccount.create_domain_catchall(
            username="admin@example.com",
            domain="example.com",
            imap_config=ImapConfig(server="imap.example.com"),
            password="secret123",
            encryption_key=encryption_key,
        )

    def test_occupy_available_mailbox(self, available_mailbox: MailboxAccount):
        """测试占用可用邮箱"""
        available_mailbox.occupy("claude_service")

        assert available_mailbox.status == MailboxStatus.OCCUPIED
        assert available_mailbox.occupied_by_service == "claude_service"
        assert available_mailbox.is_occupied is True
        assert available_mailbox.is_available is False

    def test_occupy_already_occupied_mailbox_raises_error(
        self, available_mailbox: MailboxAccount
    ):
        """测试占用已被占用的邮箱抛出异常"""
        available_mailbox.occupy("claude_service")

        with pytest.raises(InvalidStateTransitionException) as exc_info:
            available_mailbox.occupy("another_service")

        assert "already occupied" in str(exc_info.value.message)

    def test_release_occupied_mailbox(self, available_mailbox: MailboxAccount):
        """测试释放被占用的邮箱"""
        available_mailbox.occupy("claude_service")
        available_mailbox.release()

        assert available_mailbox.status == MailboxStatus.AVAILABLE
        assert available_mailbox.occupied_by_service is None
        assert available_mailbox.is_available is True
        assert available_mailbox.is_occupied is False

    def test_release_available_mailbox_raises_error(
        self, available_mailbox: MailboxAccount
    ):
        """测试释放可用邮箱抛出异常"""
        with pytest.raises(InvalidStateTransitionException) as exc_info:
            available_mailbox.release()

        assert "not occupied" in str(exc_info.value.message)


class TestMailboxAccountPassword:
    """MailboxAccount 密码管理测试"""

    @pytest.fixture
    def encryption_key(self) -> bytes:
        """生成测试用加密密钥"""
        return Fernet.generate_key()

    def test_get_decrypted_password(self, encryption_key: bytes):
        """测试获取解密后的密码"""
        mailbox = MailboxAccount.create_domain_catchall(
            username="admin@example.com",
            domain="example.com",
            imap_config=ImapConfig(server="imap.example.com"),
            password="secret123",
            encryption_key=encryption_key,
        )

        decrypted = mailbox.get_decrypted_password(encryption_key)

        assert decrypted == "secret123"

    def test_get_password_without_password_set_raises_error(
        self, encryption_key: bytes
    ):
        """测试没有设置密码时获取密码抛出异常"""
        mailbox = MailboxAccount(
            username="admin@example.com",
            mailbox_type=MailboxType.HOTMAIL,
            imap_config=ImapConfig(server="imap.example.com"),
            encrypted_password=None,
        )

        with pytest.raises(InvalidOperationException) as exc_info:
            mailbox.get_decrypted_password(encryption_key)

        assert "No password has been set" in str(exc_info.value.message)


class TestMailboxAccountEquality:
    """MailboxAccount 相等性测试"""

    @pytest.fixture
    def encryption_key(self) -> bytes:
        """生成测试用加密密钥"""
        return Fernet.generate_key()

    def test_same_id_are_equal(self, encryption_key: bytes):
        """测试相同 ID 的邮箱相等"""
        custom_id = UUID("12345678-1234-5678-1234-567812345678")
        mailbox1 = MailboxAccount.create_domain_catchall(
            username="admin@example.com",
            domain="example.com",
            imap_config=ImapConfig(server="imap.example.com"),
            password="secret123",
            encryption_key=encryption_key,
            id=custom_id,
        )
        mailbox2 = MailboxAccount.create_domain_catchall(
            username="other@example.com",  # 不同用户名
            domain="other.com",  # 不同域名
            imap_config=ImapConfig(server="imap.other.com"),
            password="other_password",
            encryption_key=encryption_key,
            id=custom_id,  # 相同 ID
        )

        assert mailbox1 == mailbox2

    def test_different_id_are_not_equal(self, encryption_key: bytes):
        """测试不同 ID 的邮箱不相等"""
        mailbox1 = MailboxAccount.create_domain_catchall(
            username="admin@example.com",
            domain="example.com",
            imap_config=ImapConfig(server="imap.example.com"),
            password="secret123",
            encryption_key=encryption_key,
        )
        mailbox2 = MailboxAccount.create_domain_catchall(
            username="admin@example.com",  # 相同用户名
            domain="example.com",  # 相同域名
            imap_config=ImapConfig(server="imap.example.com"),
            password="secret123",
            encryption_key=encryption_key,
        )

        assert mailbox1 != mailbox2  # 因为 ID 不同
