"""Tests for GetCodeHandler"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from application.queries.verification.get_code import GetCodeQuery
from application.handlers.verification.get_code_handler import (
    CodeResult,
    GetCodeHandler,
)
from domain.verification.entities.wait_request import WaitRequest
from domain.verification.value_objects.wait_request_status import WaitRequestStatus


class TestGetCodeHandlerNotFound:
    """GetCodeHandler 未找到请求测试"""

    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        """创建 Mock 仓储"""
        repo = MagicMock()
        repo.get_by_id.return_value = None
        return repo

    def test_returns_not_found_when_request_not_exists(self, mock_repo: MagicMock):
        """测试请求不存在时返回 not_found"""
        handler = GetCodeHandler(wait_request_repo=mock_repo)
        query = GetCodeQuery(request_id=uuid4())

        result = handler.handle(query)

        assert result.found is False
        assert result.status == "not_found"
        assert result.data is None
        assert result.message is None

    def test_calls_repository_with_correct_id(self, mock_repo: MagicMock):
        """测试使用正确的 ID 调用仓储"""
        handler = GetCodeHandler(wait_request_repo=mock_repo)
        request_id = uuid4()
        query = GetCodeQuery(request_id=request_id)

        handler.handle(query)

        mock_repo.get_by_id.assert_called_once_with(request_id)


class TestGetCodeHandlerCompleted:
    """GetCodeHandler 已完成请求测试"""

    @pytest.fixture
    def completed_request(self) -> WaitRequest:
        """创建已完成的等待请求"""
        request = WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/webhook",
        )
        request.complete("123456")
        return request

    @pytest.fixture
    def mock_repo(self, completed_request: WaitRequest) -> MagicMock:
        """创建 Mock 仓储"""
        repo = MagicMock()
        repo.get_by_id.return_value = completed_request
        return repo

    def test_returns_completed_status(
        self, mock_repo: MagicMock, completed_request: WaitRequest
    ):
        """测试返回 completed 状态"""
        handler = GetCodeHandler(wait_request_repo=mock_repo)
        query = GetCodeQuery(request_id=completed_request.id)

        result = handler.handle(query)

        assert result.found is True
        assert result.status == "completed"

    def test_returns_correct_data(
        self, mock_repo: MagicMock, completed_request: WaitRequest
    ):
        """测试返回正确的数据"""
        handler = GetCodeHandler(wait_request_repo=mock_repo)
        query = GetCodeQuery(request_id=completed_request.id)

        result = handler.handle(query)

        assert result.data is not None
        assert result.data["request_id"] == str(completed_request.id)
        assert result.data["type"] == "code"
        assert result.data["value"] == "123456"
        assert result.data["email"] == "test@example.com"
        assert result.data["service"] == "claude"
        assert result.data["received_at"] is not None

    def test_detects_code_type(self, mock_repo: MagicMock):
        """测试检测 code 类型"""
        request = WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/webhook",
        )
        request.complete("ABC123")
        mock_repo.get_by_id.return_value = request

        handler = GetCodeHandler(wait_request_repo=mock_repo)
        query = GetCodeQuery(request_id=request.id)

        result = handler.handle(query)

        assert result.data["type"] == "code"

    def test_detects_link_type_https(self, mock_repo: MagicMock):
        """测试检测 HTTPS link 类型"""
        request = WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/webhook",
        )
        request.complete("https://verify.example.com/confirm?token=abc123")
        mock_repo.get_by_id.return_value = request

        handler = GetCodeHandler(wait_request_repo=mock_repo)
        query = GetCodeQuery(request_id=request.id)

        result = handler.handle(query)

        assert result.data["type"] == "link"

    def test_detects_link_type_http(self, mock_repo: MagicMock):
        """测试检测 HTTP link 类型"""
        request = WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/webhook",
        )
        request.complete("http://verify.example.com/confirm?token=abc123")
        mock_repo.get_by_id.return_value = request

        handler = GetCodeHandler(wait_request_repo=mock_repo)
        query = GetCodeQuery(request_id=request.id)

        result = handler.handle(query)

        assert result.data["type"] == "link"


class TestGetCodeHandlerPending:
    """GetCodeHandler 等待中请求测试"""

    @pytest.fixture
    def pending_request(self) -> WaitRequest:
        """创建等待中的请求"""
        return WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/webhook",
        )

    @pytest.fixture
    def mock_repo(self, pending_request: WaitRequest) -> MagicMock:
        """创建 Mock 仓储"""
        repo = MagicMock()
        repo.get_by_id.return_value = pending_request
        return repo

    def test_returns_pending_status(
        self, mock_repo: MagicMock, pending_request: WaitRequest
    ):
        """测试返回 pending 状态"""
        handler = GetCodeHandler(wait_request_repo=mock_repo)
        query = GetCodeQuery(request_id=pending_request.id)

        result = handler.handle(query)

        assert result.found is True
        assert result.status == "pending"

    def test_returns_pending_message(
        self, mock_repo: MagicMock, pending_request: WaitRequest
    ):
        """测试返回等待中消息"""
        handler = GetCodeHandler(wait_request_repo=mock_repo)
        query = GetCodeQuery(request_id=pending_request.id)

        result = handler.handle(query)

        assert result.message == "正在等待验证邮件"
        assert result.data is None


class TestGetCodeHandlerCancelled:
    """GetCodeHandler 已取消请求测试"""

    @pytest.fixture
    def cancelled_request(self) -> WaitRequest:
        """创建已取消的请求"""
        request = WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/webhook",
        )
        request.cancel()
        return request

    @pytest.fixture
    def mock_repo(self, cancelled_request: WaitRequest) -> MagicMock:
        """创建 Mock 仓储"""
        repo = MagicMock()
        repo.get_by_id.return_value = cancelled_request
        return repo

    def test_returns_cancelled_status(
        self, mock_repo: MagicMock, cancelled_request: WaitRequest
    ):
        """测试返回 cancelled 状态"""
        handler = GetCodeHandler(wait_request_repo=mock_repo)
        query = GetCodeQuery(request_id=cancelled_request.id)

        result = handler.handle(query)

        assert result.found is True
        assert result.status == "cancelled"


class TestGetCodeHandlerFailed:
    """GetCodeHandler 已失败请求测试"""

    @pytest.fixture
    def failed_request(self) -> WaitRequest:
        """创建已失败的请求"""
        request = WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/webhook",
        )
        request.fail("Webhook callback failed after 3 retries")
        return request

    @pytest.fixture
    def mock_repo(self, failed_request: WaitRequest) -> MagicMock:
        """创建 Mock 仓储"""
        repo = MagicMock()
        repo.get_by_id.return_value = failed_request
        return repo

    def test_returns_failed_status(
        self, mock_repo: MagicMock, failed_request: WaitRequest
    ):
        """测试返回 failed 状态"""
        handler = GetCodeHandler(wait_request_repo=mock_repo)
        query = GetCodeQuery(request_id=failed_request.id)

        result = handler.handle(query)

        assert result.found is True
        assert result.status == "failed"

    def test_returns_failure_reason(
        self, mock_repo: MagicMock, failed_request: WaitRequest
    ):
        """测试返回失败原因"""
        handler = GetCodeHandler(wait_request_repo=mock_repo)
        query = GetCodeQuery(request_id=failed_request.id)

        result = handler.handle(query)

        assert result.message == "Webhook callback failed after 3 retries"


class TestCodeResult:
    """CodeResult 数据类测试"""

    def test_create_not_found_result(self):
        """测试创建未找到结果"""
        result = CodeResult(found=False, status="not_found")

        assert result.found is False
        assert result.status == "not_found"
        assert result.data is None
        assert result.message is None

    def test_create_completed_result(self):
        """测试创建已完成结果"""
        data = {
            "request_id": "test-id",
            "type": "code",
            "value": "123456",
            "email": "test@example.com",
            "service": "claude",
            "received_at": "2025-01-15T10:30:00",
        }
        result = CodeResult(found=True, status="completed", data=data)

        assert result.found is True
        assert result.status == "completed"
        assert result.data == data
        assert result.message is None

    def test_create_pending_result(self):
        """测试创建等待中结果"""
        result = CodeResult(
            found=True,
            status="pending",
            message="正在等待验证邮件",
        )

        assert result.found is True
        assert result.status == "pending"
        assert result.data is None
        assert result.message == "正在等待验证邮件"

    def test_create_failed_result(self):
        """测试创建失败结果"""
        result = CodeResult(
            found=True,
            status="failed",
            message="Connection timeout",
        )

        assert result.found is True
        assert result.status == "failed"
        assert result.message == "Connection timeout"
