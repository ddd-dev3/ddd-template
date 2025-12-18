"""取消等待请求命令"""

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from domain.mailbox.repositories.mailbox_account_repository import (
    MailboxAccountRepository,
)
from domain.verification.repositories.wait_request_repository import (
    WaitRequestRepository,
)


@dataclass
class CancelWaitRequestCommand:
    """取消等待请求命令

    Attributes:
        request_id: 等待请求 ID
    """

    request_id: UUID


@dataclass
class CancelWaitRequestResult:
    """命令执行结果

    Attributes:
        success: 是否成功
        message: 结果消息
        error_code: 错误代码（失败时有值）: "NOT_FOUND", "ALREADY_TERMINAL"
        current_status: 当前状态（用于错误响应）
    """

    success: bool
    message: str = ""
    error_code: Optional[str] = None
    current_status: Optional[str] = None


class CancelWaitRequestHandler:
    """取消等待请求处理器

    处理取消等待请求命令：
    1. 根据 request_id 查找等待请求
    2. 检查请求是否处于 PENDING 状态
    3. 取消请求
    4. 释放邮箱占用
    """

    def __init__(
        self,
        wait_request_repo: WaitRequestRepository,
        mailbox_repo: MailboxAccountRepository,
        logger: Optional[logging.Logger] = None,
    ):
        """初始化处理器

        Args:
            wait_request_repo: 等待请求仓储
            mailbox_repo: 邮箱账号仓储
            logger: 日志记录器
        """
        self._wait_request_repo = wait_request_repo
        self._mailbox_repo = mailbox_repo
        self._logger = logger or logging.getLogger(__name__)

    def handle(self, command: CancelWaitRequestCommand) -> CancelWaitRequestResult:
        """处理取消命令

        Args:
            command: 取消等待请求命令

        Returns:
            命令执行结果
        """
        self._logger.info(f"Processing cancel wait request: request_id={command.request_id}")

        # 1. 获取等待请求
        wait_request = self._wait_request_repo.get_by_id(command.request_id)
        if wait_request is None:
            self._logger.warning(f"Request not found: {command.request_id}")
            return CancelWaitRequestResult(
                success=False,
                message="Request not found",
                error_code="NOT_FOUND",
            )

        # 2. 检查是否可取消
        if not wait_request.is_pending:
            self._logger.warning(
                f"Request cannot be cancelled: {command.request_id}, "
                f"current status: {wait_request.status.value}"
            )
            return CancelWaitRequestResult(
                success=False,
                message="Request cannot be cancelled",
                error_code="ALREADY_TERMINAL",
                current_status=wait_request.status.value,
            )

        # 3. 取消请求
        wait_request.cancel()
        self._wait_request_repo.update(wait_request)

        # 4. 释放邮箱占用
        self._release_mailbox(wait_request.mailbox_id)

        self._logger.info(
            f"Wait request cancelled: request_id={command.request_id}, "
            f"email={wait_request.email}, service={wait_request.service_name}"
        )

        return CancelWaitRequestResult(
            success=True,
            message="Wait request cancelled successfully",
        )

    def _release_mailbox(self, mailbox_id: UUID) -> None:
        """释放邮箱占用

        Args:
            mailbox_id: 邮箱 ID
        """
        mailbox = self._mailbox_repo.get_by_id(mailbox_id)
        if mailbox is None:
            self._logger.warning(f"Mailbox {mailbox_id} not found for release")
            return

        if not mailbox.is_occupied:
            self._logger.debug(f"Mailbox {mailbox_id} is already available")
            return

        try:
            mailbox.release()
            self._mailbox_repo.update(mailbox)
            self._logger.debug(f"Released mailbox {mailbox_id}")
        except Exception as e:
            self._logger.warning(f"Failed to release mailbox {mailbox_id}: {e}")
