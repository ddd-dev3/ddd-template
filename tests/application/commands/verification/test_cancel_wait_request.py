"""CancelWaitRequestHandler 测试"""

import pytest
from unittest.mock import Mock
from uuid import uuid4

from application.commands.verification.cancel_wait_request import (
    CancelWaitRequestCommand,
    CancelWaitRequestHandler,
    CancelWaitRequestResult,
)
from domain.verification.entities.wait_request import WaitRequest
from domain.verification.value_objects.wait_request_status import WaitRequestStatus
from domain.mailbox.entities.mailbox_account import MailboxAccount


class TestCancelWaitRequestCommand:
    """CancelWaitRequestCommand 数据类测试"""

    def test_create_command(self):
        """测试创建命令"""
        request_id = uuid4()
        command = CancelWaitRequestCommand(request_id=request_id)

        assert command.request_id == request_id

    def test_create_command_with_different_uuid(self):
        """测试使用不同 UUID 创建命令"""
        request_id1 = uuid4()
        request_id2 = uuid4()

        command1 = CancelWaitRequestCommand(request_id=request_id1)
        command2 = CancelWaitRequestCommand(request_id=request_id2)

        assert command1.request_id == request_id1
        assert command2.request_id == request_id2
        assert command1.request_id != command2.request_id


class TestCancelWaitRequestResult:
    """CancelWaitRequestResult 数据类测试"""

    def test_success_result(self):
        """测试成功结果"""
        result = CancelWaitRequestResult(
            success=True,
            message="Wait request cancelled successfully",
        )

        assert result.success is True
        assert result.message == "Wait request cancelled successfully"
        assert result.error_code is None
        assert result.current_status is None

    def test_not_found_result(self):
        """测试请求不存在结果"""
        result = CancelWaitRequestResult(
            success=False,
            message="Request not found",
            error_code="NOT_FOUND",
        )

        assert result.success is False
        assert result.message == "Request not found"
        assert result.error_code == "NOT_FOUND"
        assert result.current_status is None

    def test_already_terminal_result(self):
        """测试请求已终止结果"""
        result = CancelWaitRequestResult(
            success=False,
            message="Request cannot be cancelled",
            error_code="ALREADY_TERMINAL",
            current_status="completed",
        )

        assert result.success is False
        assert result.message == "Request cannot be cancelled"
        assert result.error_code == "ALREADY_TERMINAL"
        assert result.current_status == "completed"

    def test_default_values(self):
        """测试默认值"""
        result = CancelWaitRequestResult(success=True)

        assert result.success is True
        assert result.message == ""
        assert result.error_code is None
        assert result.current_status is None


