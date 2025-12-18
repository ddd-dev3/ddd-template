"""ListMailboxAccountsHandler 单元测试"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
from uuid import uuid4

from application.handlers.mailbox.list_mailbox_accounts_handler import (
    ListMailboxAccountsHandler,
)
from application.queries.mailbox.list_mailbox_accounts import (
    ListMailboxAccountsQuery,
)
from domain.mailbox.repositories.mailbox_account_repository import MailboxAccountRepository
from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mailbox.value_objects.mailbox_enums import MailboxType, MailboxStatus
from domain.mailbox.value_objects.imap_config import ImapConfig


def create_mock_mailbox(
    mailbox_id: str = None,
    username: str = "test@example.com",
    mailbox_type: MailboxType = MailboxType.HOTMAIL,
    status: MailboxStatus = MailboxStatus.AVAILABLE,
    domain: str = None,
    occupied_by_service: str = None,
) -> MailboxAccount:
    """创建用于测试的 Mock 邮箱实体"""
    mailbox = Mock(spec=MailboxAccount)
    mailbox.id = mailbox_id or str(uuid4())
    mailbox.username = username
    mailbox.mailbox_type = mailbox_type
    mailbox.status = status
    mailbox.domain = domain
    mailbox.occupied_by_service = occupied_by_service
    mailbox.created_at = datetime.now(timezone.utc)
    mailbox.imap_config = Mock(spec=ImapConfig)
    mailbox.imap_config.server = "imap.example.com"
    mailbox.imap_config.port = 993
    return mailbox


@pytest.fixture
def mock_repository() -> Mock:
    """创建 Mock 仓储"""
    return Mock(spec=MailboxAccountRepository)


@pytest.fixture
def handler(mock_repository: Mock) -> ListMailboxAccountsHandler:
    """创建处理器实例"""
    return ListMailboxAccountsHandler(repository=mock_repository)


class TestListMailboxAccountsHandlerBasic:
    """基本查询测试"""

    @pytest.mark.asyncio
    async def test_list_empty_result(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试查询空结果"""
        mock_repository.list_filtered.return_value = ([], 0)

        query = ListMailboxAccountsQuery()
        result = await handler.handle(query)

        assert result.success is True
        assert result.data == []
        assert result.pagination.total == 0
        assert result.pagination.page == 1
        assert result.pagination.limit == 20
        assert result.pagination.total_pages == 1

    @pytest.mark.asyncio
    async def test_list_with_results(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试查询返回结果"""
        mailboxes = [
            create_mock_mailbox(username="user1@example.com"),
            create_mock_mailbox(username="user2@example.com"),
        ]
        mock_repository.list_filtered.return_value = (mailboxes, 2)

        query = ListMailboxAccountsQuery()
        result = await handler.handle(query)

        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0].username == "user1@example.com"
        assert result.data[1].username == "user2@example.com"
        assert result.pagination.total == 2

    @pytest.mark.asyncio
    async def test_list_converts_entity_to_item(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试正确转换实体为列表项"""
        mailbox = create_mock_mailbox(
            mailbox_id="test-id-123",
            username="admin@example.com",
            mailbox_type=MailboxType.DOMAIN_CATCHALL,
            status=MailboxStatus.OCCUPIED,
            domain="example.com",
            occupied_by_service="verification_service",
        )
        mock_repository.list_filtered.return_value = ([mailbox], 1)

        query = ListMailboxAccountsQuery()
        result = await handler.handle(query)

        assert result.success is True
        item = result.data[0]
        assert item.id == "test-id-123"
        assert item.username == "admin@example.com"
        assert item.type == "domain_catchall"
        assert item.status == "occupied"
        assert item.domain == "example.com"
        assert item.occupied_by_service == "verification_service"
        assert item.imap_server == "imap.example.com"
        assert item.imap_port == 993


class TestListMailboxAccountsHandlerFiltering:
    """筛选测试"""

    @pytest.mark.asyncio
    async def test_filter_by_service(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试按服务筛选"""
        mock_repository.list_filtered.return_value = ([], 0)

        query = ListMailboxAccountsQuery(service="my_service")
        await handler.handle(query)

        mock_repository.list_filtered.assert_called_once_with(
            service="my_service",
            status=None,
            page=1,
            limit=20,
        )

    @pytest.mark.asyncio
    async def test_filter_by_status_available(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试按 available 状态筛选"""
        mock_repository.list_filtered.return_value = ([], 0)

        query = ListMailboxAccountsQuery(status="available")
        await handler.handle(query)

        mock_repository.list_filtered.assert_called_once_with(
            service=None,
            status=MailboxStatus.AVAILABLE,
            page=1,
            limit=20,
        )

    @pytest.mark.asyncio
    async def test_filter_by_status_occupied(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试按 occupied 状态筛选"""
        mock_repository.list_filtered.return_value = ([], 0)

        query = ListMailboxAccountsQuery(status="occupied")
        await handler.handle(query)

        mock_repository.list_filtered.assert_called_once_with(
            service=None,
            status=MailboxStatus.OCCUPIED,
            page=1,
            limit=20,
        )

    @pytest.mark.asyncio
    async def test_filter_by_invalid_status_returns_error(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试无效状态筛选返回错误"""
        query = ListMailboxAccountsQuery(status="invalid_status")
        result = await handler.handle(query)

        assert result.success is False
        assert result.error_code == "INVALID_STATUS"
        assert "invalid_status" in result.message
        mock_repository.list_filtered.assert_not_called()

    @pytest.mark.asyncio
    async def test_filter_by_service_and_status(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试同时按服务和状态筛选"""
        mock_repository.list_filtered.return_value = ([], 0)

        query = ListMailboxAccountsQuery(service="test_service", status="occupied")
        await handler.handle(query)

        mock_repository.list_filtered.assert_called_once_with(
            service="test_service",
            status=MailboxStatus.OCCUPIED,
            page=1,
            limit=20,
        )


class TestListMailboxAccountsHandlerPagination:
    """分页测试"""

    @pytest.mark.asyncio
    async def test_pagination_defaults(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试默认分页参数"""
        mock_repository.list_filtered.return_value = ([], 0)

        query = ListMailboxAccountsQuery()
        result = await handler.handle(query)

        assert result.pagination.page == 1
        assert result.pagination.limit == 20

    @pytest.mark.asyncio
    async def test_pagination_custom_page(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试自定义页码"""
        mock_repository.list_filtered.return_value = ([], 0)

        query = ListMailboxAccountsQuery(page=5)
        await handler.handle(query)

        mock_repository.list_filtered.assert_called_once_with(
            service=None,
            status=None,
            page=5,
            limit=20,
        )

    @pytest.mark.asyncio
    async def test_pagination_custom_limit(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试自定义每页数量"""
        mock_repository.list_filtered.return_value = ([], 0)

        query = ListMailboxAccountsQuery(limit=50)
        await handler.handle(query)

        mock_repository.list_filtered.assert_called_once_with(
            service=None,
            status=None,
            page=1,
            limit=50,
        )

    @pytest.mark.asyncio
    async def test_pagination_limit_capped_at_100(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试每页数量上限为 100"""
        mock_repository.list_filtered.return_value = ([], 0)

        query = ListMailboxAccountsQuery(limit=500)  # 超出限制
        await handler.handle(query)

        mock_repository.list_filtered.assert_called_once_with(
            service=None,
            status=None,
            page=1,
            limit=100,  # 被限制为 100
        )

    @pytest.mark.asyncio
    async def test_pagination_page_minimum_is_1(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试页码最小值为 1"""
        mock_repository.list_filtered.return_value = ([], 0)

        query = ListMailboxAccountsQuery(page=0)  # 无效页码
        await handler.handle(query)

        mock_repository.list_filtered.assert_called_once_with(
            service=None,
            status=None,
            page=1,  # 被调整为 1
            limit=20,
        )

    @pytest.mark.asyncio
    async def test_pagination_limit_minimum_is_1(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试每页数量最小值为 1"""
        mock_repository.list_filtered.return_value = ([], 0)

        query = ListMailboxAccountsQuery(limit=0)  # 无效限制
        await handler.handle(query)

        mock_repository.list_filtered.assert_called_once_with(
            service=None,
            status=None,
            page=1,
            limit=1,  # 被调整为 1
        )

    @pytest.mark.asyncio
    async def test_pagination_total_pages_calculation(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试总页数计算"""
        mock_repository.list_filtered.return_value = ([], 55)  # 55 条记录

        query = ListMailboxAccountsQuery(limit=20)
        result = await handler.handle(query)

        assert result.pagination.total == 55
        assert result.pagination.total_pages == 3  # ceil(55/20) = 3

    @pytest.mark.asyncio
    async def test_pagination_total_pages_single_page(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试总页数为单页"""
        mock_repository.list_filtered.return_value = ([], 15)

        query = ListMailboxAccountsQuery(limit=20)
        result = await handler.handle(query)

        assert result.pagination.total_pages == 1

    @pytest.mark.asyncio
    async def test_pagination_total_pages_exact_fit(
        self,
        handler: ListMailboxAccountsHandler,
        mock_repository: Mock,
    ):
        """测试总数刚好整除的情况"""
        mock_repository.list_filtered.return_value = ([], 40)

        query = ListMailboxAccountsQuery(limit=20)
        result = await handler.handle(query)

        assert result.pagination.total_pages == 2  # 40/20 = 2
