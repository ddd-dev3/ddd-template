"""RegisterWaitRequestHandler 测试"""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from application.commands.verification.register_wait_request import (
    RegisterWaitRequestCommand,
    RegisterWaitRequestHandler,
    RegisterWaitRequestResult,
)
from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mailbox.value_objects.mailbox_enums import MailboxStatus, MailboxType
from domain.verification.entities.wait_request import WaitRequest


class TestRegisterWaitRequestCommand:
    """RegisterWaitRequestCommand 数据类测试"""

    def test_create_command(self):
        """测试创建命令"""
        command = RegisterWaitRequestCommand(
            email="test@example.com",
            service_name="claude",
            callback_url="https://api.example.com/callback",
        )

        assert command.email == "test@example.com"
        assert command.service_name == "claude"
        assert command.callback_url == "https://api.example.com/callback"


class TestRegisterWaitRequestResult:
    """RegisterWaitRequestResult 数据类测试"""

    def test_success_result(self):
        """测试成功结果"""
        request_id = uuid4()
        result = RegisterWaitRequestResult(
            success=True,
            request_id=request_id,
            message="Wait request created successfully",
        )

        assert result.success is True
        assert result.request_id == request_id
        assert result.message == "Wait request created successfully"
        assert result.error_code is None

    def test_failure_result(self):
        """测试失败结果"""
        result = RegisterWaitRequestResult(
            success=False,
            message="Mailbox not found",
            error_code="MAILBOX_NOT_FOUND",
        )

        assert result.success is False
        assert result.request_id is None
        assert result.message == "Mailbox not found"
        assert result.error_code == "MAILBOX_NOT_FOUND"


class TestRegisterWaitRequestHandler:
    """RegisterWaitRequestHandler 处理器测试"""

    @pytest.fixture
    def mock_mailbox_repo(self):
        """创建 mock 邮箱仓储"""
        return Mock()

    @pytest.fixture
    def mock_wait_request_repo(self):
        """创建 mock 等待请求仓储"""
        return Mock()

    @pytest.fixture
    def handler(self, mock_mailbox_repo, mock_wait_request_repo):
        """创建处理器实例"""
        return RegisterWaitRequestHandler(
            mailbox_repo=mock_mailbox_repo,
            wait_request_repo=mock_wait_request_repo,
        )

    @pytest.fixture
    def available_mailbox(self):
        """创建一个可用状态的邮箱"""
        mailbox = Mock(spec=MailboxAccount)
        mailbox.id = uuid4()
        mailbox.username = "test@example.com"
        mailbox.status = MailboxStatus.AVAILABLE
        mailbox.occupied_by_service = None
        return mailbox

    @pytest.fixture
    def occupied_mailbox(self):
        """创建一个已占用状态的邮箱"""
        mailbox = Mock(spec=MailboxAccount)
        mailbox.id = uuid4()
        mailbox.username = "test@example.com"
        mailbox.status = MailboxStatus.OCCUPIED
        mailbox.occupied_by_service = "other_service"
        return mailbox


class TestRegisterWaitRequestHandlerSuccess(TestRegisterWaitRequestHandler):
    """成功场景测试"""

    def test_handle_success(
        self, handler, mock_mailbox_repo, mock_wait_request_repo, available_mailbox
    ):
        """测试成功创建等待请求 (AC1)"""
        # 设置 mock 返回值
        mock_mailbox_repo.get_by_username.return_value = available_mailbox

        # 创建命令
        command = RegisterWaitRequestCommand(
            email="test@example.com",
            service_name="claude",
            callback_url="https://api.example.com/callback",
        )

        # 执行
        result = handler.handle(command)

        # 验证
        assert result.success is True
        assert result.request_id is not None
        assert result.message == "Wait request created successfully"
        assert result.error_code is None

        # 验证邮箱被占用
        available_mailbox.occupy.assert_called_once_with("claude")
        mock_mailbox_repo.update.assert_called_once_with(available_mailbox)

        # 验证等待请求被添加
        mock_wait_request_repo.add.assert_called_once()


class TestRegisterWaitRequestHandlerMailboxNotFound(TestRegisterWaitRequestHandler):
    """邮箱不存在场景测试"""

    def test_handle_mailbox_not_found(
        self, handler, mock_mailbox_repo, mock_wait_request_repo
    ):
        """测试邮箱不存在返回 404 (AC3)"""
        # 设置 mock 返回 None
        mock_mailbox_repo.get_by_username.return_value = None

        # 创建命令
        command = RegisterWaitRequestCommand(
            email="nonexistent@example.com",
            service_name="claude",
            callback_url="https://api.example.com/callback",
        )

        # 执行
        result = handler.handle(command)

        # 验证
        assert result.success is False
        assert result.request_id is None
        assert "Mailbox not found" in result.message
        assert result.error_code == "MAILBOX_NOT_FOUND"

        # 验证没有尝试创建等待请求
        mock_wait_request_repo.add.assert_not_called()


class TestRegisterWaitRequestHandlerMailboxOccupied(TestRegisterWaitRequestHandler):
    """邮箱已占用场景测试"""

    def test_handle_mailbox_occupied(
        self, handler, mock_mailbox_repo, mock_wait_request_repo, occupied_mailbox
    ):
        """测试邮箱已被占用返回 409 (AC2)"""
        # 设置 mock 返回已占用的邮箱
        mock_mailbox_repo.get_by_username.return_value = occupied_mailbox

        # 创建命令
        command = RegisterWaitRequestCommand(
            email="test@example.com",
            service_name="claude",
            callback_url="https://api.example.com/callback",
        )

        # 执行
        result = handler.handle(command)

        # 验证
        assert result.success is False
        assert result.request_id is None
        assert "already occupied" in result.message
        assert result.error_code == "MAILBOX_OCCUPIED"

        # 验证没有尝试占用邮箱
        occupied_mailbox.occupy.assert_not_called()
        mock_mailbox_repo.update.assert_not_called()

        # 验证没有尝试创建等待请求
        mock_wait_request_repo.add.assert_not_called()


class TestRegisterWaitRequestHandlerEdgeCases(TestRegisterWaitRequestHandler):
    """边界情况测试"""

    def test_handle_with_long_callback_url(
        self, handler, mock_mailbox_repo, mock_wait_request_repo, available_mailbox
    ):
        """测试长回调 URL"""
        mock_mailbox_repo.get_by_username.return_value = available_mailbox

        long_url = "https://api.example.com/callback?" + "x" * 500

        command = RegisterWaitRequestCommand(
            email="test@example.com",
            service_name="claude",
            callback_url=long_url,
        )

        result = handler.handle(command)

        assert result.success is True

    def test_handle_with_special_characters_in_service_name(
        self, handler, mock_mailbox_repo, mock_wait_request_repo, available_mailbox
    ):
        """测试服务名包含特殊字符"""
        mock_mailbox_repo.get_by_username.return_value = available_mailbox

        command = RegisterWaitRequestCommand(
            email="test@example.com",
            service_name="claude-ai-v2",
            callback_url="https://api.example.com/callback",
        )

        result = handler.handle(command)

        assert result.success is True
        available_mailbox.occupy.assert_called_once_with("claude-ai-v2")
