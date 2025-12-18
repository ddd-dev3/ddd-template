"""添加邮箱账号处理器"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from application.commands.mailbox.add_mailbox_account import AddMailboxAccountCommand
from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mailbox.repositories.mailbox_account_repository import MailboxAccountRepository
from domain.mailbox.services.imap_connection_validator import ImapConnectionValidator
from domain.mailbox.value_objects.imap_config import ImapConfig
from domain.mailbox.value_objects.mailbox_enums import MailboxType
from domain.common.exceptions import (
    DuplicateEntityException,
    ImapConnectionException,
    InvalidOperationException,
)


@dataclass
class AddMailboxAccountResult:
    """
    添加邮箱账号结果

    Attributes:
        success: 是否成功
        mailbox_id: 新创建的邮箱 ID（成功时）
        username: 邮箱用户名
        message: 结果消息
        error_code: 错误代码（失败时）
    """

    success: bool
    mailbox_id: Optional[str] = None
    username: str = ""
    message: str = ""
    error_code: Optional[str] = None


class AddMailboxAccountHandler:
    """
    添加邮箱账号处理器

    业务流程：
    1. 验证请求参数
    2. 检查邮箱是否已存在（重复检测）
    3. 验证 IMAP 连接
    4. 创建邮箱实体（密码加密）
    5. 保存到仓储
    """

    def __init__(
        self,
        repository: MailboxAccountRepository,
        imap_validator: ImapConnectionValidator,
        encryption_key: str,
    ):
        """
        初始化处理器

        Args:
            repository: 邮箱账号仓储
            imap_validator: IMAP 连接验证服务
            encryption_key: 密码加密密钥
        """
        self._repository = repository
        self._imap_validator = imap_validator
        self._encryption_key = encryption_key

    async def handle(self, command: AddMailboxAccountCommand) -> AddMailboxAccountResult:
        """
        处理添加邮箱账号命令

        Args:
            command: 添加邮箱账号命令

        Returns:
            AddMailboxAccountResult 处理结果
        """
        try:
            # 1. 验证邮箱类型
            try:
                mailbox_type = MailboxType(command.mailbox_type)
            except ValueError:
                return AddMailboxAccountResult(
                    success=False,
                    username=command.username,
                    message=f"Invalid mailbox type: {command.mailbox_type}. Must be 'domain_catchall' or 'hotmail'",
                    error_code="INVALID_MAILBOX_TYPE",
                )

            # 2. 检查邮箱是否已存在
            if self._repository.exists_by_username(command.username):
                return AddMailboxAccountResult(
                    success=False,
                    username=command.username,
                    message=f"Mailbox with username '{command.username}' already exists",
                    error_code="DUPLICATE_MAILBOX",
                )

            # 3. 创建 IMAP 配置
            imap_config = ImapConfig(
                server=command.imap_server,
                port=command.imap_port,
                use_ssl=command.use_ssl,
            )

            # 4. 验证 IMAP 连接
            try:
                self._imap_validator.validate(
                    config=imap_config,
                    username=command.username,
                    password=command.password,
                )
            except ImapConnectionException as e:
                return AddMailboxAccountResult(
                    success=False,
                    username=command.username,
                    message=f"IMAP connection failed: {e.message}",
                    error_code=e.code,
                )

            # 5. 创建邮箱实体
            if mailbox_type == MailboxType.DOMAIN_CATCHALL:
                if not command.domain:
                    return AddMailboxAccountResult(
                        success=False,
                        username=command.username,
                        message="Domain is required for domain_catchall mailbox type",
                        error_code="MISSING_DOMAIN",
                    )
                mailbox = MailboxAccount.create_domain_catchall(
                    username=command.username,
                    domain=command.domain,
                    imap_config=imap_config,
                    password=command.password,
                    encryption_key=self._encryption_key,
                )
            else:  # HOTMAIL
                mailbox = MailboxAccount.create_hotmail(
                    username=command.username,
                    imap_config=imap_config,
                    password=command.password,
                    encryption_key=self._encryption_key,
                )

            # 6. 保存到仓储
            self._repository.add(mailbox)

            return AddMailboxAccountResult(
                success=True,
                mailbox_id=str(mailbox.id),
                username=command.username,
                message="Mailbox account created successfully",
            )

        except InvalidOperationException as e:
            return AddMailboxAccountResult(
                success=False,
                username=command.username,
                message=e.message,
                error_code=e.code,
            )
        except Exception as e:
            return AddMailboxAccountResult(
                success=False,
                username=command.username,
                message=f"Unexpected error: {str(e)}",
                error_code="INTERNAL_ERROR",
            )
