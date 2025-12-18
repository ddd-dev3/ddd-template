"""邮件仓储接口"""

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from domain.mail.entities.email import Email


class EmailRepository(ABC):
    """
    邮件仓储接口

    定义邮件的数据访问契约，具体实现在基础设施层。
    """

    @abstractmethod
    def add(self, email: Email) -> None:
        """
        添加邮件记录

        Args:
            email: 邮件实体
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, email_id: UUID) -> Optional[Email]:
        """
        根据 ID 获取邮件

        Args:
            email_id: 邮件 ID

        Returns:
            邮件实体，不存在返回 None
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_message_id(self, message_id: str) -> Optional[Email]:
        """
        根据 Message-ID 获取邮件

        Args:
            message_id: IMAP 邮件唯一标识

        Returns:
            邮件实体，不存在返回 None
        """
        raise NotImplementedError

    @abstractmethod
    def exists_by_message_id(self, message_id: str) -> bool:
        """
        检查 Message-ID 是否已存在

        用于防止重复存储同一封邮件。

        Args:
            message_id: IMAP 邮件唯一标识

        Returns:
            True 如果存在，False 如果不存在
        """
        raise NotImplementedError

    @abstractmethod
    def list_by_mailbox_id(self, mailbox_id: UUID) -> List[Email]:
        """
        获取指定邮箱的所有邮件

        Args:
            mailbox_id: 邮箱账号 ID

        Returns:
            邮件列表
        """
        raise NotImplementedError

    @abstractmethod
    def list_unprocessed(self, limit: int = 100) -> List[Email]:
        """
        获取未处理的邮件

        Args:
            limit: 最大返回数量，默认 100，防止内存溢出

        Returns:
            未处理的邮件列表（is_processed=False），按接收时间升序
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, email: Email) -> None:
        """
        更新邮件记录

        Args:
            email: 邮件实体
        """
        raise NotImplementedError

    @abstractmethod
    def remove(self, email: Email) -> None:
        """
        删除邮件记录

        Args:
            email: 邮件实体
        """
        raise NotImplementedError
