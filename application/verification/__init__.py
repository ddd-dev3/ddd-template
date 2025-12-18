"""验证码服务应用层模块"""

from application.verification.services import (
    MailRequestMatchingService,
    MatchResult,
    EmailProcessingService,
    BatchProcessResult,
)

__all__ = [
    "MailRequestMatchingService",
    "MatchResult",
    "EmailProcessingService",
    "BatchProcessResult",
]
