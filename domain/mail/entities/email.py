"""邮件实体"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from domain.common.base_entity import BaseEntity
from domain.common.exceptions import InvalidOperationException


@dataclass(eq=False)
class Email(BaseEntity):
    """
    邮件实体

    表示从 IMAP 服务器收取的一封邮件，包含邮件的基本信息和内容。

    Attributes:
        mailbox_id: 关联的邮箱账号 ID
        from_address: 发件人地址
        subject: 邮件主题
        body_text: 纯文本正文（可选）
        body_html: HTML 正文（可选）
        received_at: 邮件接收时间
        message_id: IMAP 邮件唯一标识（Message-ID header）
        is_processed: 是否已处理（提取验证码/链接）
    """

    mailbox_id: UUID = field(default=None)  # type: ignore
    from_address: str = field(default="")
    subject: str = field(default="")
    body_text: Optional[str] = field(default=None)
    body_html: Optional[str] = field(default=None)
    received_at: Optional[datetime] = field(default=None)
    message_id: str = field(default="")
    is_processed: bool = field(default=False)

    def __post_init__(self) -> None:
        """初始化后验证"""
        self._validate()

    def _validate(self) -> None:
        """验证邮件实体的有效性"""
        if self.mailbox_id is None:
            raise InvalidOperationException(
                operation="create_email",
                reason="Mailbox ID cannot be None"
            )

        if not self.message_id:
            raise InvalidOperationException(
                operation="create_email",
                reason="Message ID cannot be empty"
            )

    @classmethod
    def create(
        cls,
        mailbox_id: UUID,
        message_id: str,
        from_address: str,
        subject: str,
        received_at: datetime,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        id: Optional[UUID] = None,
    ) -> "Email":
        """
        工厂方法：创建邮件实体

        Args:
            mailbox_id: 关联的邮箱账号 ID
            message_id: IMAP 邮件唯一标识
            from_address: 发件人地址
            subject: 邮件主题
            received_at: 邮件接收时间
            body_text: 纯文本正文（可选）
            body_html: HTML 正文（可选）
            id: 可选的 UUID，不提供则自动生成

        Returns:
            Email 实例
        """
        kwargs = {
            "mailbox_id": mailbox_id,
            "message_id": message_id,
            "from_address": from_address,
            "subject": subject,
            "received_at": received_at,
            "body_text": body_text,
            "body_html": body_html,
            "is_processed": False,
        }

        if id is not None:
            kwargs["id"] = id

        return cls(**kwargs)

    def mark_as_processed(self) -> None:
        """
        标记邮件为已处理

        Raises:
            InvalidOperationException: 如果邮件已经被处理过
        """
        if self.is_processed:
            raise InvalidOperationException(
                operation="mark_as_processed",
                reason="Email has already been processed"
            )

        self.is_processed = True
        self.update_timestamp()

    @property
    def has_html_body(self) -> bool:
        """检查邮件是否包含 HTML 正文"""
        return self.body_html is not None and len(self.body_html) > 0

    @property
    def has_text_body(self) -> bool:
        """检查邮件是否包含纯文本正文"""
        return self.body_text is not None and len(self.body_text) > 0

    @property
    def body(self) -> str:
        """
        获取邮件正文内容

        优先返回纯文本正文，如果不存在则返回 HTML 正文，
        如果都不存在则返回空字符串。
        """
        if self.has_text_body:
            return self.body_text  # type: ignore
        if self.has_html_body:
            return self.body_html  # type: ignore
        return ""
