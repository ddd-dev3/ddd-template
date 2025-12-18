"""邮件批量处理服务测试"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from domain.mail.entities.email import Email
from application.verification.services.email_processing_service import (
    EmailProcessingService,
    BatchProcessResult,
)
from application.verification.services.mail_request_matching_service import MatchResult


class TestEmailProcessingService:
    """邮件批量处理服务测试"""

    @pytest.fixture
    def mock_email_repo(self):
        """模拟邮件仓储"""
        return Mock()

    @pytest.fixture
    def mock_matching_service(self):
        """模拟匹配服务"""
        return Mock()

    @pytest.fixture
    def mock_logger(self):
        """模拟日志记录器"""
        return Mock()

    @pytest.fixture
    def service(self, mock_email_repo, mock_matching_service, mock_logger):
        """创建测试服务实例"""
        return EmailProcessingService(
            email_repo=mock_email_repo,
            matching_service=mock_matching_service,
            logger=mock_logger,
        )

    @pytest.fixture
    def sample_emails(self):
        """创建测试邮件列表"""
        return [
            Email(
                id=uuid4(),
                mailbox_id=uuid4(),
                message_id=f"<test{i}@example.com>",
                from_address=f"noreply@service{i}.com",
                subject=f"Verification code {i}",
                body_text=f"Your code is {100000 + i}",
                body_html=f"<p>Your code is {100000 + i}</p>",
                received_at=datetime.now(timezone.utc),
                is_processed=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                version=1,
            )
            for i in range(3)
        ]

    def test_process_unprocessed_emails_all_matched(
        self, service, mock_email_repo, mock_matching_service, sample_emails
    ):
        """测试所有邮件都匹配成功"""
        # Arrange
        mock_email_repo.list_unprocessed.return_value = sample_emails
        wait_request_ids = [uuid4() for _ in sample_emails]

        def create_match_result(email):
            idx = sample_emails.index(email)
            return MatchResult(
                matched=True,
                wait_request_id=wait_request_ids[idx],
                extraction_type="code",
                extraction_value=f"{100000 + idx}",
                message="Success",
            )

        mock_matching_service.process_email.side_effect = create_match_result

        # Act
        result = service.process_unprocessed_emails(limit=100)

        # Assert
        assert result.total_processed == 3
        assert result.matched_count == 3
        assert result.extraction_success_count == 3
        assert len(result.results) == 3
        mock_email_repo.list_unprocessed.assert_called_once_with(limit=100)
        assert mock_matching_service.process_email.call_count == 3

    def test_process_unprocessed_emails_partial_match(
        self, service, mock_email_repo, mock_matching_service, sample_emails
    ):
        """测试部分邮件匹配成功"""
        # Arrange
        mock_email_repo.list_unprocessed.return_value = sample_emails
        wait_request_id = uuid4()

        # First matches with extraction, second matches without extraction, third no match
        mock_matching_service.process_email.side_effect = [
            MatchResult(
                matched=True,
                wait_request_id=wait_request_id,
                extraction_type="code",
                extraction_value="123456",
                message="Success",
            ),
            MatchResult(
                matched=True,
                wait_request_id=uuid4(),
                extraction_type=None,
                extraction_value=None,
                message="Matched but extraction failed",
            ),
            MatchResult(
                matched=False,
                message="No pending request",
            ),
        ]

        # Act
        result = service.process_unprocessed_emails(limit=100)

        # Assert
        assert result.total_processed == 3
        assert result.matched_count == 2
        assert result.extraction_success_count == 1
        assert len(result.results) == 3

    def test_process_unprocessed_emails_no_emails(
        self, service, mock_email_repo, mock_matching_service
    ):
        """测试无待处理邮件"""
        # Arrange
        mock_email_repo.list_unprocessed.return_value = []

        # Act
        result = service.process_unprocessed_emails(limit=100)

        # Assert
        assert result.total_processed == 0
        assert result.matched_count == 0
        assert result.extraction_success_count == 0
        assert len(result.results) == 0
        mock_matching_service.process_email.assert_not_called()

    def test_process_unprocessed_emails_with_exception(
        self, service, mock_email_repo, mock_matching_service, mock_logger, sample_emails
    ):
        """测试处理过程中发生异常"""
        # Arrange
        mock_email_repo.list_unprocessed.return_value = sample_emails
        wait_request_id = uuid4()

        # First succeeds, second raises exception, third succeeds
        mock_matching_service.process_email.side_effect = [
            MatchResult(
                matched=True,
                wait_request_id=wait_request_id,
                extraction_type="code",
                extraction_value="123456",
                message="Success",
            ),
            Exception("Database connection error"),
            MatchResult(
                matched=True,
                wait_request_id=uuid4(),
                extraction_type="link",
                extraction_value="https://example.com/verify",
                message="Success",
            ),
        ]

        # Act
        result = service.process_unprocessed_emails(limit=100)

        # Assert
        assert result.total_processed == 3
        assert result.matched_count == 2  # Two successful matches
        assert result.extraction_success_count == 2
        assert len(result.results) == 3

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        assert "Database connection error" in error_call_args

        # Verify error result was added
        error_result = result.results[1]
        assert error_result.matched is False
        assert "Processing error" in error_result.message

    def test_process_unprocessed_emails_respects_limit(
        self, service, mock_email_repo, mock_matching_service
    ):
        """测试处理数量限制"""
        # Arrange
        mock_email_repo.list_unprocessed.return_value = []

        # Act
        service.process_unprocessed_emails(limit=50)

        # Assert
        mock_email_repo.list_unprocessed.assert_called_once_with(limit=50)

    def test_process_unprocessed_emails_default_limit(
        self, service, mock_email_repo, mock_matching_service
    ):
        """测试默认处理数量限制"""
        # Arrange
        mock_email_repo.list_unprocessed.return_value = []

        # Act
        service.process_unprocessed_emails()

        # Assert
        mock_email_repo.list_unprocessed.assert_called_once_with(limit=100)


class TestBatchProcessResult:
    """批量处理结果测试"""

    def test_result_creation(self):
        """测试结果创建"""
        results = [
            MatchResult(matched=True, message="Success"),
            MatchResult(matched=False, message="No match"),
        ]
        result = BatchProcessResult(
            total_processed=2,
            matched_count=1,
            extraction_success_count=1,
            results=results,
        )

        assert result.total_processed == 2
        assert result.matched_count == 1
        assert result.extraction_success_count == 1
        assert len(result.results) == 2


@pytest.mark.asyncio
class TestEmailProcessingServiceAsync:
    """邮件批量处理服务异步测试"""

    @pytest.fixture
    def mock_email_repo(self):
        """模拟邮件仓储"""
        return Mock()

    @pytest.fixture
    def mock_matching_service(self):
        """模拟匹配服务"""
        return Mock()

    @pytest.fixture
    def service(self, mock_email_repo, mock_matching_service):
        """创建测试服务实例"""
        return EmailProcessingService(
            email_repo=mock_email_repo,
            matching_service=mock_matching_service,
        )

    async def test_process_unprocessed_emails_async(
        self, service, mock_email_repo, mock_matching_service
    ):
        """测试异步批量处理"""
        # Arrange
        email = Email(
            id=uuid4(),
            mailbox_id=uuid4(),
            message_id="<test@example.com>",
            from_address="noreply@github.com",
            subject="Verification",
            body_text="Code: 123456",
            body_html="<p>Code: 123456</p>",
            received_at=datetime.now(timezone.utc),
            is_processed=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
        )
        mock_email_repo.list_unprocessed.return_value = [email]
        mock_matching_service.process_email.return_value = MatchResult(
            matched=True,
            wait_request_id=uuid4(),
            extraction_type="code",
            extraction_value="123456",
            message="Success",
        )

        # Act
        result = await service.process_unprocessed_emails_async(limit=50)

        # Assert
        assert result.total_processed == 1
        assert result.matched_count == 1
        assert result.extraction_success_count == 1
        mock_email_repo.list_unprocessed.assert_called_once_with(limit=50)
