"""删除邮箱账号命令"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DeleteMailboxAccountCommand:
    """
    删除邮箱账号命令

    Attributes:
        mailbox_id: 要删除的邮箱账号 ID (UUID 字符串)
    """

    mailbox_id: str


@dataclass
class DeleteMailboxAccountResult:
    """
    删除邮箱账号结果

    Attributes:
        success: 是否成功
        mailbox_id: 被删除的邮箱 ID
        username: 被删除的邮箱用户名
        message: 消息
        error_code: 错误码（失败时）
            - MAILBOX_NOT_FOUND: 邮箱不存在
            - MAILBOX_OCCUPIED: 邮箱被占用，无法删除
    """

    success: bool
    mailbox_id: str = ""
    username: str = ""
    message: str = ""
    error_code: Optional[str] = None
