"""DeleteMailboxAccountHandler 单元测试"""

import pytest
from unittest.mock import Mock
from uuid import uuid4

from application.handlers.mailbox.delete_mailbox_account_handler import (
    DeleteMailboxAccountHandler,
)
from application.commands.mailbox.delete_mailbox_account import (
    DeleteMailboxAccountCommand,
)
from domain.mailbox.repositories.mailbox_account_repository import MailboxAccountRepository
from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mailbox.value_objects.mailbox_enums import MailboxStatus


def create_mock_mailbox(
    mailbox_id: str = None,
    username: str = "test@example.com",
    status: MailboxStatus = MailboxStatus.AVAILABLE,
) -> Mock:
    """创建用于测试的 Mock 邮箱实体"""
    mailbox = Mock(spec=MailboxAccount)
    mailbox.id = mailbox_id or str(uuid4())
    mailbox.username = username
    mailbox.status = status
    return mailbox


@pytest.fixture
def mock_repository() -> Mock:
    """创建 Mock 仓储"""
    return Mock(spec=MailboxAccountRepository)


@pytest.fixture
def handler(mock_repository: Mock) -> DeleteMailboxAccountHandler:
    """创建处理器实例"""
    return DeleteMailboxAccountHandler(repository=mock_repository)


class TestDeleteMailboxAccountHandlerSuccess:
    """成功删除测试"""

    @pytest.mark.asyncio
    async def test_delete_available_mailbox_success(
        self,
        handler: DeleteMailboxAccountHandler,
        mock_repository: Mock,
    ):
        """测试成功删除 available 状态的邮箱"""
        mailbox_id = str(uuid4())
        mailbox = create_mock_mailbox(
            mailbox_id=mailbox_id,
            username="test@example.com",
            status=MailboxStatus.AVAILABLE,
        )
        mock_repository.get_by_id.return_value = mailbox

        command = DeleteMailboxAccountCommand(mailbox_id=mailbox_id)
        result = await handler.handle(command)

        assert result.success is True
        assert result.mailbox_id == mailbox_id
        assert result.username == "test@example.com"
        assert "deleted successfully" in result.message
        mock_repository.remove.assert_called_once_with(mailbox)

    @pytest.mark.asyncio
    async def test_delete_calls_repository_remove(
        self,
        handler: DeleteMailboxAccountHandler,
        mock_repository: Mock,
    ):
        """测试删除调用仓储的 remove 方法"""
        mailbox_id = str(uuid4())
        mailbox = create_mock_mailbox(mailbox_id=mailbox_id)
        mock_repository.get_by_id.return_value = mailbox

        command = DeleteMailboxAccountCommand(mailbox_id=mailbox_id)
        await handler.handle(command)

        mock_repository.remove.assert_called_once_with(mailbox)


class TestDeleteMailboxAccountHandlerNotFound:
    """邮箱不存在测试"""

    @pytest.mark.asyncio
    async def test_delete_nonexistent_mailbox_returns_not_found(
        self,
        handler: DeleteMailboxAccountHandler,
        mock_repository: Mock,
    ):
        """测试删除不存在的邮箱返回 MAILBOX_NOT_FOUND"""
        mailbox_id = str(uuid4())
        mock_repository.get_by_id.return_value = None

        command = DeleteMailboxAccountCommand(mailbox_id=mailbox_id)
        result = await handler.handle(command)

        assert result.success is False
        assert result.error_code == "MAILBOX_NOT_FOUND"
        assert mailbox_id in result.message
        mock_repository.remove.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_invalid_uuid_returns_not_found(
        self,
        handler: DeleteMailboxAccountHandler,
        mock_repository: Mock,
    ):
        """测试无效 UUID 格式返回 MAILBOX_NOT_FOUND"""
        invalid_id = "not-a-valid-uuid"

        command = DeleteMailboxAccountCommand(mailbox_id=invalid_id)
        result = await handler.handle(command)

        assert result.success is False
        assert result.error_code == "MAILBOX_NOT_FOUND"
        mock_repository.get_by_id.assert_not_called()
        mock_repository.remove.assert_not_called()


