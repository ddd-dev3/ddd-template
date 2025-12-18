"""AddMailboxAccountHandler 单元测试"""

import pytest
from unittest.mock import Mock, MagicMock
from cryptography.fernet import Fernet

from application.commands.mailbox.add_mailbox_account import AddMailboxAccountCommand
from application.handlers.mailbox.add_mailbox_account_handler import (
    AddMailboxAccountHandler,
    AddMailboxAccountResult,
)
from domain.mailbox.repositories.mailbox_account_repository import MailboxAccountRepository
from domain.mailbox.services.imap_connection_validator import ImapConnectionValidator
from domain.common.exceptions import ImapConnectionException, ImapAuthenticationException


@pytest.fixture
def encryption_key() -> str:
    """生成测试用加密密钥"""
    return Fernet.generate_key().decode()


@pytest.fixture
def mock_repository() -> Mock:
    """创建 Mock 仓储"""
    return Mock(spec=MailboxAccountRepository)


@pytest.fixture
def mock_imap_validator() -> Mock:
    """创建 Mock IMAP 验证器"""
    return Mock(spec=ImapConnectionValidator)


@pytest.fixture
def handler(
    mock_repository: Mock,
    mock_imap_validator: Mock,
    encryption_key: str,
) -> AddMailboxAccountHandler:
    """创建处理器实例"""
    return AddMailboxAccountHandler(
        repository=mock_repository,
        imap_validator=mock_imap_validator,
        encryption_key=encryption_key,
    )


class TestAddMailboxAccountHandlerSuccess:
    """成功场景测试"""

    @pytest.mark.asyncio
    async def test_add_domain_catchall_mailbox_success(
        self,
        handler: AddMailboxAccountHandler,
        mock_repository: Mock,
        mock_imap_validator: Mock,
    ):
        """测试成功添加域名 Catch-All 邮箱"""
        # Arrange
        mock_repository.exists_by_username.return_value = False
        mock_imap_validator.validate.return_value = None  # 验证通过

        command = AddMailboxAccountCommand(
            mailbox_type="domain_catchall",
            username="admin@example.com",
            password="secret123",
            imap_server="imap.example.com",
            imap_port=993,
            use_ssl=True,
            domain="example.com",
        )

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.success is True
        assert result.mailbox_id is not None
        assert result.username == "admin@example.com"
        assert result.error_code is None

        # 验证仓储调用
        mock_repository.exists_by_username.assert_called_once_with("admin@example.com")
        mock_repository.add.assert_called_once()

        # 验证 IMAP 验证调用
        mock_imap_validator.validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_hotmail_mailbox_success(
        self,
        handler: AddMailboxAccountHandler,
        mock_repository: Mock,
        mock_imap_validator: Mock,
    ):
        """测试成功添加 Hotmail 邮箱"""
        # Arrange
        mock_repository.exists_by_username.return_value = False
        mock_imap_validator.validate.return_value = None

        command = AddMailboxAccountCommand(
            mailbox_type="hotmail",
            username="user@hotmail.com",
            password="password123",
            imap_server="outlook.office365.com",
            imap_port=993,
            use_ssl=True,
        )

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.success is True
        assert result.mailbox_id is not None
        assert result.username == "user@hotmail.com"
        mock_repository.add.assert_called_once()


class TestAddMailboxAccountHandlerValidation:
    """验证场景测试"""

    @pytest.mark.asyncio
    async def test_invalid_mailbox_type_returns_error(
        self,
        handler: AddMailboxAccountHandler,
        mock_repository: Mock,
    ):
        """测试无效邮箱类型返回错误"""
        # Arrange
        command = AddMailboxAccountCommand(
            mailbox_type="invalid_type",
            username="test@example.com",
            password="secret",
            imap_server="imap.example.com",
        )

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.success is False
        assert result.error_code == "INVALID_MAILBOX_TYPE"
        assert "invalid_type" in result.message

        # 仓储不应被调用
        mock_repository.exists_by_username.assert_not_called()
        mock_repository.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_domain_catchall_without_domain_returns_error(
        self,
        handler: AddMailboxAccountHandler,
        mock_repository: Mock,
        mock_imap_validator: Mock,
    ):
        """测试域名 Catch-All 邮箱没有提供域名返回错误"""
        # Arrange
        mock_repository.exists_by_username.return_value = False
        mock_imap_validator.validate.return_value = None

        command = AddMailboxAccountCommand(
            mailbox_type="domain_catchall",
            username="admin@example.com",
            password="secret",
            imap_server="imap.example.com",
            domain=None,  # 缺少域名
        )

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.success is False
        assert result.error_code == "MISSING_DOMAIN"
        mock_repository.add.assert_not_called()


