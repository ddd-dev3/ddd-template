"""邮箱命令模块"""

from application.commands.mailbox.add_mailbox_account import AddMailboxAccountCommand
from application.commands.mailbox.delete_mailbox_account import (
    DeleteMailboxAccountCommand,
    DeleteMailboxAccountResult,
)

__all__ = [
    "AddMailboxAccountCommand",
    "DeleteMailboxAccountCommand",
    "DeleteMailboxAccountResult",
]
