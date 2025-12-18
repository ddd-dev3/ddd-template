"""邮箱值对象模块"""

from domain.mailbox.value_objects.mailbox_enums import MailboxType, MailboxStatus
from domain.mailbox.value_objects.imap_config import ImapConfig
from domain.mailbox.value_objects.encrypted_password import EncryptedPassword

__all__ = [
    "MailboxType",
    "MailboxStatus",
    "ImapConfig",
    "EncryptedPassword",
]
