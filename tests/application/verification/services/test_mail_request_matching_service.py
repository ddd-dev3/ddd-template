"""邮件请求匹配服务测试"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from domain.mail.entities.email import Email
from domain.verification.entities.wait_request import WaitRequest
from domain.verification.value_objects.wait_request_status import WaitRequestStatus
from domain.ai.value_objects.extraction_result import ExtractionResult, ExtractionType
from application.verification.services.mail_request_matching_service import (
    MailRequestMatchingService,
    MatchResult,
)


class TestMailRequestMatchingService:
    """邮件请求匹配服务测试"""

    @pytest.fixture
    def mock_email_repo(self):
        """模拟邮件仓储"""
        return Mock()

    @pytest.fixture
    def mock_wait_request_repo(self):
        """模拟等待请求仓储"""
        return Mock()

    @pytest.fixture
    def mock_mailbox_repo(self):
        """模拟邮箱账号仓储"""
        return Mock()

    @pytest.fixture
    def mock_ai_service(self):
        """模拟 AI 提取服务"""
        return Mock()

    @pytest.fixture
    def service(
        self,
        mock_email_repo,
        mock_wait_request_repo,
        mock_mailbox_repo,
        mock_ai_service,
    ):
        """创建测试服务实例"""
        return MailRequestMatchingService(
            email_repo=mock_email_repo,
            wait_request_repo=mock_wait_request_repo,
            mailbox_repo=mock_mailbox_repo,
            ai_service=mock_ai_service,
        )

    @pytest.fixture
    def sample_email(self):
        """创建测试邮件"""
        return Email(
            id=uuid4(),
            mailbox_id=uuid4(),
            message_id="<test@example.com>",
            from_address="noreply@github.com",
            subject="Your GitHub verification code",
            body_text="Your code is 123456",
            body_html="<p>Your code is 123456</p>",
            received_at=datetime.now(timezone.utc),
            is_processed=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
        )

    @pytest.fixture
    def sample_mailbox(self):
        """创建测试邮箱"""
        mailbox = Mock()
        mailbox.id = uuid4()
        mailbox.username = "test@example.com"
        return mailbox

    @pytest.fixture
    def sample_wait_request(self, sample_mailbox):
        """创建测试等待请求"""
        return WaitRequest(
            id=uuid4(),
            mailbox_id=sample_mailbox.id,
            email="test@example.com",
            service_name="github",
            callback_url="https://api.example.com/callback",
            status=WaitRequestStatus.PENDING,
            extraction_result=None,
            completed_at=None,
            failure_reason=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
        )

    def test_process_email_matches_single_pending_request(
        self,
        service,
        mock_mailbox_repo,
        mock_wait_request_repo,
        mock_ai_service,
        mock_email_repo,
        sample_email,
        sample_mailbox,
        sample_wait_request,
    ):
        """测试成功匹配单个等待请求"""
        # Arrange
        mock_mailbox_repo.get_by_id.return_value = sample_mailbox
        mock_wait_request_repo.get_pending_by_email.return_value = sample_wait_request
        mock_wait_request_repo.get_all_pending_by_email.return_value = [
            sample_wait_request
        ]

        extraction_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        mock_ai_service.unified_extract_from_email.return_value = extraction_result

        # Act
        result = service.process_email(sample_email)

        # Assert
        assert result.matched is True
        assert result.wait_request_id == sample_wait_request.id
        assert result.extraction_type == "code"
        assert result.extraction_value == "123456"
        mock_wait_request_repo.update.assert_called_once()
        mock_email_repo.update.assert_called_once_with(sample_email)

    def test_process_email_no_match_when_mailbox_not_found(
        self,
        service,
        mock_mailbox_repo,
        sample_email,
    ):
        """测试邮箱不存在时返回无匹配"""
        # Arrange
        mock_mailbox_repo.get_by_id.return_value = None

        # Act
        result = service.process_email(sample_email)

        # Assert
        assert result.matched is False
        assert "Mailbox not found" in result.message

    def test_process_email_no_match_when_no_pending_request(
        self,
        service,
        mock_mailbox_repo,
        mock_wait_request_repo,
        sample_email,
        sample_mailbox,
    ):
        """测试无待处理请求时返回无匹配"""
        # Arrange
        mock_mailbox_repo.get_by_id.return_value = sample_mailbox
        mock_wait_request_repo.get_pending_by_email.return_value = None

        # Act
        result = service.process_email(sample_email)

        # Assert
        assert result.matched is False
        assert "No pending request" in result.message

    def test_smart_match_by_service_name_in_from_address(
        self,
        service,
        mock_mailbox_repo,
        mock_wait_request_repo,
        mock_ai_service,
        mock_email_repo,
        sample_email,
        sample_mailbox,
    ):
        """测试通过发件人地址中的服务名智能匹配"""
        # Arrange
        github_request = WaitRequest(
            id=uuid4(),
            mailbox_id=sample_mailbox.id,
            email="test@example.com",
            service_name="github",
            callback_url="https://api.example.com/callback",
            status=WaitRequestStatus.PENDING,
            extraction_result=None,
            completed_at=None,
            failure_reason=None,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
        )
        twitter_request = WaitRequest(
            id=uuid4(),
            mailbox_id=sample_mailbox.id,
            email="test@example.com",
            service_name="twitter",
            callback_url="https://api.example.com/callback",
            status=WaitRequestStatus.PENDING,
            extraction_result=None,
            completed_at=None,
            failure_reason=None,
            created_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
        )

        mock_mailbox_repo.get_by_id.return_value = sample_mailbox
        mock_wait_request_repo.get_pending_by_email.return_value = github_request
        mock_wait_request_repo.get_all_pending_by_email.return_value = [
            github_request,
            twitter_request,
        ]

        extraction_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        mock_ai_service.unified_extract_from_email.return_value = extraction_result

        # Act
        result = service.process_email(sample_email)

        # Assert - Should match github since from_address contains "github"
        assert result.matched is True
        assert result.wait_request_id == github_request.id

    def test_smart_match_by_service_name_in_subject(
        self,
        service,
        mock_mailbox_repo,
        mock_wait_request_repo,
        mock_ai_service,
        mock_email_repo,
        sample_mailbox,
    ):
        """测试通过邮件主题中的服务名智能匹配"""
        # Arrange
        email = Email(
            id=uuid4(),
            mailbox_id=sample_mailbox.id,
            message_id="<test@example.com>",
            from_address="noreply@service.com",  # No service name here
            subject="Your Twitter verification code",  # Service name in subject
            body_text="Your code is 123456",
            body_html="<p>Your code is 123456</p>",
            received_at=datetime.now(timezone.utc),
            is_processed=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
        )

        github_request = WaitRequest(
            id=uuid4(),
            mailbox_id=sample_mailbox.id,
            email="test@example.com",
            service_name="github",
            callback_url="https://api.example.com/callback",
            status=WaitRequestStatus.PENDING,
            extraction_result=None,
            completed_at=None,
            failure_reason=None,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
        )
        twitter_request = WaitRequest(
            id=uuid4(),
            mailbox_id=sample_mailbox.id,
            email="test@example.com",
            service_name="twitter",
            callback_url="https://api.example.com/callback",
            status=WaitRequestStatus.PENDING,
            extraction_result=None,
            completed_at=None,
            failure_reason=None,
            created_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
        )

        mock_mailbox_repo.get_by_id.return_value = sample_mailbox
        mock_wait_request_repo.get_pending_by_email.return_value = github_request
        mock_wait_request_repo.get_all_pending_by_email.return_value = [
            github_request,
            twitter_request,
        ]

        extraction_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        mock_ai_service.unified_extract_from_email.return_value = extraction_result

        # Act
        result = service.process_email(email)

        # Assert - Should match twitter since subject contains "Twitter"
        assert result.matched is True
        assert result.wait_request_id == twitter_request.id

    def test_smart_match_fifo_fallback_when_no_service_match(
        self,
        service,
        mock_mailbox_repo,
        mock_wait_request_repo,
        mock_ai_service,
        mock_email_repo,
        sample_mailbox,
    ):
        """测试无法匹配服务名时使用 FIFO（最早请求优先）"""
        # Arrange
        email = Email(
            id=uuid4(),
            mailbox_id=sample_mailbox.id,
            message_id="<test@example.com>",
            from_address="noreply@unknown.com",  # No service name
            subject="Your verification code",  # No service name
            body_text="Your code is 123456",
            body_html="<p>Your code is 123456</p>",
            received_at=datetime.now(timezone.utc),
            is_processed=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
        )

        # Create requests with different creation times
        older_request = WaitRequest(
            id=uuid4(),
            mailbox_id=sample_mailbox.id,
            email="test@example.com",
            service_name="service_a",
            callback_url="https://api.example.com/callback",
            status=WaitRequestStatus.PENDING,
            extraction_result=None,
            completed_at=None,
            failure_reason=None,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),  # Older
            updated_at=datetime.now(timezone.utc),
            version=1,
        )
        newer_request = WaitRequest(
            id=uuid4(),
            mailbox_id=sample_mailbox.id,
            email="test@example.com",
            service_name="service_b",
            callback_url="https://api.example.com/callback",
            status=WaitRequestStatus.PENDING,
            extraction_result=None,
            completed_at=None,
            failure_reason=None,
            created_at=datetime(2025, 1, 2, tzinfo=timezone.utc),  # Newer
            updated_at=datetime.now(timezone.utc),
            version=1,
        )

        mock_mailbox_repo.get_by_id.return_value = sample_mailbox
        mock_wait_request_repo.get_pending_by_email.return_value = older_request
        mock_wait_request_repo.get_all_pending_by_email.return_value = [
            newer_request,  # Intentionally out of order
            older_request,
        ]

        extraction_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        mock_ai_service.unified_extract_from_email.return_value = extraction_result

        # Act
        result = service.process_email(email)

        # Assert - Should match older request (FIFO)
        assert result.matched is True
        assert result.wait_request_id == older_request.id

    def test_process_email_extraction_failed_keeps_request_pending(
        self,
        service,
        mock_mailbox_repo,
        mock_wait_request_repo,
        mock_ai_service,
        mock_email_repo,
        sample_email,
        sample_mailbox,
        sample_wait_request,
    ):
        """测试提取失败时保持请求为待处理状态"""
        # Arrange
        mock_mailbox_repo.get_by_id.return_value = sample_mailbox
        mock_wait_request_repo.get_pending_by_email.return_value = sample_wait_request
        mock_wait_request_repo.get_all_pending_by_email.return_value = [
            sample_wait_request
        ]

        extraction_result = ExtractionResult(
            type=ExtractionType.UNKNOWN,
            code=None,
            link=None,
            confidence=0.0,
        )
        mock_ai_service.unified_extract_from_email.return_value = extraction_result

        # Act
        result = service.process_email(sample_email)

        # Assert
        assert result.matched is True  # Matched but extraction failed
        assert result.wait_request_id == sample_wait_request.id
        assert result.extraction_value is None
        assert "extraction failed" in result.message
        mock_wait_request_repo.update.assert_not_called()  # Should NOT update request
        mock_email_repo.update.assert_called_once()  # Should still mark email processed

    def test_process_email_persists_email_is_processed(
        self,
        service,
        mock_mailbox_repo,
        mock_wait_request_repo,
        mock_ai_service,
        mock_email_repo,
        sample_email,
        sample_mailbox,
        sample_wait_request,
    ):
        """测试处理后正确持久化邮件的 is_processed 状态"""
        # Arrange
        mock_mailbox_repo.get_by_id.return_value = sample_mailbox
        mock_wait_request_repo.get_pending_by_email.return_value = sample_wait_request
        mock_wait_request_repo.get_all_pending_by_email.return_value = [
            sample_wait_request
        ]

        extraction_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        mock_ai_service.unified_extract_from_email.return_value = extraction_result

        # Act
        service.process_email(sample_email)

        # Assert - Email repo update must be called to persist is_processed
        mock_email_repo.update.assert_called_once_with(sample_email)
