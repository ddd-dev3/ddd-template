"""邮件应用服务"""

from application.mail.services.mail_polling_service import MailPollingService
from application.mail.services.async_mail_polling_service import AsyncMailPollingService

__all__ = ["MailPollingService", "AsyncMailPollingService"]
