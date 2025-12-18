"""解析后的邮件值对象"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.common.base_value_object import BaseValueObject
from domain.mail.value_objects.email_content import EmailContent


@dataclass(frozen=True)
class ParsedEmail(BaseValueObject):
    """
    解析后的邮件值对象

    表示从 IMAP 服务器获取并解析后的邮件数据，
    用于在领域服务和实体之间传递数据。

    Attributes:
        message_id: IMAP 邮件唯一标识（Message-ID header）
        from_address: 发件人地址
        subject: 邮件主题
        content: 邮件内容（文本和 HTML）
        received_at: 邮件接收时间
    """

    message_id: str
    from_address: str
    subject: str
    content: EmailContent
    received_at: Optional[datetime] = None

    @property
    def body_text(self) -> Optional[str]:
        """获取纯文本正文"""
        return self.content.text

    @property
    def body_html(self) -> Optional[str]:
        """获取 HTML 正文"""
        return self.content.html
