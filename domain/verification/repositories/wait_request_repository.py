"""等待请求仓储接口"""

from typing import List, Optional, Protocol
from uuid import UUID

from domain.verification.entities.wait_request import WaitRequest
from domain.verification.value_objects.wait_request_status import WaitRequestStatus


class WaitRequestRepository(Protocol):
    """等待请求仓储接口

    定义等待请求的持久化操作契约。
    具体实现在 infrastructure 层。
    """

    def add(self, wait_request: WaitRequest) -> None:
        """添加等待请求

        Args:
            wait_request: 要添加的等待请求实体
        """
        ...

    def get_by_id(self, request_id: UUID) -> Optional[WaitRequest]:
        """按 ID 获取等待请求

        Args:
            request_id: 等待请求 ID

        Returns:
            等待请求实体，如果不存在返回 None
        """
        ...

    def get_pending_by_mailbox_id(self, mailbox_id: UUID) -> Optional[WaitRequest]:
        """获取邮箱的待处理请求

        Args:
            mailbox_id: 邮箱账号 ID

        Returns:
            处于 PENDING 状态的等待请求，如果不存在返回 None
        """
        ...

    def get_pending_by_email(self, email: str) -> Optional[WaitRequest]:
        """按邮箱地址获取待处理请求

        Args:
            email: 邮箱地址

        Returns:
            处于 PENDING 状态的等待请求，如果不存在返回 None
        """
        ...

    def get_all_pending_by_email(self, email: str) -> List[WaitRequest]:
        """获取邮箱地址的所有待处理请求

        用于同一邮箱存在多个等待请求的场景（不同 service）。

        Args:
            email: 邮箱地址

        Returns:
            所有 PENDING 状态的等待请求列表，按创建时间升序排序
        """
        ...

    def get_pending_by_email_and_service(
        self, email: str, service_name: str
    ) -> Optional[WaitRequest]:
        """按邮箱地址和服务名获取待处理请求

        用于精确匹配特定服务的等待请求。

        Args:
            email: 邮箱地址
            service_name: 服务名称

        Returns:
            匹配的等待请求，如果不存在返回 None
        """
        ...

    def update(self, wait_request: WaitRequest) -> None:
        """更新等待请求

        Args:
            wait_request: 要更新的等待请求实体
        """
        ...

    def list_by_status(
        self,
        status: WaitRequestStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WaitRequest]:
        """按状态列出等待请求

        Args:
            status: 请求状态
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            等待请求列表
        """
        ...

    def delete(self, request_id: UUID) -> bool:
        """删除等待请求

        Args:
            request_id: 等待请求 ID

        Returns:
            如果成功删除返回 True，否则返回 False
        """
        ...
