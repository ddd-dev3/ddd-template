"""验证码服务应用层服务模块"""

from application.verification.services.mail_request_matching_service import (
    MailRequestMatchingService,
    MatchResult,
)
from application.verification.services.email_processing_service import (
    EmailProcessingService,
    BatchProcessResult,
)
from application.verification.services.webhook_notification_service import (
    WebhookNotificationService,
    NotificationResult,
)

__all__ = [
    "MailRequestMatchingService",
    "MatchResult",
    "EmailProcessingService",
    "BatchProcessResult",
    "WebhookNotificationService",
    "NotificationResult",
]
