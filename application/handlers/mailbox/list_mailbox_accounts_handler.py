"""查询邮箱账号列表处理器"""

import math
from typing import Optional

from application.queries.mailbox.list_mailbox_accounts import (
    ListMailboxAccountsQuery,
    ListMailboxAccountsResult,
    MailboxAccountItem,
    PaginationInfo,
)
from domain.mailbox.repositories.mailbox_account_repository import MailboxAccountRepository
from domain.mailbox.value_objects.mailbox_enums import MailboxStatus


class ListMailboxAccountsHandler:
    """
    查询邮箱账号列表处理器

    处理 ListMailboxAccountsQuery，返回分页的邮箱账号列表。
    """

    def __init__(self, repository: MailboxAccountRepository):
        """
        初始化处理器

        Args:
            repository: 邮箱账号仓储
        """
        self._repository = repository

    async def handle(self, query: ListMailboxAccountsQuery) -> ListMailboxAccountsResult:
        """
        处理查询请求

        Args:
            query: 查询参数

        Returns:
            ListMailboxAccountsResult: 查询结果
        """
        # 验证分页参数
        page = max(1, query.page)
        limit = max(1, min(100, query.limit))  # 限制最大每页 100

        # 转换状态参数
        status_filter: Optional[MailboxStatus] = None
        if query.status:
            try:
                status_filter = MailboxStatus(query.status)
            except ValueError:
                return ListMailboxAccountsResult(
                    success=False,
                    message=f"Invalid status value: {query.status}. Valid values: available, occupied",
                    error_code="INVALID_STATUS",
                )

        # 调用仓储查询
        mailboxes, total = self._repository.list_filtered(
            service=query.service,
            status=status_filter,
            page=page,
            limit=limit,
        )

        # 转换为响应格式
        items = [
            MailboxAccountItem(
                id=str(mailbox.id),
                username=mailbox.username,
                type=mailbox.mailbox_type.value,
                imap_server=mailbox.imap_config.server if mailbox.imap_config else "",
                imap_port=mailbox.imap_config.port if mailbox.imap_config else 993,
                domain=mailbox.domain,
                status=mailbox.status.value,
                occupied_by_service=mailbox.occupied_by_service,
                created_at=mailbox.created_at.isoformat() if mailbox.created_at else "",
            )
            for mailbox in mailboxes
        ]

        # 计算总页数
        total_pages = math.ceil(total / limit) if total > 0 else 1

        pagination = PaginationInfo(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )

        return ListMailboxAccountsResult(
            success=True,
            data=items,
            pagination=pagination,
            message="Query successful",
        )
