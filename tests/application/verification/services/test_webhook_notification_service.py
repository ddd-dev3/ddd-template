"""Tests for WebhookNotificationService"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from application.verification.services.webhook_notification_service import (
    WebhookNotificationService,
    NotificationResult,
)
from domain.verification.services.webhook_client import WebhookResult
from domain.verification.entities.wait_request import WaitRequest
from domain.verification.value_objects.wait_request_status import WaitRequestStatus


class TestWebhookNotificationServiceSuccess:
    """WebhookNotificationService 成功场景测试"""

    @pytest.fixture
    def mock_webhook_client(self) -> MagicMock:
        """创建 Mock Webhook 客户端"""
        client = MagicMock()
        client.send.return_value = WebhookResult(
            success=True,
            status_code=200,
            retry_count=0,
        )
        return client

    @pytest.fixture
    def mock_wait_request_repo(self) -> MagicMock:
        """创建 Mock 等待请求仓储"""
        return MagicMock()

    @pytest.fixture
    def mock_mailbox_repo(self) -> MagicMock:
        """创建 Mock 邮箱仓储"""
        repo = MagicMock()
        mailbox = MagicMock()
        mailbox.is_occupied = True
        repo.get_by_id.return_value = mailbox
        return repo

    @pytest.fixture
    def wait_request(self) -> WaitRequest:
        """创建测试用等待请求"""
        return WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/webhook",
        )

    def test_successful_notification_returns_success(
        self,
        mock_webhook_client: MagicMock,
        mock_wait_request_repo: MagicMock,
        mock_mailbox_repo: MagicMock,
        wait_request: WaitRequest,
    ):
        """测试成功通知返回成功结果"""
        service = WebhookNotificationService(
            webhook_client=mock_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        result = service.notify(
            wait_request=wait_request,
            extraction_type="code",
            extraction_value="123456",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        assert result.success is True
        assert result.retry_count == 0
        assert result.error_message == ""

    def test_successful_notification_sends_correct_payload(
        self,
        mock_webhook_client: MagicMock,
        mock_wait_request_repo: MagicMock,
        mock_mailbox_repo: MagicMock,
        wait_request: WaitRequest,
    ):
        """测试成功通知发送正确的载荷"""
        service = WebhookNotificationService(
            webhook_client=mock_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        service.notify(
            wait_request=wait_request,
            extraction_type="code",
            extraction_value="123456",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        # 验证调用参数
        mock_webhook_client.send.assert_called_once()
        call_args = mock_webhook_client.send.call_args
        assert call_args.kwargs["url"] == "https://example.com/webhook"

        payload = call_args.kwargs["payload"]
        assert payload["type"] == "code"
        assert payload["value"] == "123456"
        assert payload["email"] == "test@example.com"
        assert payload["service"] == "claude"
        assert payload["received_at"] == "2024-01-15T10:30:00"

    def test_successful_notification_releases_mailbox(
        self,
        mock_webhook_client: MagicMock,
        mock_wait_request_repo: MagicMock,
        mock_mailbox_repo: MagicMock,
        wait_request: WaitRequest,
    ):
        """测试成功通知后释放邮箱"""
        mailbox = MagicMock()
        mailbox.is_occupied = True
        mock_mailbox_repo.get_by_id.return_value = mailbox

        service = WebhookNotificationService(
            webhook_client=mock_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        service.notify(
            wait_request=wait_request,
            extraction_type="code",
            extraction_value="123456",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        # 验证释放邮箱
        mailbox.release.assert_called_once()
        mock_mailbox_repo.update.assert_called_once_with(mailbox)


class TestWebhookNotificationServiceFailure:
    """WebhookNotificationService 失败场景测试"""

    @pytest.fixture
    def mock_failed_webhook_client(self) -> MagicMock:
        """创建失败的 Mock Webhook 客户端"""
        client = MagicMock()
        client.send.return_value = WebhookResult(
            success=False,
            status_code=500,
            retry_count=3,
            error_message="HTTP 500",
        )
        return client

    @pytest.fixture
    def mock_wait_request_repo(self) -> MagicMock:
        """创建 Mock 等待请求仓储"""
        return MagicMock()

    @pytest.fixture
    def mock_mailbox_repo(self) -> MagicMock:
        """创建 Mock 邮箱仓储"""
        repo = MagicMock()
        mailbox = MagicMock()
        mailbox.is_occupied = True
        repo.get_by_id.return_value = mailbox
        return repo

    @pytest.fixture
    def wait_request(self) -> WaitRequest:
        """创建测试用等待请求"""
        return WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/webhook",
        )

    def test_failed_notification_returns_failure(
        self,
        mock_failed_webhook_client: MagicMock,
        mock_wait_request_repo: MagicMock,
        mock_mailbox_repo: MagicMock,
        wait_request: WaitRequest,
    ):
        """测试失败通知返回失败结果"""
        service = WebhookNotificationService(
            webhook_client=mock_failed_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        result = service.notify(
            wait_request=wait_request,
            extraction_type="code",
            extraction_value="123456",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        assert result.success is False
        assert result.retry_count == 3
        assert "HTTP 500" in result.error_message

    def test_failed_notification_marks_request_as_failed(
        self,
        mock_failed_webhook_client: MagicMock,
        mock_wait_request_repo: MagicMock,
        mock_mailbox_repo: MagicMock,
        wait_request: WaitRequest,
    ):
        """测试失败通知标记请求为失败"""
        service = WebhookNotificationService(
            webhook_client=mock_failed_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        service.notify(
            wait_request=wait_request,
            extraction_type="code",
            extraction_value="123456",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        # 验证请求被标记为失败
        assert wait_request.status == WaitRequestStatus.FAILED
        assert "Webhook failed" in wait_request.failure_reason
        mock_wait_request_repo.update.assert_called_once_with(wait_request)

    def test_failed_notification_still_releases_mailbox(
        self,
        mock_failed_webhook_client: MagicMock,
        mock_wait_request_repo: MagicMock,
        mock_mailbox_repo: MagicMock,
        wait_request: WaitRequest,
    ):
        """测试即使通知失败也释放邮箱"""
        mailbox = MagicMock()
        mailbox.is_occupied = True
        mock_mailbox_repo.get_by_id.return_value = mailbox

        service = WebhookNotificationService(
            webhook_client=mock_failed_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        service.notify(
            wait_request=wait_request,
            extraction_type="code",
            extraction_value="123456",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        # 验证即使失败也释放邮箱
        mailbox.release.assert_called_once()


class TestWebhookNotificationServiceMailboxRelease:
    """WebhookNotificationService 邮箱释放测试"""

    @pytest.fixture
    def mock_webhook_client(self) -> MagicMock:
        """创建 Mock Webhook 客户端"""
        client = MagicMock()
        client.send.return_value = WebhookResult(success=True)
        return client

    @pytest.fixture
    def mock_wait_request_repo(self) -> MagicMock:
        """创建 Mock 等待请求仓储"""
        return MagicMock()

    @pytest.fixture
    def wait_request(self) -> WaitRequest:
        """创建测试用等待请求"""
        return WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/webhook",
        )

    def test_mailbox_not_found_logs_warning(
        self,
        mock_webhook_client: MagicMock,
        mock_wait_request_repo: MagicMock,
        wait_request: WaitRequest,
    ):
        """测试邮箱不存在时记录警告"""
        mock_mailbox_repo = MagicMock()
        mock_mailbox_repo.get_by_id.return_value = None

        service = WebhookNotificationService(
            webhook_client=mock_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        # 不应该抛出异常
        result = service.notify(
            wait_request=wait_request,
            extraction_type="code",
            extraction_value="123456",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        assert result.success is True

    def test_already_available_mailbox_not_released(
        self,
        mock_webhook_client: MagicMock,
        mock_wait_request_repo: MagicMock,
        wait_request: WaitRequest,
    ):
        """测试已经可用的邮箱不会再次释放"""
        mock_mailbox_repo = MagicMock()
        mailbox = MagicMock()
        mailbox.is_occupied = False  # 已经可用
        mock_mailbox_repo.get_by_id.return_value = mailbox

        service = WebhookNotificationService(
            webhook_client=mock_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        service.notify(
            wait_request=wait_request,
            extraction_type="code",
            extraction_value="123456",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        # 已经可用的邮箱不应该调用 release
        mailbox.release.assert_not_called()

    def test_release_error_is_handled_gracefully(
        self,
        mock_webhook_client: MagicMock,
        mock_wait_request_repo: MagicMock,
        wait_request: WaitRequest,
    ):
        """测试释放邮箱错误被优雅处理"""
        mock_mailbox_repo = MagicMock()
        mailbox = MagicMock()
        mailbox.is_occupied = True
        mailbox.release.side_effect = Exception("Database error")
        mock_mailbox_repo.get_by_id.return_value = mailbox

        service = WebhookNotificationService(
            webhook_client=mock_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        # 不应该抛出异常
        result = service.notify(
            wait_request=wait_request,
            extraction_type="code",
            extraction_value="123456",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        # 通知仍然成功
        assert result.success is True


class TestWebhookNotificationServiceRetryCount:
    """WebhookNotificationService 重试次数测试"""

    @pytest.fixture
    def mock_wait_request_repo(self) -> MagicMock:
        """创建 Mock 等待请求仓储"""
        return MagicMock()

    @pytest.fixture
    def mock_mailbox_repo(self) -> MagicMock:
        """创建 Mock 邮箱仓储"""
        repo = MagicMock()
        mailbox = MagicMock()
        mailbox.is_occupied = True
        repo.get_by_id.return_value = mailbox
        return repo

    @pytest.fixture
    def wait_request(self) -> WaitRequest:
        """创建测试用等待请求"""
        return WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/webhook",
        )

    def test_retry_count_zero_on_first_success(
        self,
        mock_wait_request_repo: MagicMock,
        mock_mailbox_repo: MagicMock,
        wait_request: WaitRequest,
    ):
        """测试首次成功时重试次数为 0"""
        mock_client = MagicMock()
        mock_client.send.return_value = WebhookResult(
            success=True, retry_count=0
        )

        service = WebhookNotificationService(
            webhook_client=mock_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        result = service.notify(
            wait_request=wait_request,
            extraction_type="code",
            extraction_value="123456",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        assert result.retry_count == 0

    def test_retry_count_one_on_second_success(
        self,
        mock_wait_request_repo: MagicMock,
        mock_mailbox_repo: MagicMock,
        wait_request: WaitRequest,
    ):
        """测试第二次成功时重试次数为 1"""
        mock_client = MagicMock()
        mock_client.send.return_value = WebhookResult(
            success=True, retry_count=1
        )

        service = WebhookNotificationService(
            webhook_client=mock_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        result = service.notify(
            wait_request=wait_request,
            extraction_type="code",
            extraction_value="123456",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        assert result.retry_count == 1

    def test_retry_count_three_on_all_failures(
        self,
        mock_wait_request_repo: MagicMock,
        mock_mailbox_repo: MagicMock,
        wait_request: WaitRequest,
    ):
        """测试所有重试失败时重试次数为 3"""
        mock_client = MagicMock()
        mock_client.send.return_value = WebhookResult(
            success=False,
            retry_count=3,
            error_message="All retries failed",
        )

        service = WebhookNotificationService(
            webhook_client=mock_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        result = service.notify(
            wait_request=wait_request,
            extraction_type="code",
            extraction_value="123456",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        assert result.retry_count == 3


class TestNotificationResult:
    """NotificationResult 数据类测试"""

    def test_success_result(self):
        """测试成功结果"""
        result = NotificationResult(success=True, retry_count=0)

        assert result.success is True
        assert result.retry_count == 0
        assert result.error_message == ""

    def test_failure_result(self):
        """测试失败结果"""
        result = NotificationResult(
            success=False,
            retry_count=3,
            error_message="Connection refused",
        )

        assert result.success is False
        assert result.retry_count == 3
        assert result.error_message == "Connection refused"

    def test_default_values(self):
        """测试默认值"""
        result = NotificationResult(success=True)

        assert result.retry_count == 0
        assert result.error_message == ""