class TestDeleteMailboxAccountHandlerOccupied:
    """邮箱被占用测试"""

    @pytest.mark.asyncio
    async def test_delete_occupied_mailbox_returns_conflict(
        self,
        handler: DeleteMailboxAccountHandler,
        mock_repository: Mock,
    ):
        """测试删除 occupied 状态的邮箱返回 MAILBOX_OCCUPIED"""
        mailbox_id = str(uuid4())
        mailbox = create_mock_mailbox(
            mailbox_id=mailbox_id,
            username="occupied@example.com",
            status=MailboxStatus.OCCUPIED,
        )
        mock_repository.get_by_id.return_value = mailbox

        command = DeleteMailboxAccountCommand(mailbox_id=mailbox_id)
        result = await handler.handle(command)

        assert result.success is False
        assert result.error_code == "MAILBOX_OCCUPIED"
        assert "Release it first" in result.message
        assert result.username == "occupied@example.com"
        mock_repository.remove.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_occupied_does_not_call_remove(
        self,
        handler: DeleteMailboxAccountHandler,
        mock_repository: Mock,
    ):
        """测试 occupied 邮箱不调用 remove"""
        mailbox_id = str(uuid4())
        mailbox = create_mock_mailbox(status=MailboxStatus.OCCUPIED)
        mock_repository.get_by_id.return_value = mailbox

        command = DeleteMailboxAccountCommand(mailbox_id=mailbox_id)
        await handler.handle(command)

        mock_repository.remove.assert_not_called()


class TestDeleteMailboxAccountHandlerEdgeCases:
    """边界情况测试"""

    @pytest.mark.asyncio
    async def test_delete_with_empty_string_id(
        self,
        handler: DeleteMailboxAccountHandler,
        mock_repository: Mock,
    ):
        """测试空字符串 ID"""
        command = DeleteMailboxAccountCommand(mailbox_id="")
        result = await handler.handle(command)

        assert result.success is False
        assert result.error_code == "MAILBOX_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_result_contains_correct_mailbox_id(
        self,
        handler: DeleteMailboxAccountHandler,
        mock_repository: Mock,
    ):
        """测试结果包含正确的邮箱 ID"""
        mailbox_id = str(uuid4())
        mailbox = create_mock_mailbox(mailbox_id=mailbox_id)
        mock_repository.get_by_id.return_value = mailbox

        command = DeleteMailboxAccountCommand(mailbox_id=mailbox_id)
        result = await handler.handle(command)

        assert result.mailbox_id == mailbox_id

    @pytest.mark.asyncio
    async def test_result_contains_username_on_success(
        self,
        handler: DeleteMailboxAccountHandler,
        mock_repository: Mock,
    ):
        """测试成功时结果包含用户名"""
        mailbox_id = str(uuid4())
        mailbox = create_mock_mailbox(
            mailbox_id=mailbox_id,
            username="specific@example.com",
        )
        mock_repository.get_by_id.return_value = mailbox

        command = DeleteMailboxAccountCommand(mailbox_id=mailbox_id)
        result = await handler.handle(command)

        assert result.username == "specific@example.com"

    @pytest.mark.asyncio
    async def test_result_contains_username_on_occupied_error(
        self,
        handler: DeleteMailboxAccountHandler,
        mock_repository: Mock,
    ):
        """测试占用错误时结果包含用户名"""
        mailbox_id = str(uuid4())
        mailbox = create_mock_mailbox(
            mailbox_id=mailbox_id,
            username="occupied-user@example.com",
            status=MailboxStatus.OCCUPIED,
        )
        mock_repository.get_by_id.return_value = mailbox

        command = DeleteMailboxAccountCommand(mailbox_id=mailbox_id)
        result = await handler.handle(command)

        assert result.username == "occupied-user@example.com"
