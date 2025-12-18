"""添加邮箱账号命令"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AddMailboxAccountCommand:
    """
    添加邮箱账号命令

    Attributes:
        mailbox_type: 邮箱类型（domain_catchall 或 hotmail）
        username: 邮箱地址/用户名
        password: IMAP 密码（明文，将被加密存储）
        imap_server: IMAP 服务器地址
        imap_port: IMAP 服务器端口，默认 993
        use_ssl: 是否使用 SSL/TLS，默认 True
        domain: 域名（仅 domain_catchall 类型需要）
    """

    mailbox_type: str
    username: str
    password: str
    imap_server: str
    imap_port: int = 993
    use_ssl: bool = True
    domain: Optional[str] = None
