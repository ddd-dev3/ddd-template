"""邮箱账号 API 路由测试"""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from interfaces.api.routes.accounts import (
    router,
    AddMailboxAccountRequest,
    set_handler_getter,
    get_add_mailbox_handler,
    set_list_handler_getter,
    get_list_mailbox_handler,
    set_delete_handler_getter,
    get_delete_mailbox_handler,
)
from application.handlers.mailbox.add_mailbox_account_handler import (
    AddMailboxAccountHandler,
    AddMailboxAccountResult,
)
from application.handlers.mailbox.list_mailbox_accounts_handler import (
    ListMailboxAccountsHandler,
)
from application.queries.mailbox.list_mailbox_accounts import (
    ListMailboxAccountsResult,
    MailboxAccountItem,
    PaginationInfo,
)
from application.handlers.mailbox.delete_mailbox_account_handler import (
    DeleteMailboxAccountHandler,
)
from application.commands.mailbox.delete_mailbox_account import (
    DeleteMailboxAccountResult,
)


@pytest.fixture
def mock_handler() -> Mock:
    """创建 Mock Handler"""
    handler = Mock(spec=AddMailboxAccountHandler)
    return handler


@pytest.fixture
def app(mock_handler: Mock) -> FastAPI:
    """创建测试用 FastAPI 应用"""
    app = FastAPI()
    app.include_router(router)

    # 设置 handler getter
    set_handler_getter(lambda: mock_handler)

    # 存储 handler 引用以便在测试中配置
    app.state.mock_handler = mock_handler

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """创建测试客户端"""
    return TestClient(app)