class TestAddMailboxAccountHandlerDuplicate:
    """重复检测测试"""

    @pytest.mark.asyncio
    async def test_duplicate_mailbox_returns_error(
        self,
        handler: AddMailboxAccountHandler,
        mock_repository: Mock,
    ):
        """测试重复邮箱返回错误"""
        # Arrange
        mock_repository.exists_by_username.return_value = True  # 已存在

        command = AddMailboxAccountCommand(
            mailbox_type="hotmail",
            username="existing@hotmail.com",
            password="secret",
            imap_server="outlook.office365.com",
        )

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.success is False
        assert result.error_code == "DUPLICATE_MAILBOX"
        assert "already exists" in result.message
        mock_repository.add.assert_not_called()


class TestAddMailboxAccountHandlerImapValidation:
    """IMAP 验证测试"""

    @pytest.mark.asyncio
    async def test_imap_connection_error_returns_error(
        self,
        handler: AddMailboxAccountHandler,
        mock_repository: Mock,
        mock_imap_validator: Mock,
    ):
        """测试 IMAP 连接失败返回错误"""
        # Arrange
        mock_repository.exists_by_username.return_value = False
        mock_imap_validator.validate.side_effect = ImapConnectionException(
            message="Connection refused",
            server="imap.example.com",
            port=993,
        )

        command = AddMailboxAccountCommand(
            mailbox_type="hotmail",
            username="test@hotmail.com",
            password="wrong",
            imap_server="imap.example.com",
        )

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.success is False
        assert result.error_code == "IMAP_CONNECTION_ERROR"
        assert "Connection refused" in result.message
        mock_repository.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_imap_auth_error_returns_error(
        self,
        handler: AddMailboxAccountHandler,
        mock_repository: Mock,
        mock_imap_validator: Mock,
    ):
        """测试 IMAP 认证失败返回错误"""
        # Arrange
        mock_repository.exists_by_username.return_value = False
        mock_imap_validator.validate.side_effect = ImapAuthenticationException(
            message="Invalid credentials",
            server="imap.example.com",
            port=993,
        )

        command = AddMailboxAccountCommand(
            mailbox_type="hotmail",
            username="test@hotmail.com",
            password="wrong_password",
            imap_server="imap.example.com",
        )

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.success is False
        assert result.error_code == "IMAP_AUTH_ERROR"
        assert "Invalid credentials" in result.message
        mock_repository.add.assert_not_called()


class TestAddMailboxAccountHandlerEncryption:
    """加密测试"""

    @pytest.mark.asyncio
    async def test_password_is_encrypted_before_saving(
        self,
        handler: AddMailboxAccountHandler,
        mock_repository: Mock,
        mock_imap_validator: Mock,
        encryption_key: str,
    ):
        """测试密码在保存前被加密"""
        # Arrange
        mock_repository.exists_by_username.return_value = False
        mock_imap_validator.validate.return_value = None
        plain_password = "my_secret_password"

        command = AddMailboxAccountCommand(
            mailbox_type="hotmail",
            username="test@hotmail.com",
            password=plain_password,
            imap_server="outlook.office365.com",
        )

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.success is True

        # 获取保存的邮箱实体
        saved_mailbox = mock_repository.add.call_args[0][0]

        # 验证密码已加密
        assert saved_mailbox.encrypted_password is not None
        assert saved_mailbox.encrypted_password.encrypted_value != plain_password.encode()

        # 验证可以解密回原始密码
        decrypted = saved_mailbox.get_decrypted_password(encryption_key)
        assert decrypted == plain_password


class TestAddMailboxAccountResult:
    """结果对象测试"""

    def test_success_result(self):
        """测试成功结果"""
        result = AddMailboxAccountResult(
            success=True,
            mailbox_id="123",
            username="test@test.com",
            message="Created",
        )
        assert result.success is True
        assert result.error_code is None

    def test_failure_result(self):
        """测试失败结果"""
        result = AddMailboxAccountResult(
            success=False,
            username="test@test.com",
            message="Error",
            error_code="SOME_ERROR",
        )
        assert result.success is False
        assert result.error_code == "SOME_ERROR"
