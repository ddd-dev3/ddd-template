"""注册等待请求命令"""

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from domain.mailbox.repositories.mailbox_account_repository import (
    MailboxAccountRepository,
)
from domain.mailbox.value_objects.mailbox_enums import MailboxStatus
from domain.verification.entities.wait_request import WaitRequest
from domain.verification.repositories.wait_request_repository import (
    WaitRequestRepository,
)


@dataclass
class RegisterWaitRequestCommand:
    """注册等待请求命令

    Attributes:
        email: 邮箱地址
        service_name: 业务服务名称（如 "claude", "openai" 等）
        callback_url: Webhook 回调地址
    """

    email: str
    service_name: str
    callback_url: str


@dataclass
class RegisterWaitRequestResult:
    """命令执行结果

    Attributes:
        success: 是否成功
        request_id: 创建的等待请求 ID（成功时有值）
        message: 结果消息
        error_code: 错误代码（失败时有值）
    """

    success: bool
    request_id: Optional[UUID] = None
    message: str = ""
    error_code: Optional[str] = None


class RegisterWaitRequestHandler:
    """注册等待请求处理器

    处理注册等待请求命令：
    1. 根据 email 查找邮箱账号
    2. 检查邮箱是否可用（未被占用）
    3. 占用邮箱
    4. 创建等待请求
    """

    def __init__(
        self,
        mailbox_repo: MailboxAccountRepository,
        wait_request_repo: WaitRequestRepository,
        logger: Optional[logging.Logger] = None,
    ):
        """
        初始化处理器

        Args:
            mailbox_repo: 邮箱账号仓储
            wait_request_repo: 等待请求仓储
            logger: 日志记录器
        """
        self._mailbox_repo = mailbox_repo
        self._wait_request_repo = wait_request_repo
        self._logger = logger or logging.getLogger(__name__)

    def handle(self, command: RegisterWaitRequestCommand) -> RegisterWaitRequestResult:
        """
        处理注册等待请求命令

        Args:
            command: 注册等待请求命令

        Returns:
            命令执行结果
        """
        self._logger.info(
            f"Processing register wait request: email={command.email}, "
            f"service={command.service_name}"
        )

        # 1. 根据 email 查找邮箱账号
        mailbox = self._mailbox_repo.get_by_username(command.email)
        if mailbox is None:
            self._logger.warning(f"Mailbox not found: {command.email}")
            return RegisterWaitRequestResult(
                success=False,
                message=f"Mailbox not found: {command.email}",
                error_code="MAILBOX_NOT_FOUND",
            )

        # 2. 检查邮箱是否可用
        if mailbox.status == MailboxStatus.OCCUPIED:
            self._logger.warning(
                f"Mailbox already occupied: {command.email} by {mailbox.occupied_by_service}"
            )
            return RegisterWaitRequestResult(
                success=False,
                message=f"Mailbox already occupied by: {mailbox.occupied_by_service}",
                error_code="MAILBOX_OCCUPIED",
            )

        # 3. 占用邮箱
        mailbox.occupy(command.service_name)
        self._mailbox_repo.update(mailbox)

        # 4. 创建等待请求
        wait_request = WaitRequest.create(
            mailbox_id=mailbox.id,
            email=command.email,
            service_name=command.service_name,
            callback_url=command.callback_url,
        )
        self._wait_request_repo.add(wait_request)

        self._logger.info(
            f"Wait request created: request_id={wait_request.id}, "
            f"email={command.email}, service={command.service_name}"
        )

        return RegisterWaitRequestResult(
            success=True,
            request_id=wait_request.id,
            message="Wait request created successfully",
        )