class TestAddMailboxAccountEndpoint:
    """添加邮箱账号端点测试"""

    def test_add_domain_catchall_mailbox_success(
        self,
        client: TestClient,
        app: FastAPI,
    ):
        """测试成功添加域名 Catch-All 邮箱"""
        # 配置 mock handler 返回成功结果
        mock_handler = app.state.mock_handler
        mock_handler.handle = AsyncMock(return_value=AddMailboxAccountResult(
            success=True,
            mailbox_id="550e8400-e29b-41d4-a716-446655440000",
            username="admin@example.com",
            message="Mailbox account created successfully",
        ))

        response = client.post(
            "/accounts",
            json={
                "type": "domain_catchall",
                "username": "admin@example.com",
                "password": "secret123",
                "imap_server": "imap.example.com",
                "imap_port": 993,
                "domain": "example.com",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert data["username"] == "admin@example.com"
        assert data["type"] == "domain_catchall"
        assert data["domain"] == "example.com"
        assert data["status"] == "available"

    def test_add_hotmail_mailbox_success(
        self,
        client: TestClient,
        app: FastAPI,
    ):
        """测试成功添加 Hotmail 邮箱"""
        mock_handler = app.state.mock_handler
        mock_handler.handle = AsyncMock(return_value=AddMailboxAccountResult(
            success=True,
            mailbox_id="660e8400-e29b-41d4-a716-446655440000",
            username="user@hotmail.com",
            message="Created",
        ))

        response = client.post(
            "/accounts",
            json={
                "type": "hotmail",
                "username": "user@hotmail.com",
                "password": "password123",
                "imap_server": "outlook.office365.com",
                "imap_port": 993,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "user@hotmail.com"
        assert data["type"] == "hotmail"
        assert data["domain"] is None

    def test_duplicate_mailbox_returns_409(
        self,
        client: TestClient,
        app: FastAPI,
    ):
        """测试重复邮箱返回 409 Conflict"""
        mock_handler = app.state.mock_handler
        mock_handler.handle = AsyncMock(return_value=AddMailboxAccountResult(
            success=False,
            username="existing@example.com",
            message="Mailbox with username 'existing@example.com' already exists",
            error_code="DUPLICATE_MAILBOX",
        ))

        response = client.post(
            "/accounts",
            json={
                "type": "hotmail",
                "username": "existing@example.com",
                "password": "secret",
                "imap_server": "outlook.office365.com",
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_imap_connection_error_returns_400(
        self,
        client: TestClient,
        app: FastAPI,
    ):
        """测试 IMAP 连接失败返回 400"""
        mock_handler = app.state.mock_handler
        mock_handler.handle = AsyncMock(return_value=AddMailboxAccountResult(
            success=False,
            username="test@example.com",
            message="IMAP connection failed: Connection refused",
            error_code="IMAP_CONNECTION_ERROR",
        ))

        response = client.post(
            "/accounts",
            json={
                "type": "hotmail",
                "username": "test@example.com",
                "password": "wrong",
                "imap_server": "invalid.server.com",
            },
        )

        assert response.status_code == 400
        assert "Connection refused" in response.json()["detail"]

    def test_imap_auth_error_returns_400(
        self,
        client: TestClient,
        app: FastAPI,
    ):
        """测试 IMAP 认证失败返回 400"""
        mock_handler = app.state.mock_handler
        mock_handler.handle = AsyncMock(return_value=AddMailboxAccountResult(
            success=False,
            username="test@example.com",
            message="IMAP authentication failed",
            error_code="IMAP_AUTH_ERROR",
        ))

        response = client.post(
            "/accounts",
            json={
                "type": "hotmail",
                "username": "test@example.com",
                "password": "wrong_password",
                "imap_server": "outlook.office365.com",
            },
        )

        assert response.status_code == 400
        assert "authentication" in response.json()["detail"].lower()

    def test_invalid_mailbox_type_returns_422(
        self,
        client: TestClient,
        app: FastAPI,
    ):
        """测试无效邮箱类型返回 422"""
        mock_handler = app.state.mock_handler
        mock_handler.handle = AsyncMock(return_value=AddMailboxAccountResult(
            success=False,
            username="test@example.com",
            message="Invalid mailbox type: invalid_type",
            error_code="INVALID_MAILBOX_TYPE",
        ))

        response = client.post(
            "/accounts",
            json={
                "type": "invalid_type",
                "username": "test@example.com",
                "password": "secret",
                "imap_server": "imap.example.com",
            },
        )

        assert response.status_code == 422
        assert "Invalid mailbox type" in response.json()["detail"]

    def test_missing_domain_for_catchall_returns_422(
        self,
        client: TestClient,
        app: FastAPI,
    ):
        """测试域名 Catch-All 缺少域名返回 422"""
        mock_handler = app.state.mock_handler
        mock_handler.handle = AsyncMock(return_value=AddMailboxAccountResult(
            success=False,
            username="admin@example.com",
            message="Domain is required for domain_catchall mailbox type",
            error_code="MISSING_DOMAIN",
        ))

        response = client.post(
            "/accounts",
            json={
                "type": "domain_catchall",
                "username": "admin@example.com",
                "password": "secret",
                "imap_server": "imap.example.com",
                # domain 缺失
            },
        )

        assert response.status_code == 422
        assert "Domain is required" in response.json()["detail"]


class TestHandlerNotConfigured:
    """测试 Handler 未配置场景"""

    @pytest.fixture
    def app_no_handler(self) -> FastAPI:
        """创建没有 handler 的应用"""
        app = FastAPI()
        app.include_router(router)
        # 设置 handler getter 返回 None
        set_handler_getter(lambda: None)
        return app

    @pytest.fixture
    def client_no_handler(self, app_no_handler: FastAPI) -> TestClient:
        return TestClient(app_no_handler)

    def test_handler_not_configured_returns_500(
        self,
        client_no_handler: TestClient,
    ):
        """测试 Handler 未配置返回 500"""
        response = client_no_handler.post(
            "/accounts",
            json={
                "type": "hotmail",
                "username": "test@example.com",
                "password": "secret",
                "imap_server": "outlook.office365.com",
            },
        )

        assert response.status_code == 500
        assert "Handler not configured" in response.json()["detail"]


class TestAddMailboxAccountRequestValidation:
    """请求参数验证测试"""

    @pytest.fixture
    def simple_app(self) -> FastAPI:
        """创建简单应用用于 Pydantic 验证测试"""
        app = FastAPI()
        app.include_router(router)
        # 设置一个返回 None 的 handler getter
        set_handler_getter(lambda: None)
        return app

    @pytest.fixture
    def validation_client(self, simple_app: FastAPI) -> TestClient:
        return TestClient(simple_app)

    def test_missing_required_field_username(self, validation_client: TestClient):
        """测试缺少必填字段 username"""
        response = validation_client.post(
            "/accounts",
            json={
                "type": "hotmail",
                # username 缺失
                "password": "secret",
                "imap_server": "outlook.office365.com",
            },
        )

        assert response.status_code == 422

    def test_missing_required_field_password(self, validation_client: TestClient):
        """测试缺少必填字段 password"""
        response = validation_client.post(
            "/accounts",
            json={
                "type": "hotmail",
                "username": "test@example.com",
                # password 缺失
                "imap_server": "outlook.office365.com",
            },
        )

        assert response.status_code == 422

    def test_invalid_port_below_range(self, validation_client: TestClient):
        """测试端口号低于有效范围"""
        response = validation_client.post(
            "/accounts",
            json={
                "type": "hotmail",
                "username": "test@example.com",
                "password": "secret",
                "imap_server": "outlook.office365.com",
                "imap_port": 0,  # 无效端口
            },
        )

        assert response.status_code == 422

    def test_invalid_port_above_range(self, validation_client: TestClient):
        """测试端口号高于有效范围"""
        response = validation_client.post(
            "/accounts",
            json={
                "type": "hotmail",
                "username": "test@example.com",
                "password": "secret",
                "imap_server": "outlook.office365.com",
                "imap_port": 70000,  # 无效端口
            },
        )

        assert response.status_code == 422

    def test_default_port_is_993(self):
        """测试默认端口号为 993"""
        # 这个测试验证请求模型的默认值
        request = AddMailboxAccountRequest(
            type="hotmail",
            username="test@example.com",
            password="secret",
            imap_server="outlook.office365.com",
        )

        assert request.imap_port == 993


class TestResponseModel:
    """响应模型测试"""

    @pytest.fixture
    def response_app(self) -> FastAPI:
        """创建测试响应的应用"""
        mock_handler = Mock(spec=AddMailboxAccountHandler)
        mock_handler.handle = AsyncMock(return_value=AddMailboxAccountResult(
            success=True,
            mailbox_id="test-id",
            username="test@example.com",
            message="Created",
        ))

        app = FastAPI()
        app.include_router(router)
        set_handler_getter(lambda: mock_handler)
        return app

    @pytest.fixture
    def response_client(self, response_app: FastAPI) -> TestClient:
        return TestClient(response_app)

    def test_response_does_not_include_password(
        self,
        response_client: TestClient,
    ):
        """测试响应不包含密码"""
        response = response_client.post(
            "/accounts",
            json={
                "type": "hotmail",
                "username": "test@example.com",
                "password": "super_secret_password",
                "imap_server": "outlook.office365.com",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # 确保密码不在响应中
        assert "password" not in data
        assert "super_secret_password" not in str(data)
        assert "encrypted_password" not in data


# ============ GET /accounts 端点测试 ============


@pytest.fixture
def mock_list_handler() -> Mock:
    """创建 Mock List Handler"""
    handler = Mock(spec=ListMailboxAccountsHandler)
    return handler


@pytest.fixture
def list_app(mock_list_handler: Mock) -> FastAPI:
    """创建测试 GET 端点的 FastAPI 应用"""
    app = FastAPI()
    app.include_router(router)

    # 设置 list handler getter
    set_list_handler_getter(lambda: mock_list_handler)
    # 设置 add handler getter (返回 None，因为我们只测试 GET)
    set_handler_getter(lambda: None)

    # 存储 handler 引用以便在测试中配置
    app.state.mock_list_handler = mock_list_handler

    return app


@pytest.fixture
def list_client(list_app: FastAPI) -> TestClient:
    """创建测试客户端"""
    return TestClient(list_app)


def create_sample_mailbox_items(count: int) -> list[MailboxAccountItem]:
    """创建示例邮箱列表项"""
    return [
        MailboxAccountItem(
            id=f"id-{i}",
            username=f"user{i}@example.com",
            type="hotmail",
            imap_server="outlook.office365.com",
            imap_port=993,
            domain=None,
            status="available",
            occupied_by_service=None,
            created_at="2024-01-01T00:00:00+00:00",
        )
        for i in range(count)
    ]


class TestListMailboxAccountsEndpoint:
    """GET /accounts 端点测试"""

    def test_list_accounts_empty(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试查询空列表"""
        mock_handler = list_app.state.mock_list_handler
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=True,
            data=[],
            pagination=PaginationInfo(total=0, page=1, limit=20, total_pages=1),
            message="Query successful",
        ))

        response = list_client.get("/accounts")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["pagination"]["total"] == 0
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 20
        assert data["pagination"]["total_pages"] == 1

    def test_list_accounts_with_results(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试查询返回结果"""
        mock_handler = list_app.state.mock_list_handler
        items = create_sample_mailbox_items(3)
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=True,
            data=items,
            pagination=PaginationInfo(total=3, page=1, limit=20, total_pages=1),
            message="Query successful",
        ))

        response = list_client.get("/accounts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3
        assert data["data"][0]["username"] == "user0@example.com"
        assert data["pagination"]["total"] == 3


class TestListMailboxAccountsFiltering:
    """GET /accounts 筛选测试"""

    def test_filter_by_service(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试按服务筛选"""
        mock_handler = list_app.state.mock_list_handler
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=True,
            data=[],
            pagination=PaginationInfo(total=0, page=1, limit=20, total_pages=1),
        ))

        response = list_client.get("/accounts?service=my_service")

        assert response.status_code == 200
        # 验证 handler 收到正确的查询参数
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.service == "my_service"

    def test_filter_by_status_available(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试按 available 状态筛选"""
        mock_handler = list_app.state.mock_list_handler
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=True,
            data=[],
            pagination=PaginationInfo(total=0, page=1, limit=20, total_pages=1),
        ))

        response = list_client.get("/accounts?status=available")

        assert response.status_code == 200
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.status == "available"

    def test_filter_by_status_occupied(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试按 occupied 状态筛选"""
        mock_handler = list_app.state.mock_list_handler
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=True,
            data=[],
            pagination=PaginationInfo(total=0, page=1, limit=20, total_pages=1),
        ))

        response = list_client.get("/accounts?status=occupied")

        assert response.status_code == 200
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.status == "occupied"

    def test_filter_invalid_status_returns_422(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试无效状态筛选返回 422"""
        mock_handler = list_app.state.mock_list_handler
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=False,
            message="Invalid status value: invalid. Valid values: available, occupied",
            error_code="INVALID_STATUS",
        ))

        response = list_client.get("/accounts?status=invalid")

        assert response.status_code == 422

    def test_filter_by_service_and_status(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试同时按服务和状态筛选"""
        mock_handler = list_app.state.mock_list_handler
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=True,
            data=[],
            pagination=PaginationInfo(total=0, page=1, limit=20, total_pages=1),
        ))

        response = list_client.get("/accounts?service=test_service&status=occupied")

        assert response.status_code == 200
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.service == "test_service"
        assert call_args.status == "occupied"


class TestListMailboxAccountsPagination:
    """GET /accounts 分页测试"""

    def test_pagination_default_values(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试分页默认值"""
        mock_handler = list_app.state.mock_list_handler
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=True,
            data=[],
            pagination=PaginationInfo(total=0, page=1, limit=20, total_pages=1),
        ))

        response = list_client.get("/accounts")

        assert response.status_code == 200
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.page == 1
        assert call_args.limit == 20

    def test_pagination_custom_page(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试自定义页码"""
        mock_handler = list_app.state.mock_list_handler
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=True,
            data=[],
            pagination=PaginationInfo(total=0, page=3, limit=20, total_pages=1),
        ))

        response = list_client.get("/accounts?page=3")

        assert response.status_code == 200
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.page == 3

    def test_pagination_custom_limit(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试自定义每页数量"""
        mock_handler = list_app.state.mock_list_handler
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=True,
            data=[],
            pagination=PaginationInfo(total=0, page=1, limit=50, total_pages=1),
        ))

        response = list_client.get("/accounts?limit=50")

        assert response.status_code == 200
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.limit == 50

    def test_pagination_invalid_page_below_min(
        self,
        list_client: TestClient,
    ):
        """测试页码低于最小值返回 422"""
        response = list_client.get("/accounts?page=0")
        assert response.status_code == 422

    def test_pagination_invalid_limit_below_min(
        self,
        list_client: TestClient,
    ):
        """测试每页数量低于最小值返回 422"""
        response = list_client.get("/accounts?limit=0")
        assert response.status_code == 422

    def test_pagination_invalid_limit_above_max(
        self,
        list_client: TestClient,
    ):
        """测试每页数量高于最大值返回 422"""
        response = list_client.get("/accounts?limit=101")
        assert response.status_code == 422

    def test_pagination_max_limit_allowed(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试最大每页数量 100 是允许的"""
        mock_handler = list_app.state.mock_list_handler
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=True,
            data=[],
            pagination=PaginationInfo(total=0, page=1, limit=100, total_pages=1),
        ))

        response = list_client.get("/accounts?limit=100")

        assert response.status_code == 200
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.limit == 100


class TestListMailboxAccountsHandlerNotConfigured:
    """GET /accounts Handler 未配置测试"""

    @pytest.fixture
    def app_no_list_handler(self) -> FastAPI:
        """创建没有 list handler 的应用"""
        app = FastAPI()
        app.include_router(router)
        # 设置 handler getter 返回 None
        set_list_handler_getter(lambda: None)
        set_handler_getter(lambda: None)
        return app

    @pytest.fixture
    def client_no_list_handler(self, app_no_list_handler: FastAPI) -> TestClient:
        return TestClient(app_no_list_handler)

    def test_list_handler_not_configured_returns_500(
        self,
        client_no_list_handler: TestClient,
    ):
        """测试 List Handler 未配置返回 500"""
        response = client_no_list_handler.get("/accounts")

        assert response.status_code == 500
        assert "Handler not configured" in response.json()["detail"]


class TestListMailboxAccountsResponseModel:
    """GET /accounts 响应模型测试"""

    def test_response_contains_all_fields(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试响应包含所有字段"""
        mock_handler = list_app.state.mock_list_handler
        item = MailboxAccountItem(
            id="test-id",
            username="test@example.com",
            type="domain_catchall",
            imap_server="imap.example.com",
            imap_port=993,
            domain="example.com",
            status="occupied",
            occupied_by_service="verification_service",
            created_at="2024-01-01T00:00:00+00:00",
        )
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=True,
            data=[item],
            pagination=PaginationInfo(total=1, page=1, limit=20, total_pages=1),
        ))

        response = list_client.get("/accounts")

        assert response.status_code == 200
        data = response.json()
        item_data = data["data"][0]

        assert item_data["id"] == "test-id"
        assert item_data["username"] == "test@example.com"
        assert item_data["type"] == "domain_catchall"
        assert item_data["imap_server"] == "imap.example.com"
        assert item_data["imap_port"] == 993
        assert item_data["domain"] == "example.com"
        assert item_data["status"] == "occupied"
        assert item_data["occupied_by_service"] == "verification_service"
        assert item_data["created_at"] == "2024-01-01T00:00:00+00:00"

    def test_response_does_not_include_password(
        self,
        list_client: TestClient,
        list_app: FastAPI,
    ):
        """测试响应不包含密码字段"""
        mock_handler = list_app.state.mock_list_handler
        item = MailboxAccountItem(
            id="test-id",
            username="test@example.com",
            type="hotmail",
            imap_server="outlook.office365.com",
            imap_port=993,
            domain=None,
            status="available",
            occupied_by_service=None,
            created_at="2024-01-01T00:00:00+00:00",
        )
        mock_handler.handle = AsyncMock(return_value=ListMailboxAccountsResult(
            success=True,
            data=[item],
            pagination=PaginationInfo(total=1, page=1, limit=20, total_pages=1),
        ))

        response = list_client.get("/accounts")

        assert response.status_code == 200
        data = response.json()
        item_data = data["data"][0]

        # 确保密码相关字段不在响应中
        assert "password" not in item_data
        assert "encrypted_password" not in item_data


# ============ DELETE /accounts/{mailbox_id} 端点测试 ============


@pytest.fixture
def mock_delete_handler() -> Mock:
    """创建 Mock Delete Handler"""
    handler = Mock(spec=DeleteMailboxAccountHandler)
    return handler


@pytest.fixture
def delete_app(mock_delete_handler: Mock) -> FastAPI:
    """创建测试 DELETE 端点的 FastAPI 应用"""
    app = FastAPI()
    app.include_router(router)

    # 设置 delete handler getter
    set_delete_handler_getter(lambda: mock_delete_handler)
    # 设置其他 handler getter (返回 None，因为我们只测试 DELETE)
    set_handler_getter(lambda: None)
    set_list_handler_getter(lambda: None)

    # 存储 handler 引用以便在测试中配置
    app.state.mock_delete_handler = mock_delete_handler

    return app


@pytest.fixture
def delete_client(delete_app: FastAPI) -> TestClient:
    """创建测试客户端"""
    return TestClient(delete_app)


class TestDeleteMailboxAccountEndpoint:
    """DELETE /accounts/{mailbox_id} 端点测试"""

    def test_delete_available_mailbox_success(
        self,
        delete_client: TestClient,
        delete_app: FastAPI,
    ):
        """测试成功删除 available 状态的邮箱"""
        mailbox_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_handler = delete_app.state.mock_delete_handler
        mock_handler.handle = AsyncMock(return_value=DeleteMailboxAccountResult(
            success=True,
            mailbox_id=mailbox_id,
            username="test@example.com",
            message=f"Mailbox account '{mailbox_id}' deleted successfully",
        ))

        response = delete_client.delete(f"/accounts/{mailbox_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mailbox_id
        assert "deleted successfully" in data["message"]

    def test_delete_returns_correct_response_fields(
        self,
        delete_client: TestClient,
        delete_app: FastAPI,
    ):
        """测试删除成功返回正确的响应字段"""
        mailbox_id = "660e8400-e29b-41d4-a716-446655440001"
        mock_handler = delete_app.state.mock_delete_handler
        mock_handler.handle = AsyncMock(return_value=DeleteMailboxAccountResult(
            success=True,
            mailbox_id=mailbox_id,
            username="deleted@example.com",
            message="Deleted",
        ))

        response = delete_client.delete(f"/accounts/{mailbox_id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "id" in data
        # 确保不返回敏感信息
        assert "password" not in data
        assert "encrypted_password" not in data


class TestDeleteMailboxAccountNotFound:
    """DELETE /accounts/{mailbox_id} 404 测试"""

    def test_delete_nonexistent_mailbox_returns_404(
        self,
        delete_client: TestClient,
        delete_app: FastAPI,
    ):
        """测试删除不存在的邮箱返回 404"""
        mailbox_id = "nonexistent-id-12345"
        mock_handler = delete_app.state.mock_delete_handler
        mock_handler.handle = AsyncMock(return_value=DeleteMailboxAccountResult(
            success=False,
            mailbox_id=mailbox_id,
            message=f"Mailbox with ID '{mailbox_id}' not found",
            error_code="MAILBOX_NOT_FOUND",
        ))

        response = delete_client.delete(f"/accounts/{mailbox_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_invalid_uuid_returns_404(
        self,
        delete_client: TestClient,
        delete_app: FastAPI,
    ):
        """测试无效 UUID 格式返回 404"""
        invalid_id = "not-a-valid-uuid"
        mock_handler = delete_app.state.mock_delete_handler
        mock_handler.handle = AsyncMock(return_value=DeleteMailboxAccountResult(
            success=False,
            mailbox_id=invalid_id,
            message=f"Mailbox with ID '{invalid_id}' not found",
            error_code="MAILBOX_NOT_FOUND",
        ))

        response = delete_client.delete(f"/accounts/{invalid_id}")

        assert response.status_code == 404


class TestDeleteMailboxAccountOccupied:
    """DELETE /accounts/{mailbox_id} 409 Conflict 测试"""

    def test_delete_occupied_mailbox_returns_409(
        self,
        delete_client: TestClient,
        delete_app: FastAPI,
    ):
        """测试删除 occupied 状态的邮箱返回 409"""
        mailbox_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_handler = delete_app.state.mock_delete_handler
        mock_handler.handle = AsyncMock(return_value=DeleteMailboxAccountResult(
            success=False,
            mailbox_id=mailbox_id,
            username="occupied@example.com",
            message=f"Mailbox 'occupied@example.com' is currently occupied. Release it first before deleting.",
            error_code="MAILBOX_OCCUPIED",
        ))

        response = delete_client.delete(f"/accounts/{mailbox_id}")

        assert response.status_code == 409
        assert "occupied" in response.json()["detail"].lower()

    def test_delete_occupied_message_suggests_release(
        self,
        delete_client: TestClient,
        delete_app: FastAPI,
    ):
        """测试 occupied 错误消息提示先释放占用"""
        mailbox_id = "770e8400-e29b-41d4-a716-446655440002"
        mock_handler = delete_app.state.mock_delete_handler
        mock_handler.handle = AsyncMock(return_value=DeleteMailboxAccountResult(
            success=False,
            mailbox_id=mailbox_id,
            username="busy@example.com",
            message="Mailbox 'busy@example.com' is currently occupied. Release it first before deleting.",
            error_code="MAILBOX_OCCUPIED",
        ))

        response = delete_client.delete(f"/accounts/{mailbox_id}")

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "release" in detail.lower() or "Release" in detail


class TestDeleteMailboxAccountHandlerNotConfigured:
    """DELETE /accounts/{mailbox_id} Handler 未配置测试"""

    @pytest.fixture
    def app_no_delete_handler(self) -> FastAPI:
        """创建没有 delete handler 的应用"""
        app = FastAPI()
        app.include_router(router)
        # 设置 handler getter 返回 None
        set_delete_handler_getter(lambda: None)
        set_handler_getter(lambda: None)
        set_list_handler_getter(lambda: None)
        return app

    @pytest.fixture
    def client_no_delete_handler(self, app_no_delete_handler: FastAPI) -> TestClient:
        return TestClient(app_no_delete_handler)

    def test_delete_handler_not_configured_returns_500(
        self,
        client_no_delete_handler: TestClient,
    ):
        """测试 Delete Handler 未配置返回 500"""
        response = client_no_delete_handler.delete("/accounts/some-id")

        assert response.status_code == 500
        assert "Handler not configured" in response.json()["detail"]


class TestDeleteMailboxAccountGenericError:
    """DELETE /accounts/{mailbox_id} 通用错误测试"""

    def test_delete_unknown_error_returns_400(
        self,
        delete_client: TestClient,
        delete_app: FastAPI,
    ):
        """测试未知错误返回 400"""
        mailbox_id = "880e8400-e29b-41d4-a716-446655440003"
        mock_handler = delete_app.state.mock_delete_handler
        mock_handler.handle = AsyncMock(return_value=DeleteMailboxAccountResult(
            success=False,
            mailbox_id=mailbox_id,
            message="Unexpected error occurred",
            error_code="UNKNOWN_ERROR",
        ))

        response = delete_client.delete(f"/accounts/{mailbox_id}")

        assert response.status_code == 400
        assert "error" in response.json()["detail"].lower()
