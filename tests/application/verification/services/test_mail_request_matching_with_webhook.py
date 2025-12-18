"""Integration tests for MailRequestMatchingService with Webhook notification"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from application.verification.services.mail_request_matching_service import (
    MailRequestMatchingService,
    MatchResult,
)
from application.verification.services.webhook_notification_service import (
    WebhookNotificationService,
    NotificationResult,
)
from domain.ai.value_objects.extraction_result import ExtractionResult
from domain.ai.value_objects.extraction_type import ExtractionType
from domain.mail.entities.email import Email
from domain.verification.entities.wait_request import WaitRequest
from domain.verification.value_objects.wait_request_status import WaitRequestStatus
from domain.verification.services.webhook_client import WebhookResult
from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mailbox.value_objects.imap_config import ImapConfig


class TestMailRequestMatchingWithWebhook:
    """邮件请求匹配与 Webhook 集成测试"""

    @pytest.fixture
    def mailbox_id(self):
        """创建邮箱 ID"""
        return uuid4()

    @pytest.fixture
    def mock_mailbox(self, mailbox_id):
        """创建 Mock 邮箱"""
        mailbox = MagicMock(spec=MailboxAccount)
        mailbox.id = mailbox_id
        mailbox.username = "test@example.com"
        mailbox.is_occupied = True
        return mailbox

    @pytest.fixture
    def mock_email(self, mailbox_id):
        """创建 Mock 邮件"""
        email = MagicMock(spec=Email)
        email.id = uuid4()
        email.mailbox_id = mailbox_id
        email.from_address = "noreply@claude.ai"
        email.subject = "Your verification code"
        email.received_at = datetime(2024, 1, 15, 10, 30, 0)
        return email

    @pytest.fixture
    def wait_request(self, mailbox_id):
        """创建等待请求"""
        return WaitRequest.create(
            mailbox_id=mailbox_id,
            email="test@example.com",
            service_name="claude",
            callback_url="https://consumer.example.com/webhook",
        )

    @pytest.fixture
    def mock_email_repo(self):
        """创建 Mock 邮件仓储"""
        return MagicMock()

    @pytest.fixture
    def mock_wait_request_repo(self, wait_request):
        """创建 Mock 等待请求仓储"""
        repo = MagicMock()
        repo.get_pending_by_email.return_value = wait_request
        repo.get_all_pending_by_email.return_value = [wait_request]
        return repo

    @pytest.fixture
    def mock_mailbox_repo(self, mock_mailbox):
        """创建 Mock 邮箱仓储"""
        repo = MagicMock()
        repo.get_by_id.return_value = mock_mailbox
        return repo

    @pytest.fixture
    def mock_ai_service(self):
        """创建 Mock AI 提取服务"""
        ai_service = MagicMock()
        ai_service.unified_extract_from_email.return_value = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=1.0,
        )
        return ai_service

    @pytest.fixture
    def mock_webhook_client(self):
        """创建 Mock Webhook 客户端"""
        client = MagicMock()
        client.send.return_value = WebhookResult(
            success=True,
            status_code=200,
            retry_count=0,
        )
        return client

    def test_complete_flow_extraction_to_webhook(
        self,
        mock_email_repo,
        mock_wait_request_repo,
        mock_mailbox_repo,
        mock_ai_service,
        mock_webhook_client,
        mock_email,
        wait_request,
        mock_mailbox,
    ):
        """测试完整流程：提取成功 -> Webhook 回调"""
        # 创建 Webhook 通知服务
        webhook_service = WebhookNotificationService(
            webhook_client=mock_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        # 创建匹配服务（带 Webhook 服务）
        matching_service = MailRequestMatchingService(
            email_repo=mock_email_repo,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
            ai_service=mock_ai_service,
            webhook_service=webhook_service,
        )

        # 处理邮件
        result = matching_service.process_email(mock_email)

        # 验证结果
        assert result.matched is True
        assert result.extraction_type == "code"
        assert result.extraction_value == "123456"
        assert result.callback_success is True
        assert result.callback_error is None

        # 验证 Webhook 被调用
        mock_webhook_client.send.assert_called_once()
        call_kwargs = mock_webhook_client.send.call_args.kwargs
        assert call_kwargs["url"] == "https://consumer.example.com/webhook"

        payload = call_kwargs["payload"]
        assert payload["type"] == "code"
        assert payload["value"] == "123456"
        assert payload["email"] == "test@example.com"
        assert payload["service"] == "claude"

    def test_complete_flow_with_webhook_failure(
        self,
        mock_email_repo,
        mock_wait_request_repo,
        mock_mailbox_repo,
        mock_ai_service,
        mock_email,
        wait_request,
        mock_mailbox,
    ):
        """测试完整流程：提取成功但 Webhook 失败"""
        # 创建失败的 Webhook 客户端
        failed_webhook_client = MagicMock()
        failed_webhook_client.send.return_value = WebhookResult(
            success=False,
            status_code=500,
            retry_count=3,
            error_message="Server error",
        )

        webhook_service = WebhookNotificationService(
            webhook_client=failed_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        matching_service = MailRequestMatchingService(
            email_repo=mock_email_repo,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
            ai_service=mock_ai_service,
            webhook_service=webhook_service,
        )

        result = matching_service.process_email(mock_email)

        # 验证结果：匹配和提取成功，但回调失败
        assert result.matched is True
        assert result.extraction_type == "code"
        assert result.extraction_value == "123456"
        assert result.callback_success is False
        assert "Server error" in result.callback_error

    def test_complete_flow_without_webhook_service(
        self,
        mock_email_repo,
        mock_wait_request_repo,
        mock_mailbox_repo,
        mock_ai_service,
        mock_email,
        wait_request,
    ):
        """测试没有配置 Webhook 服务的流程"""
        # 创建匹配服务（不带 Webhook 服务）
        matching_service = MailRequestMatchingService(
            email_repo=mock_email_repo,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
            ai_service=mock_ai_service,
            webhook_service=None,  # 不配置 Webhook 服务
        )

        result = matching_service.process_email(mock_email)

        # 验证结果：匹配和提取成功，回调状态为 None
        assert result.matched is True
        assert result.extraction_type == "code"
        assert result.extraction_value == "123456"
        assert result.callback_success is None
        assert result.callback_error is None

    def test_extraction_failure_no_webhook_called(
        self,
        mock_email_repo,
        mock_wait_request_repo,
        mock_mailbox_repo,
        mock_webhook_client,
        mock_email,
        wait_request,
        mock_mailbox,
    ):
        """测试提取失败时不调用 Webhook"""
        # 创建失败的 AI 服务
        failed_ai_service = MagicMock()
        failed_ai_service.unified_extract_from_email.return_value = ExtractionResult(
            type=ExtractionType.UNKNOWN,
            confidence=0.0,
        )

        webhook_service = WebhookNotificationService(
            webhook_client=mock_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        matching_service = MailRequestMatchingService(
            email_repo=mock_email_repo,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
            ai_service=failed_ai_service,
            webhook_service=webhook_service,
        )

        result = matching_service.process_email(mock_email)

        # 验证结果：匹配成功但提取失败
        assert result.matched is True
        assert result.extraction_type is None
        assert result.extraction_value is None
        assert result.callback_success is None

        # 验证 Webhook 没有被调用
        mock_webhook_client.send.assert_not_called()

    def test_no_matching_request_no_webhook_called(
        self,
        mock_email_repo,
        mock_mailbox_repo,
        mock_ai_service,
        mock_webhook_client,
        mock_email,
        mock_mailbox,
    ):
        """测试没有匹配请求时不调用 Webhook"""
        # 创建空的等待请求仓储
        empty_wait_request_repo = MagicMock()
        empty_wait_request_repo.get_pending_by_email.return_value = None

        webhook_service = WebhookNotificationService(
            webhook_client=mock_webhook_client,
            wait_request_repo=empty_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        matching_service = MailRequestMatchingService(
            email_repo=mock_email_repo,
            wait_request_repo=empty_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
            ai_service=mock_ai_service,
            webhook_service=webhook_service,
        )

        result = matching_service.process_email(mock_email)

        # 验证结果：没有匹配
        assert result.matched is False

        # 验证 Webhook 没有被调用
        mock_webhook_client.send.assert_not_called()


class TestWebhookPayloadContent:
    """Webhook 载荷内容测试"""

    @pytest.fixture
    def mailbox_id(self):
        return uuid4()

    @pytest.fixture
    def mock_mailbox(self, mailbox_id):
        mailbox = MagicMock(spec=MailboxAccount)
        mailbox.id = mailbox_id
        mailbox.username = "user@domain.com"
        mailbox.is_occupied = True
        return mailbox

    @pytest.fixture
    def mock_email(self, mailbox_id):
        email = MagicMock(spec=Email)
        email.id = uuid4()
        email.mailbox_id = mailbox_id
        email.from_address = "noreply@github.com"
        email.subject = "Verify your email"
        email.received_at = datetime(2024, 3, 20, 14, 45, 30)
        return email

    def test_payload_contains_link_type(
        self,
        mailbox_id,
        mock_mailbox,
        mock_email,
    ):
        """测试载荷包含 link 类型"""
        wait_request = WaitRequest.create(
            mailbox_id=mailbox_id,
            email="user@domain.com",
            service_name="github",
            callback_url="https://api.example.com/callback",
        )

        mock_webhook_client = MagicMock()
        mock_webhook_client.send.return_value = WebhookResult(success=True)

        mock_wait_request_repo = MagicMock()
        mock_wait_request_repo.get_pending_by_email.return_value = wait_request
        mock_wait_request_repo.get_all_pending_by_email.return_value = [wait_request]

        mock_mailbox_repo = MagicMock()
        mock_mailbox_repo.get_by_id.return_value = mock_mailbox

        mock_ai_service = MagicMock()
        mock_ai_service.unified_extract_from_email.return_value = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://github.com/verify?token=abc123",
            confidence=1.0,
        )

        mock_email_repo = MagicMock()

        webhook_service = WebhookNotificationService(
            webhook_client=mock_webhook_client,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
        )

        matching_service = MailRequestMatchingService(
            email_repo=mock_email_repo,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
            ai_service=mock_ai_service,
            webhook_service=webhook_service,
        )

        result = matching_service.process_email(mock_email)

        # 验证 payload 内容
        call_kwargs = mock_webhook_client.send.call_args.kwargs
        payload = call_kwargs["payload"]

        assert payload["type"] == "link"
        assert payload["value"] == "https://github.com/verify?token=abc123"
        assert payload["email"] == "user@domain.com"
        assert payload["service"] == "github"
        assert payload["received_at"] == "2024-03-20T14:45:30"
