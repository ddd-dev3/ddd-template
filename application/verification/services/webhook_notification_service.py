"""Webhook 通知服务"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID
import logging

from domain.verification.entities.wait_request import WaitRequest
from domain.verification.repositories.wait_request_repository import WaitRequestRepository
from domain.verification.services.webhook_client import WebhookClient
from domain.verification.value_objects.webhook_payload import WebhookPayload
from domain.mailbox.repositories.mailbox_account_repository import MailboxAccountRepository


@dataclass
class NotificationResult:
    """通知结果

    Attributes:
        success: 是否成功
        retry_count: 重试次数
        error_message: 错误信息（失败时）
    """

    success: bool
    retry_count: int = 0
    error_message: str = ""


class WebhookNotificationService:
    """Webhook 通知服务

    负责在验证信息提取成功后发送回调通知。

    职责：
    - 构建 Webhook 载荷
    - 调用 WebhookClient 发送请求
    - 成功时释放邮箱占用
    - 失败时标记请求失败
    """

    def __init__(
        self,
        webhook_client: WebhookClient,
        wait_request_repo: WaitRequestRepository,
        mailbox_repo: MailboxAccountRepository,
        logger: Optional[logging.Logger] = None,
    ):
        """初始化服务

        Args:
            webhook_client: Webhook 客户端
            wait_request_repo: 等待请求仓储
            mailbox_repo: 邮箱账号仓储
            logger: 日志记录器
        """
        self._webhook_client = webhook_client
        self._wait_request_repo = wait_request_repo
        self._mailbox_repo = mailbox_repo
        self._logger = logger or logging.getLogger(__name__)

    def notify(
        self,
        wait_request: WaitRequest,
        extraction_type: str,
        extraction_value: str,
        received_at: datetime,
    ) -> NotificationResult:
        """发送 Webhook 通知

        构建回调载荷并发送到消费者注册的 callback_url。
        成功时释放邮箱占用，失败时标记请求失败。

        Args:
            wait_request: 等待请求实体
            extraction_type: 提取类型 ("code" 或 "link")
            extraction_value: 提取的值
            received_at: 邮件接收时间

        Returns:
            NotificationResult 包含通知结果
        """
        # 1. 构建 payload
        payload = WebhookPayload(
            request_id=wait_request.id,
            type=extraction_type,
            value=extraction_value,
            email=wait_request.email,
            service=wait_request.service_name,
            received_at=received_at,
        )

        self._logger.info(
            f"Sending webhook notification for request {wait_request.id} "
            f"to {wait_request.callback_url}"
        )

        # 2. 发送 Webhook
        result = self._webhook_client.send(
            url=wait_request.callback_url,
            payload=payload.to_dict(),
        )

        # 3. 处理结果
        if result.success:
            # 释放邮箱占用
            self._release_mailbox(wait_request.mailbox_id)
            self._logger.info(
                f"Notification successful for request {wait_request.id} "
                f"(retries: {result.retry_count})"
            )
            return NotificationResult(
                success=True,
                retry_count=result.retry_count,
            )
        else:
            # 标记请求失败（仅当请求仍处于 PENDING 状态时）
            if wait_request.is_pending:
                wait_request.fail(f"Webhook failed: {result.error_message}")
                self._wait_request_repo.update(wait_request)
            else:
                # 请求已经完成，只记录 webhook 失败日志
                self._logger.warning(
                    f"Webhook failed but request {wait_request.id} is already "
                    f"in {wait_request.status.value} state"
                )
            # 释放邮箱占用（即使失败也要释放）
            self._release_mailbox(wait_request.mailbox_id)
            self._logger.error(
                f"Notification failed for request {wait_request.id}: "
                f"{result.error_message} (retries: {result.retry_count})"
            )
            return NotificationResult(
                success=False,
                retry_count=result.retry_count,
                error_message=result.error_message,
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

        # 检查邮箱是否已被占用
        if hasattr(mailbox, "is_occupied") and not mailbox.is_occupied:
            self._logger.debug(f"Mailbox {mailbox_id} is already available")
            return

        try:
            mailbox.release()
            self._mailbox_repo.update(mailbox)
            self._logger.debug(f"Released mailbox {mailbox_id}")
        except Exception as e:
            self._logger.warning(
                f"Failed to release mailbox {mailbox_id}: {e}"
            )
