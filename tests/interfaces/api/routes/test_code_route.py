"""查询验证码 API 路由测试"""

import pytest
from unittest.mock import Mock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from interfaces.api.routes.code import (
    router,
    set_get_code_handler_getter,
    CodeResponseDTO,
    PendingResponseDTO,
    GoneResponseDTO,
)
from application.handlers.verification.get_code_handler import (
    GetCodeHandler,
    CodeResult,
)


@pytest.fixture
def app():
    """创建测试应用"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_handler():
    """创建 mock handler"""
    return Mock(spec=GetCodeHandler)


@pytest.fixture
def setup_handler(mock_handler):
    """设置 handler getter"""
    set_get_code_handler_getter(lambda: mock_handler)
    yield
    set_get_code_handler_getter(None)


class TestCodeRouteCompleted:
    """GET /code/{request_id} 已完成状态测试 (AC1)"""

    def test_returns_200_for_completed_request(
        self, client, mock_handler, setup_handler
    ):
        """测试已完成请求返回 200"""
        request_id = uuid4()
        mock_handler.handle.return_value = CodeResult(
            found=True,
            status="completed",
            data={
                "request_id": str(request_id),
                "type": "code",
                "value": "123456",
                "email": "test@example.com",
                "service": "claude",
                "received_at": "2025-01-15T10:30:00",
            },
        )

        response = client.get(f"/code/{request_id}")

        assert response.status_code == 200

    def test_returns_correct_data_for_code(
        self, client, mock_handler, setup_handler
    ):
        """测试返回正确的验证码数据"""
        request_id = uuid4()
        mock_handler.handle.return_value = CodeResult(
            found=True,
            status="completed",
            data={
                "request_id": str(request_id),
                "type": "code",
                "value": "123456",
                "email": "test@example.com",
                "service": "claude",
                "received_at": "2025-01-15T10:30:00",
            },
        )

        response = client.get(f"/code/{request_id}")
        data = response.json()

        assert data["request_id"] == str(request_id)
        assert data["type"] == "code"
        assert data["value"] == "123456"
        assert data["email"] == "test@example.com"
        assert data["service"] == "claude"
        assert data["received_at"] == "2025-01-15T10:30:00"

    def test_returns_correct_data_for_link(
        self, client, mock_handler, setup_handler
    ):
        """测试返回正确的链接数据"""
        request_id = uuid4()
        mock_handler.handle.return_value = CodeResult(
            found=True,
            status="completed",
            data={
                "request_id": str(request_id),
                "type": "link",
                "value": "https://verify.example.com/confirm?token=abc123",
                "email": "test@example.com",
                "service": "claude",
                "received_at": "2025-01-15T10:30:00",
            },
        )

        response = client.get(f"/code/{request_id}")
        data = response.json()

        assert data["type"] == "link"
        assert data["value"] == "https://verify.example.com/confirm?token=abc123"


class TestCodeRoutePending:
    """GET /code/{request_id} 等待中状态测试 (AC2)"""

    def test_returns_202_for_pending_request(
        self, client, mock_handler, setup_handler
    ):
        """测试等待中请求返回 202"""
        request_id = uuid4()
        mock_handler.handle.return_value = CodeResult(
            found=True,
            status="pending",
            message="正在等待验证邮件",
        )

        response = client.get(f"/code/{request_id}")

        assert response.status_code == 202

    def test_returns_pending_message(
        self, client, mock_handler, setup_handler
    ):
        """测试返回等待中消息"""
        request_id = uuid4()
        mock_handler.handle.return_value = CodeResult(
            found=True,
            status="pending",
            message="正在等待验证邮件",
        )

        response = client.get(f"/code/{request_id}")
        data = response.json()

        assert data["request_id"] == str(request_id)
        assert data["status"] == "pending"
        assert data["message"] == "正在等待验证邮件"


class TestCodeRouteNotFound:
    """GET /code/{request_id} 未找到状态测试 (AC3)"""

    def test_returns_404_for_not_found_request(
        self, client, mock_handler, setup_handler
    ):
        """测试请求不存在返回 404"""
        request_id = uuid4()
        mock_handler.handle.return_value = CodeResult(
            found=False,
            status="not_found",
        )

        response = client.get(f"/code/{request_id}")

        assert response.status_code == 404

    def test_returns_not_found_message(
        self, client, mock_handler, setup_handler
    ):
        """测试返回未找到消息"""
        request_id = uuid4()
        mock_handler.handle.return_value = CodeResult(
            found=False,
            status="not_found",
        )

        response = client.get(f"/code/{request_id}")
        data = response.json()

        assert data["detail"] == "Request not found"


class TestCodeRouteGone:
    """GET /code/{request_id} 已终止状态测试"""

    def test_returns_410_for_cancelled_request(
        self, client, mock_handler, setup_handler
    ):
        """测试已取消请求返回 410"""
        request_id = uuid4()
        mock_handler.handle.return_value = CodeResult(
            found=True,
            status="cancelled",
            message=None,
        )

        response = client.get(f"/code/{request_id}")

        assert response.status_code == 410

    def test_returns_cancelled_status(
        self, client, mock_handler, setup_handler
    ):
        """测试返回取消状态"""
        request_id = uuid4()
        mock_handler.handle.return_value = CodeResult(
            found=True,
            status="cancelled",
            message=None,
        )

        response = client.get(f"/code/{request_id}")
        data = response.json()

        assert data["request_id"] == str(request_id)
        assert data["status"] == "cancelled"

    def test_returns_410_for_failed_request(
        self, client, mock_handler, setup_handler
    ):
        """测试已失败请求返回 410"""
        request_id = uuid4()
        mock_handler.handle.return_value = CodeResult(
            found=True,
            status="failed",
            message="Webhook callback failed after 3 retries",
        )

        response = client.get(f"/code/{request_id}")

        assert response.status_code == 410

    def test_returns_failure_reason(
        self, client, mock_handler, setup_handler
    ):
        """测试返回失败原因"""
        request_id = uuid4()
        mock_handler.handle.return_value = CodeResult(
            found=True,
            status="failed",
            message="Webhook callback failed after 3 retries",
        )

        response = client.get(f"/code/{request_id}")
        data = response.json()

        assert data["status"] == "failed"
        assert data["reason"] == "Webhook callback failed after 3 retries"


class TestCodeRouteHandlerNotConfigured:
    """Handler 未配置测试"""

    def test_returns_500_when_handler_not_configured(self, client):
        """测试 handler 未配置返回 500"""
        set_get_code_handler_getter(None)

        response = client.get(f"/code/{uuid4()}")

        assert response.status_code == 500
        data = response.json()
        assert "Handler not configured" in data["detail"]


class TestCodeRouteInvalidUUID:
    """无效 UUID 测试"""

    def test_returns_422_for_invalid_uuid(
        self, client, mock_handler, setup_handler
    ):
        """测试无效 UUID 返回 422"""
        response = client.get("/code/not-a-valid-uuid")

        assert response.status_code == 422


class TestCodeResponseDTO:
    """CodeResponseDTO 测试"""

    def test_valid_code_response(self):
        """测试有效的验证码响应 DTO"""
        dto = CodeResponseDTO(
            request_id="test-id",
            type="code",
            value="123456",
            email="test@example.com",
            service="claude",
            received_at="2025-01-15T10:30:00",
        )

        assert dto.request_id == "test-id"
        assert dto.type == "code"
        assert dto.value == "123456"

    def test_valid_link_response(self):
        """测试有效的链接响应 DTO"""
        dto = CodeResponseDTO(
            request_id="test-id",
            type="link",
            value="https://verify.example.com/confirm",
            email="test@example.com",
            service="claude",
            received_at="2025-01-15T10:30:00",
        )

        assert dto.type == "link"


class TestPendingResponseDTO:
    """PendingResponseDTO 测试"""

    def test_valid_pending_response(self):
        """测试有效的等待中响应 DTO"""
        dto = PendingResponseDTO(
            request_id="test-id",
            status="pending",
            message="正在等待验证邮件",
        )

        assert dto.request_id == "test-id"
        assert dto.status == "pending"
        assert dto.message == "正在等待验证邮件"


class TestGoneResponseDTO:
    """GoneResponseDTO 测试"""

    def test_valid_cancelled_response(self):
        """测试有效的取消响应 DTO"""
        dto = GoneResponseDTO(
            request_id="test-id",
            status="cancelled",
            reason=None,
        )

        assert dto.status == "cancelled"

    def test_valid_failed_response(self):
        """测试有效的失败响应 DTO"""
        dto = GoneResponseDTO(
            request_id="test-id",
            status="failed",
            reason="Connection timeout",
        )

        assert dto.status == "failed"
        assert dto.reason == "Connection timeout"
