"""邮箱处理器模块"""

from application.handlers.mailbox.add_mailbox_account_handler import (
    AddMailboxAccountHandler,
    AddMailboxAccountResult,
)
from application.handlers.mailbox.list_mailbox_accounts_handler import (
    ListMailboxAccountsHandler,
)
from application.handlers.mailbox.delete_mailbox_account_handler import (
    DeleteMailboxAccountHandler,
)

__all__ = [
    "AddMailboxAccountHandler",
    "AddMailboxAccountResult",
    "ListMailboxAccountsHandler",
    "DeleteMailboxAccountHandler",
]
