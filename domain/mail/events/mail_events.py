"""邮件领域事件

这些事件由应用层服务在适当时机发布，而非实体层。

使用示例（应用层）:
    from domain.mail.events.mail_events import MailFetched, MailProcessed
    from pyventus import EventLinker

    # 在 MailFetchApplicationService 中：
    async def fetch_emails_for_mailbox(self, mailbox_id: UUID):
        emails = self.imap_service.fetch_new_emails(mailbox)
        for email in emails:
            self.email_repository.add(email)
            # 发布 MailFetched 事件
            await EventLinker.emit(MailFetched(
                aggregate_id=email.id,
                mailbox_id=mailbox.id,
                message_id=email.message_id,
                ...
            ))
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from domain.common.base_event import DomainEvent


@dataclass(frozen=True)
class MailFetched(DomainEvent):
    """
    邮件收取事件

    当新邮件从 IMAP 服务器成功收取并存储时触发。
    应由应用层服务（如 MailFetchApplicationService）在存储邮件后发布。

    Attributes:
        aggregate_id: 邮件实体 ID（Email.id）
        mailbox_id: 关联的邮箱账号 ID
        message_id: IMAP 邮件唯一标识
        from_address: 发件人地址
        subject: 邮件主题
        received_at: 邮件接收时间
    """

    mailbox_id: UUID = None  # type: ignore
    message_id: str = ""
    from_address: str = ""
    subject: str = ""
    received_at: Optional[datetime] = None


@dataclass(frozen=True)
class MailProcessed(DomainEvent):
    """
    邮件处理完成事件

    当邮件被处理（提取验证码/链接）完成时触发。
    应由应用层服务在调用 email.mark_as_processed() 并提取内容后发布。

    Attributes:
        aggregate_id: 邮件实体 ID（Email.id）
        mailbox_id: 关联的邮箱账号 ID
        extraction_type: 提取类型（code/link/unknown）
        extraction_value: 提取的值（验证码或链接）
    """

    mailbox_id: UUID = None  # type: ignore
    extraction_type: str = ""
    extraction_value: Optional[str] = None