class TestCancelWaitRequestHandler:
    """CancelWaitRequestHandler 处理器测试"""

    @pytest.fixture
    def mock_wait_request_repo(self):
        """创建 mock 等待请求仓储"""
        return Mock()

    @pytest.fixture
    def mock_mailbox_repo(self):
        """创建 mock 邮箱仓储"""
        return Mock()

    @pytest.fixture
    def handler(self, mock_wait_request_repo, mock_mailbox_repo):
        """创建处理器实例"""
        return CancelWaitRequestHandler(
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

    @pytest.fixture
    def pending_wait_request(self):
        """创建一个 PENDING 状态的等待请求"""
        request = Mock(spec=WaitRequest)
        request.id = uuid4()
        request.mailbox_id = uuid4()
        request.email = "test@example.com"
        request.service_name = "claude"
        request.status = WaitRequestStatus.PENDING
        request.is_pending = True
        return request

    @pytest.fixture
    def completed_wait_request(self):
        """创建一个 COMPLETED 状态的等待请求"""
        request = Mock(spec=WaitRequest)
        request.id = uuid4()
        request.mailbox_id = uuid4()
        request.email = "test@example.com"
        request.service_name = "claude"
        request.status = WaitRequestStatus.COMPLETED
        request.is_pending = False
        return request

    @pytest.fixture
    def cancelled_wait_request(self):
        """创建一个 CANCELLED 状态的等待请求"""
        request = Mock(spec=WaitRequest)
        request.id = uuid4()
        request.mailbox_id = uuid4()
        request.email = "test@example.com"
        request.service_name = "claude"
        request.status = WaitRequestStatus.CANCELLED
        request.is_pending = False
        return request

    @pytest.fixture
    def occupied_mailbox(self):
        """创建一个已占用的邮箱"""
        mailbox = Mock(spec=MailboxAccount)
        mailbox.id = uuid4()
        mailbox.is_occupied = True
        return mailbox

    @pytest.fixture
    def available_mailbox(self):
        """创建一个可用的邮箱"""
        mailbox = Mock(spec=MailboxAccount)
        mailbox.id = uuid4()
        mailbox.is_occupied = False
        return mailbox


class TestCancelWaitRequestHandlerSuccess(TestCancelWaitRequestHandler):
    """成功取消场景测试"""

    def test_handle_success(
        self,
        handler,
        mock_wait_request_repo,
        mock_mailbox_repo,
        pending_wait_request,
        occupied_mailbox,
    ):
        """测试成功取消等待请求 (AC1)"""
        # 设置 mock 返回值
        mock_wait_request_repo.get_by_id.return_value = pending_wait_request
        mock_mailbox_repo.get_by_id.return_value = occupied_mailbox

        # 创建命令
        command = CancelWaitRequestCommand(request_id=pending_wait_request.id)

        # 执行
        result = handler.handle(command)

        # 验证结果
        assert result.success is True
        assert result.message == "Wait request cancelled successfully"
        assert result.error_code is None
        assert result.current_status is None

        # 验证等待请求被取消
        pending_wait_request.cancel.assert_called_once()
        mock_wait_request_repo.update.assert_called_once_with(pending_wait_request)

        # 验证邮箱被释放
        occupied_mailbox.release.assert_called_once()
        mock_mailbox_repo.update.assert_called_once_with(occupied_mailbox)

    def test_handle_success_with_already_released_mailbox(
        self,
        handler,
        mock_wait_request_repo,
        mock_mailbox_repo,
        pending_wait_request,
        available_mailbox,
    ):
        """测试取消时邮箱已释放的情况"""
        # 设置 mock 返回值
        mock_wait_request_repo.get_by_id.return_value = pending_wait_request
        mock_mailbox_repo.get_by_id.return_value = available_mailbox

        # 创建命令
        command = CancelWaitRequestCommand(request_id=pending_wait_request.id)

        # 执行
        result = handler.handle(command)

        # 验证结果成功
        assert result.success is True

        # 验证等待请求被取消
        pending_wait_request.cancel.assert_called_once()

        # 验证邮箱没有被释放（因为已经是可用状态）
        available_mailbox.release.assert_not_called()


class TestCancelWaitRequestHandlerNotFound(TestCancelWaitRequestHandler):
    """请求不存在场景测试"""

    def test_handle_not_found(
        self, handler, mock_wait_request_repo, mock_mailbox_repo
    ):
        """测试请求不存在返回 404 (AC3)"""
        # 设置 mock 返回 None
        mock_wait_request_repo.get_by_id.return_value = None

        # 创建命令
        nonexistent_id = uuid4()
        command = CancelWaitRequestCommand(request_id=nonexistent_id)

        # 执行
        result = handler.handle(command)

        # 验证
        assert result.success is False
        assert result.message == "Request not found"
        assert result.error_code == "NOT_FOUND"
        assert result.current_status is None

        # 验证没有尝试更新
        mock_wait_request_repo.update.assert_not_called()
        mock_mailbox_repo.get_by_id.assert_not_called()


class TestCancelWaitRequestHandlerAlreadyTerminal(TestCancelWaitRequestHandler):
    """请求已终止场景测试"""

    def test_handle_completed_request(
        self,
        handler,
        mock_wait_request_repo,
        mock_mailbox_repo,
        completed_wait_request,
    ):
        """测试取消已完成的请求返回 400 (AC2)"""
        # 设置 mock 返回已完成的请求
        mock_wait_request_repo.get_by_id.return_value = completed_wait_request

        # 创建命令
        command = CancelWaitRequestCommand(request_id=completed_wait_request.id)

        # 执行
        result = handler.handle(command)

        # 验证
        assert result.success is False
        assert result.message == "Request cannot be cancelled"
        assert result.error_code == "ALREADY_TERMINAL"
        assert result.current_status == "completed"

        # 验证没有尝试取消
        completed_wait_request.cancel.assert_not_called()
        mock_wait_request_repo.update.assert_not_called()
        mock_mailbox_repo.get_by_id.assert_not_called()

    def test_handle_cancelled_request(
        self,
        handler,
        mock_wait_request_repo,
        mock_mailbox_repo,
        cancelled_wait_request,
    ):
        """测试取消已取消的请求返回 400 (AC2)"""
        # 设置 mock 返回已取消的请求
        mock_wait_request_repo.get_by_id.return_value = cancelled_wait_request

        # 创建命令
        command = CancelWaitRequestCommand(request_id=cancelled_wait_request.id)

        # 执行
        result = handler.handle(command)

        # 验证
        assert result.success is False
        assert result.message == "Request cannot be cancelled"
        assert result.error_code == "ALREADY_TERMINAL"
        assert result.current_status == "cancelled"

        # 验证没有尝试取消
        cancelled_wait_request.cancel.assert_not_called()

    def test_handle_failed_request(
        self, handler, mock_wait_request_repo, mock_mailbox_repo
    ):
        """测试取消已失败的请求返回 400 (AC2)"""
        # 创建一个 FAILED 状态的等待请求
        failed_request = Mock(spec=WaitRequest)
        failed_request.id = uuid4()
        failed_request.status = WaitRequestStatus.FAILED
        failed_request.is_pending = False

        mock_wait_request_repo.get_by_id.return_value = failed_request

        # 创建命令
        command = CancelWaitRequestCommand(request_id=failed_request.id)

        # 执行
        result = handler.handle(command)

        # 验证
        assert result.success is False
        assert result.error_code == "ALREADY_TERMINAL"
        assert result.current_status == "failed"


class TestCancelWaitRequestHandlerEdgeCases(TestCancelWaitRequestHandler):
    """边界情况测试"""

    def test_handle_mailbox_not_found_after_cancel(
        self,
        handler,
        mock_wait_request_repo,
        mock_mailbox_repo,
        pending_wait_request,
    ):
        """测试取消后找不到邮箱的情况（仍然成功）"""
        # 设置 mock 返回值
        mock_wait_request_repo.get_by_id.return_value = pending_wait_request
        mock_mailbox_repo.get_by_id.return_value = None

        # 创建命令
        command = CancelWaitRequestCommand(request_id=pending_wait_request.id)

        # 执行
        result = handler.handle(command)

        # 验证结果成功（邮箱释放失败不影响取消操作）
        assert result.success is True

        # 验证等待请求被取消
        pending_wait_request.cancel.assert_called_once()
        mock_wait_request_repo.update.assert_called_once_with(pending_wait_request)

    def test_handle_mailbox_release_exception(
        self,
        handler,
        mock_wait_request_repo,
        mock_mailbox_repo,
        pending_wait_request,
        occupied_mailbox,
    ):
        """测试邮箱释放抛出异常的情况（仍然成功）"""
        # 设置 mock 返回值
        mock_wait_request_repo.get_by_id.return_value = pending_wait_request
        mock_mailbox_repo.get_by_id.return_value = occupied_mailbox
        occupied_mailbox.release.side_effect = Exception("Release failed")

        # 创建命令
        command = CancelWaitRequestCommand(request_id=pending_wait_request.id)

        # 执行
        result = handler.handle(command)

        # 验证结果成功（邮箱释放失败不影响取消操作）
        assert result.success is True

        # 验证等待请求被取消
        pending_wait_request.cancel.assert_called_once()
