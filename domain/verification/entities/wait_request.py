"""等待请求实体"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from domain.common.base_entity import BaseEntity
from domain.common.exceptions import InvalidStateTransitionException
from domain.verification.value_objects.wait_request_status import WaitRequestStatus


@dataclass(eq=False)
class WaitRequest(BaseEntity):
    """等待请求实体

    表示一个验证码/验证链接等待请求。
    当 API 消费者声明要用某个邮箱注册某服务时创建。

    Attributes:
        mailbox_id: 关联的邮箱账号 ID
        email: 邮箱地址（冗余存储，方便查询）
        service_name: 业务服务名称（如 "claude", "openai" 等）
        callback_url: Webhook 回调地址
        status: 请求状态
        completed_at: 完成时间（仅当状态为 COMPLETED 时有值）
        extraction_result: 提取结果（验证码或链接）
        failure_reason: 失败原因（仅当状态为 FAILED 时有值）
    """

    mailbox_id: UUID = field(default=None)
    email: str = field(default="")
    service_name: str = field(default="")
    callback_url: str = field(default="")
    status: WaitRequestStatus = field(default=WaitRequestStatus.PENDING)
    completed_at: Optional[datetime] = field(default=None)
    extraction_result: Optional[str] = field(default=None)
    failure_reason: Optional[str] = field(default=None)

    @classmethod
    def create(
        cls,
        mailbox_id: UUID,
        email: str,
        service_name: str,
        callback_url: str,
    ) -> "WaitRequest":
        """工厂方法创建等待请求

        Args:
            mailbox_id: 邮箱账号 ID
            email: 邮箱地址
            service_name: 业务服务名称
            callback_url: Webhook 回调地址

        Returns:
            新创建的等待请求实体
        """
        return cls(
            mailbox_id=mailbox_id,
            email=email,
            service_name=service_name,
            callback_url=callback_url,
            status=WaitRequestStatus.PENDING,
        )

    def complete(self, extraction_result: str) -> None:
        """标记为已完成

        Args:
            extraction_result: 提取到的验证码或链接

        Raises:
            InvalidStateTransitionException: 如果当前状态不是 PENDING
        """
        if self.status != WaitRequestStatus.PENDING:
            raise InvalidStateTransitionException(
                entity="WaitRequest",
                from_state=self.status.value,
                to_state=WaitRequestStatus.COMPLETED.value,
                reason="Only PENDING requests can be completed",
            )
        self.status = WaitRequestStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.extraction_result = extraction_result
        self.update_timestamp()

    def cancel(self) -> None:
        """取消请求

        Raises:
            InvalidStateTransitionException: 如果当前状态不是 PENDING
        """
        if self.status != WaitRequestStatus.PENDING:
            raise InvalidStateTransitionException(
                entity="WaitRequest",
                from_state=self.status.value,
                to_state=WaitRequestStatus.CANCELLED.value,
                reason="Only PENDING requests can be cancelled",
            )
        self.status = WaitRequestStatus.CANCELLED
        self.update_timestamp()

    def fail(self, reason: Optional[str] = None) -> None:
        """标记为失败

        Args:
            reason: 失败原因（可选）

        Raises:
            InvalidStateTransitionException: 如果当前状态不是 PENDING
        """
        if self.status != WaitRequestStatus.PENDING:
            raise InvalidStateTransitionException(
                entity="WaitRequest",
                from_state=self.status.value,
                to_state=WaitRequestStatus.FAILED.value,
                reason="Only PENDING requests can be marked as failed",
            )
        self.status = WaitRequestStatus.FAILED
        self.failure_reason = reason
        self.update_timestamp()

    @property
    def is_pending(self) -> bool:
        """是否处于等待状态"""
        return self.status == WaitRequestStatus.PENDING

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status == WaitRequestStatus.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        """是否已取消"""
        return self.status == WaitRequestStatus.CANCELLED

    @property
    def is_failed(self) -> bool:
        """是否已失败"""
        return self.status == WaitRequestStatus.FAILED

    @property
    def is_terminal(self) -> bool:
        """是否处于终态（已完成、已取消或已失败）"""
        return self.status in (
            WaitRequestStatus.COMPLETED,
            WaitRequestStatus.CANCELLED,
            WaitRequestStatus.FAILED,
        )
