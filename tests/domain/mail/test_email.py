"""Email 实体单元测试"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID

from domain.mail.entities.email import Email
from domain.common.exceptions import InvalidOperationException


class TestEmailCreate:
    """Email.create() 工厂方法测试"""

    def test_create_email_with_required_fields(self):
        """测试使用必需字段创建邮件"""
        mailbox_id = uuid4()
        message_id = "<test123@example.com>"
        from_address = "sender@example.com"
        subject = "Test Email"
        received_at = datetime.now(timezone.utc)

        email = Email.create(
            mailbox_id=mailbox_id,
            message_id=message_id,
            from_address=from_address,
            subject=subject,
            received_at=received_at,
        )

        assert email.mailbox_id == mailbox_id
        assert email.message_id == message_id
        assert email.from_address == from_address
        assert email.subject == subject
        assert email.received_at == received_at
        assert email.is_processed is False
        assert email.body_text is None
        assert email.body_html is None

    def test_create_email_with_text_body(self):
        """测试创建包含纯文本正文的邮件"""
        mailbox_id = uuid4()
        body_text = "This is plain text content"

        email = Email.create(
            mailbox_id=mailbox_id,
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Test",
            received_at=datetime.now(timezone.utc),
            body_text=body_text,
        )

        assert email.body_text == body_text
        assert email.has_text_body is True
        assert email.has_html_body is False

    def test_create_email_with_html_body(self):
        """测试创建包含 HTML 正文的邮件"""
        mailbox_id = uuid4()
        body_html = "<html><body><p>HTML content</p></body></html>"

        email = Email.create(
            mailbox_id=mailbox_id,
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Test",
            received_at=datetime.now(timezone.utc),
            body_html=body_html,
        )

        assert email.body_html == body_html
        assert email.has_html_body is True
        assert email.has_text_body is False

    def test_create_email_with_both_bodies(self):
        """测试创建同时包含纯文本和 HTML 正文的邮件"""
        mailbox_id = uuid4()
        body_text = "Plain text"
        body_html = "<p>HTML</p>"

        email = Email.create(
            mailbox_id=mailbox_id,
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Test",
            received_at=datetime.now(timezone.utc),
            body_text=body_text,
            body_html=body_html,
        )

        assert email.body_text == body_text
        assert email.body_html == body_html
        assert email.has_text_body is True
        assert email.has_html_body is True

    def test_create_email_with_custom_id(self):
        """测试使用自定义 ID 创建邮件"""
        custom_id = uuid4()
        mailbox_id = uuid4()

        email = Email.create(
            mailbox_id=mailbox_id,
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Test",
            received_at=datetime.now(timezone.utc),
            id=custom_id,
        )

        assert email.id == custom_id


class TestEmailValidation:
    """Email 验证测试"""

    def test_create_email_without_mailbox_id_raises_exception(self):
        """测试缺少 mailbox_id 时抛出异常"""
        with pytest.raises(InvalidOperationException) as exc_info:
            Email.create(
                mailbox_id=None,  # type: ignore
                message_id="<test@example.com>",
                from_address="sender@example.com",
                subject="Test",
                received_at=datetime.now(timezone.utc),
            )

        assert "Mailbox ID cannot be None" in str(exc_info.value)

    def test_create_email_without_message_id_raises_exception(self):
        """测试缺少 message_id 时抛出异常"""
        with pytest.raises(InvalidOperationException) as exc_info:
            Email.create(
                mailbox_id=uuid4(),
                message_id="",
                from_address="sender@example.com",
                subject="Test",
                received_at=datetime.now(timezone.utc),
            )

        assert "Message ID cannot be empty" in str(exc_info.value)


class TestEmailMarkAsProcessed:
    """Email.mark_as_processed() 测试"""

    def test_mark_as_processed_success(self):
        """测试成功标记邮件为已处理"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Test",
            received_at=datetime.now(timezone.utc),
        )

        assert email.is_processed is False

        email.mark_as_processed()

        assert email.is_processed is True
        assert email.updated_at is not None

    def test_mark_as_processed_twice_raises_exception(self):
        """测试重复标记已处理抛出异常"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Test",
            received_at=datetime.now(timezone.utc),
        )

        email.mark_as_processed()

        with pytest.raises(InvalidOperationException) as exc_info:
            email.mark_as_processed()

        assert "already been processed" in str(exc_info.value)


class TestEmailBody:
    """Email.body 属性测试"""

    def test_body_returns_text_when_available(self):
        """测试优先返回纯文本正文"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Test",
            received_at=datetime.now(timezone.utc),
            body_text="Plain text",
            body_html="<p>HTML</p>",
        )

        assert email.body == "Plain text"

    def test_body_returns_html_when_no_text(self):
        """测试没有纯文本时返回 HTML"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Test",
            received_at=datetime.now(timezone.utc),
            body_html="<p>HTML only</p>",
        )

        assert email.body == "<p>HTML only</p>"

    def test_body_returns_empty_when_no_content(self):
        """测试没有内容时返回空字符串"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Test",
            received_at=datetime.now(timezone.utc),
        )

        assert email.body == ""
