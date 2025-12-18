"""
邮箱账号管理界限上下文

提供邮箱账号的领域模型，包括：
- MailboxAccount 聚合根
- ImapConfig, EncryptedPassword 值对象
- MailboxType, MailboxStatus 枚举
"""

from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mailbox.value_objects.mailbox_enums import MailboxType, MailboxStatus
from domain.mailbox.value_objects.imap_config import ImapConfig
from domain.mailbox.value_objects.encrypted_password import EncryptedPassword

__all__ = [
    "MailboxAccount",
    "MailboxType",
    "MailboxStatus",
    "ImapConfig",
    "EncryptedPassword",
]
