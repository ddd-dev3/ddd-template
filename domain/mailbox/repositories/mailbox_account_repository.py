"""邮箱账号仓储接口"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from uuid import UUID

from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mailbox.value_objects.mailbox_enums import MailboxStatus


class MailboxAccountRepository(ABC):
    """
    邮箱账号仓储接口

    定义邮箱账号的数据访问契约，具体实现在基础设施层。
    """

    @abstractmethod
    def add(self, mailbox: MailboxAccount) -> None:
        """
        添加邮箱账号

        Args:
            mailbox: 邮箱账号实体
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, mailbox_id: UUID) -> Optional[MailboxAccount]:
        """
        根据 ID 获取邮箱账号

        Args:
            mailbox_id: 邮箱账号 ID

        Returns:
            邮箱账号实体，不存在返回 None
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[MailboxAccount]:
        """
        根据用户名获取邮箱账号

        Args:
            username: 邮箱用户名/地址

        Returns:
            邮箱账号实体，不存在返回 None
        """
        raise NotImplementedError

    @abstractmethod
    def exists_by_username(self, username: str) -> bool:
        """
        检查用户名是否已存在

        Args:
            username: 邮箱用户名/地址

        Returns:
            True 如果存在，False 如果不存在
        """
        raise NotImplementedError

    @abstractmethod
    def remove(self, mailbox: MailboxAccount) -> None:
        """
        移除邮箱账号

        Args:
            mailbox: 邮箱账号实体
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, mailbox: MailboxAccount) -> None:
        """
        更新邮箱账号

        Args:
            mailbox: 邮箱账号实体
        """
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> List[MailboxAccount]:
        """
        获取所有邮箱账号

        Returns:
            邮箱账号列表
        """
        raise NotImplementedError

    @abstractmethod
    def list_filtered(
        self,
        service: Optional[str] = None,
        status: Optional[MailboxStatus] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[MailboxAccount], int]:
        """
        分页筛选查询邮箱列表

        Args:
            service: 按占用服务筛选（匹配 occupied_by_service）
            status: 按状态筛选（available/occupied）
            page: 页码，从 1 开始
            limit: 每页数量

        Returns:
            Tuple[items, total_count]: 当前页数据和总数
        """
        raise NotImplementedError
