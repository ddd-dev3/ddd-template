"""邮箱相关枚举类型"""

from enum import Enum


class MailboxType(str, Enum):
    """邮箱类型枚举"""

    DOMAIN_CATCHALL = "domain_catchall"
    """域名 Catch-All 邮箱"""

    HOTMAIL = "hotmail"
    """Hotmail/Outlook 邮箱"""


class MailboxStatus(str, Enum):
    """邮箱状态枚举"""

    AVAILABLE = "available"
    """可用状态"""

    OCCUPIED = "occupied"
    """被占用状态"""
