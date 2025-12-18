"""IMAP 连接验证服务接口"""

from abc import ABC, abstractmethod

from domain.mailbox.value_objects.imap_config import ImapConfig


class ImapConnectionValidator(ABC):
    """
    IMAP 连接验证服务接口

    定义 IMAP 连接验证的契约，具体实现在基础设施层。
    """

    @abstractmethod
    def validate(self, config: ImapConfig, username: str, password: str) -> bool:
        """
        验证 IMAP 连接

        执行以下验证步骤：
        1. 建立 SSL/TLS 连接到 IMAP 服务器
        2. 使用提供的凭证进行登录验证
        3. 选择 INBOX 验证访问权限

        Args:
            config: IMAP 服务器配置
            username: 邮箱用户名
            password: 邮箱密码（明文）

        Returns:
            True 如果连接验证成功

        Raises:
            ImapConnectionException: 如果连接失败
            ImapAuthenticationException: 如果认证失败
        """
        raise NotImplementedError
