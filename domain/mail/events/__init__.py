"""邮件领域事件模块"""

from domain.mail.events.mail_events import MailFetched, MailProcessed

__all__ = ["MailFetched", "MailProcessed"]
