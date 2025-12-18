"""邮件与请求匹配服务"""

from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID
import logging

from domain.mail.entities.email import Email
from domain.mail.repositories.email_repository import EmailRepository
from domain.verification.entities.wait_request import WaitRequest
from domain.verification.repositories.wait_request_repository import WaitRequestRepository
from domain.mailbox.repositories.mailbox_account_repository import MailboxAccountRepository
from application.ai.services.ai_extraction_service import AiExtractionService
from application.verification.services.webhook_notification_service import (
    WebhookNotificationService,
)


@dataclass
class MatchResult:
    """匹配结果

    Attributes:
        matched: 是否匹配到等待请求
        wait_request_id: 匹配的等待请求 ID
        extraction_type: 提取类型（code/link）
        extraction_value: 提取的值（验证码或链接）
        callback_success: Webhook 回调是否成功
        callback_error: Webhook 回调错误信息
        message: 结果消息
    """

    matched: bool
    wait_request_id: Optional[UUID] = None
    extraction_type: Optional[str] = None
    extraction_value: Optional[str] = None
    callback_success: Optional[bool] = None
    callback_error: Optional[str] = None
    message: str = ""


class MailRequestMatchingService:
    """邮件与请求匹配服务

    核心职责：
    1. 将收到的邮件与等待队列中的请求匹配
    2. 触发 AI 提取验证信息
    3. 更新 WaitRequest 状态

    匹配策略：
    - 通过 email.mailbox_id 获取邮箱信息
    - 使用 mailbox.username 查找 PENDING 状态的 WaitRequest
    - 多个请求时使用智能匹配（service_name）+ FIFO fallback
    """

    def __init__(
        self,
        email_repo: EmailRepository,
        wait_request_repo: WaitRequestRepository,
        mailbox_repo: MailboxAccountRepository,
        ai_service: AiExtractionService,
        webhook_service: Optional[WebhookNotificationService] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """初始化匹配服务

        Args:
            email_repo: 邮件仓储
            wait_request_repo: 等待请求仓储
            mailbox_repo: 邮箱账号仓储
            ai_service: AI 提取服务
            webhook_service: Webhook 通知服务（可选）
            logger: 日志记录器
        """
        self._email_repo = email_repo
        self._wait_request_repo = wait_request_repo
        self._mailbox_repo = mailbox_repo
        self._ai_service = ai_service
        self._webhook_service = webhook_service
        self._logger = logger or logging.getLogger(__name__)

    def process_email(self, email: Email) -> MatchResult:
        """处理邮件，匹配等待请求并提取验证信息

        完整流程：
        1. 获取邮箱账号信息
        2. 查找匹配的等待请求
        3. 触发 AI 提取
        4. 持久化 Email 的 is_processed 状态
        5. 更新 WaitRequest 状态

        Args:
            email: 待处理的邮件实体

        Returns:
            MatchResult 包含匹配和提取结果
        """
        # 1. 获取邮箱账号信息
        mailbox = self._mailbox_repo.get_by_id(email.mailbox_id)
        if mailbox is None:
            self._logger.warning(f"Mailbox not found for email {email.id}")
            return MatchResult(matched=False, message="Mailbox not found")

        # 2. 查找匹配的等待请求
        wait_request = self._find_matching_request(mailbox.username, email)
        if wait_request is None:
            self._logger.debug(
                f"No pending request found for email to {mailbox.username}"
            )
            return MatchResult(
                matched=False,
                message=f"No pending request for {mailbox.username}",
            )

        # 3. 触发 AI 提取
        extraction_result = self._ai_service.unified_extract_from_email(
            email, mark_as_processed=True
        )

        # 4. 持久化 Email 的 is_processed 状态（关键！）
        self._email_repo.update(email)

        # 5. 更新 WaitRequest
        if extraction_result.is_successful:
            wait_request.complete(extraction_result.value)
            self._wait_request_repo.update(wait_request)
            self._logger.info(
                f"Matched email {email.id} to request {wait_request.id}, "
                f"extracted {extraction_result.type.value}: {extraction_result.value}"
            )

            # 6. 发送 Webhook 通知
            callback_success = None
            callback_error = None
            if self._webhook_service is not None:
                notification_result = self._webhook_service.notify(
                    wait_request=wait_request,
                    extraction_type=extraction_result.type.value,
                    extraction_value=extraction_result.value,
                    received_at=email.received_at,
                )
                callback_success = notification_result.success
                callback_error = (
                    notification_result.error_message
                    if not notification_result.success
                    else None
                )

            return MatchResult(
                matched=True,
                wait_request_id=wait_request.id,
                extraction_type=extraction_result.type.value,
                extraction_value=extraction_result.value,
                callback_success=callback_success,
                callback_error=callback_error,
                message="Successfully matched, extracted, and notified"
                if callback_success
                else "Successfully matched and extracted",
            )
        else:
            self._logger.warning(
                f"AI extraction failed for email {email.id}, "
                f"request {wait_request.id} remains pending"
            )
            return MatchResult(
                matched=True,
                wait_request_id=wait_request.id,
                message="Matched but extraction failed",
            )

    def _find_matching_request(
        self, email_address: str, email: Email
    ) -> Optional[WaitRequest]:
        """查找匹配的等待请求

        智能匹配策略：
        1. 按邮箱地址获取所有 PENDING 请求
        2. 如果只有一个，直接返回
        3. 如果有多个，尝试通过发件人/主题智能匹配
        4. 如果无法智能匹配，返回最早创建的（FIFO）

        Args:
            email_address: 邮箱地址
            email: 邮件实体（用于智能匹配）

        Returns:
            匹配的等待请求，如果不存在返回 None
        """
        # 尝试获取单个请求（最常见场景）
        single_request = self._wait_request_repo.get_pending_by_email(email_address)
        if single_request:
            # 检查是否有多个请求
            all_pending = self._wait_request_repo.get_all_pending_by_email(
                email_address
            )
            if len(all_pending) == 1:
                return single_request
            # 有多个请求，需要智能匹配
            return self._smart_match(all_pending, email)

        return None

    def _smart_match(
        self, pending_requests: List[WaitRequest], email: Email
    ) -> WaitRequest:
        """智能匹配：根据邮件内容匹配对应的 service

        匹配策略：
        1. 检查发件人地址是否包含 service 名称
        2. 检查邮件主题是否包含 service 名称
        3. 如果都不匹配，返回最早创建的请求（FIFO）

        Args:
            pending_requests: PENDING 状态的等待请求列表
            email: 邮件实体

        Returns:
            匹配的等待请求
        """
        email_from = email.from_address.lower()
        email_subject = email.subject.lower()

        for request in pending_requests:
            service_name = request.service_name.lower()
            if service_name in email_from or service_name in email_subject:
                self._logger.debug(
                    f"Smart matched request {request.id} by service name "
                    f"'{request.service_name}'"
                )
                return request

        # Fallback: FIFO (按创建时间，最早的优先)
        oldest_request = min(pending_requests, key=lambda r: r.created_at)
        self._logger.debug(
            f"FIFO fallback: matched oldest request {oldest_request.id}"
        )
        return oldest_request
