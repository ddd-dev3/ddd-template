"""IMAP 连接验证服务实现"""

import imaplib
import ssl
import socket
from typing import Optional

from domain.mailbox.services.imap_connection_validator import ImapConnectionValidator
from domain.mailbox.value_objects.imap_config import ImapConfig
from domain.common.exceptions import ImapConnectionException, ImapAuthenticationException


class ImapConnectionValidatorImpl(ImapConnectionValidator):
    """
    IMAP 连接验证服务实现

    使用 Python 标准库 imaplib 实现 IMAP 连接验证。
    """

    def __init__(self, timeout: float = 30.0):
        """
        初始化 IMAP 连接验证器

        Args:
            timeout: 连接超时时间（秒），默认 30 秒
        """
        self._timeout = timeout

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
        imap: Optional[imaplib.IMAP4_SSL] = None

        try:
            # 创建 SSL 上下文
            context = ssl.create_default_context()

            if config.use_ssl:
                # 使用 SSL/TLS 连接
                imap = imaplib.IMAP4_SSL(
                    host=config.server,
                    port=config.port,
                    ssl_context=context,
                    timeout=self._timeout,
                )
            else:
                # 使用普通连接（不推荐，但支持）
                imap = imaplib.IMAP4(
                    host=config.server,
                    port=config.port,
                    timeout=self._timeout,
                )

            # 登录验证
            try:
                imap.login(username, password)
            except imaplib.IMAP4.error as e:
                raise ImapAuthenticationException(
                    message=f"IMAP authentication failed: {e}",
                    server=config.server,
                    port=config.port,
                )

            # 选择 INBOX 验证访问权限
            try:
                status, _ = imap.select("INBOX")
                if status != "OK":
                    raise ImapConnectionException(
                        message="Failed to select INBOX",
                        server=config.server,
                        port=config.port,
                    )
            except imaplib.IMAP4.error as e:
                raise ImapConnectionException(
                    message=f"Failed to access INBOX: {e}",
                    server=config.server,
                    port=config.port,
                )

            return True

        except ImapAuthenticationException:
            # 重新抛出认证异常
            raise
        except ImapConnectionException:
            # 重新抛出连接异常
            raise
        except socket.timeout:
            raise ImapConnectionException(
                message=f"Connection timed out after {self._timeout} seconds",
                server=config.server,
                port=config.port,
            )
        except socket.gaierror as e:
            raise ImapConnectionException(
                message=f"Failed to resolve hostname: {e}",
                server=config.server,
                port=config.port,
            )
        except ssl.SSLError as e:
            raise ImapConnectionException(
                message=f"SSL/TLS error: {e}",
                server=config.server,
                port=config.port,
            )
        except ConnectionRefusedError:
            raise ImapConnectionException(
                message="Connection refused by server",
                server=config.server,
                port=config.port,
            )
        except Exception as e:
            raise ImapConnectionException(
                message=f"IMAP connection failed: {e}",
                server=config.server,
                port=config.port,
            )
        finally:
            # 确保连接正确关闭
            if imap is not None:
                try:
                    imap.logout()
                except Exception:
                    pass  # 忽略关闭时的错误
