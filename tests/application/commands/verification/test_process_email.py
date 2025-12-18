"""处理邮件命令测试"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

from domain.mail.entities.email import Email
from application.commands.verification.process_email import (
    ProcessEmailCommand,
    ProcessEmailResult,
    ProcessEmailHandler,
)
from application.verification.services.mail_request_matching_service import MatchResult


class TestProcessEmailHandler:
    """处理邮件命令处理器测试"""

    @pytest.fixture
    def mock_email_repo(self):
        """模拟邮件仓储"""
        return Mock()

    @pytest.fixture
    def mock_matching_service(self):
        """模拟匹配服务"""
        return Mock()

    @pytest.fixture
    def handler(self, mock_email_repo, mock_matching_service):
        """创建测试处理器实例"""
        return ProcessEmailHandler(
            email_repo=mock_email_repo,
            matching_service=mock_matching_service,
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

    def test_handle_success_with_match(
        self, handler, mock_email_repo, mock_matching_service, sample_email
    ):
        """测试成功处理并匹配邮件"""
        # Arrange
        mock_email_repo.get_by_id.return_value = sample_email
        wait_request_id = uuid4()
        mock_matching_service.process_email.return_value = MatchResult(
            matched=True,
            wait_request_id=wait_request_id,
            extraction_type="code",
            extraction_value="123456",
            message="Successfully matched and extracted",
        )

        command = ProcessEmailCommand(email_id=sample_email.id)

        # Act
        result = handler.handle(command)

        # Assert
        assert result.success is True
        assert result.matched is True
        assert result.wait_request_id == wait_request_id
        assert result.extraction_type == "code"
        assert result.extraction_value == "123456"
        assert result.error_code is None
        mock_matching_service.process_email.assert_called_once_with(sample_email)

    def test_handle_success_no_match(
        self, handler, mock_email_repo, mock_matching_service, sample_email
    ):
        """测试成功处理但无匹配"""
        # Arrange
        mock_email_repo.get_by_id.return_value = sample_email
        mock_matching_service.process_email.return_value = MatchResult(
            matched=False,
            message="No pending request for test@example.com",
        )

        command = ProcessEmailCommand(email_id=sample_email.id)

        # Act
        result = handler.handle(command)

        # Assert
        assert result.success is True
        assert result.matched is False
        assert result.wait_request_id is None
        assert result.error_code is None

    def test_handle_email_not_found(self, handler, mock_email_repo):
        """测试邮件不存在"""
        # Arrange
        email_id = uuid4()
        mock_email_repo.get_by_id.return_value = None

        command = ProcessEmailCommand(email_id=email_id)

        # Act
        result = handler.handle(command)

        # Assert
        assert result.success is False
        assert result.error_code == "EMAIL_NOT_FOUND"
        assert str(email_id) in result.message

    def test_handle_email_already_processed(
        self, handler, mock_email_repo, sample_email
    ):
        """测试邮件已处理"""
        # Arrange
        sample_email.is_processed = True
        mock_email_repo.get_by_id.return_value = sample_email

        command = ProcessEmailCommand(email_id=sample_email.id)

        # Act
        result = handler.handle(command)

        # Assert
        assert result.success is False
        assert result.error_code == "EMAIL_ALREADY_PROCESSED"
        assert "already processed" in result.message


class TestProcessEmailCommand:
    """处理邮件命令测试"""

    def test_command_creation(self):
        """测试命令创建"""
        email_id = uuid4()
        command = ProcessEmailCommand(email_id=email_id)
        assert command.email_id == email_id


class TestProcessEmailResult:
    """处理邮件结果测试"""

    def test_result_default_values(self):
        """测试结果默认值"""
        result = ProcessEmailResult(success=True)
        assert result.success is True
        assert result.matched is False
        assert result.wait_request_id is None
        assert result.extraction_type is None
        assert result.extraction_value is None
        assert result.message == ""
        assert result.error_code is None

    def test_result_with_all_fields(self):
        """测试结果完整字段"""
        wait_request_id = uuid4()
        result = ProcessEmailResult(
            success=True,
            matched=True,
            wait_request_id=wait_request_id,
            extraction_type="code",
            extraction_value="123456",
            message="Success",
            error_code=None,
        )
        assert result.success is True
        assert result.matched is True
        assert result.wait_request_id == wait_request_id
        assert result.extraction_type == "code"
        assert result.extraction_value == "123456"
