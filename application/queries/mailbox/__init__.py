"""Mailbox queries package"""

from application.queries.mailbox.list_mailbox_accounts import (
    ListMailboxAccountsQuery,
    ListMailboxAccountsResult,
    MailboxAccountItem,
    PaginationInfo,
)

__all__ = [
    "ListMailboxAccountsQuery",
    "ListMailboxAccountsResult",
    "MailboxAccountItem",
    "PaginationInfo",
]
