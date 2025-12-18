"""注册等待请求 API 路由测试"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from interfaces.api.routes.register import (
    router,
    set_register_handler_getter,
    RegisterWaitRequestDTO,
    RegisterWaitResponseDTO,
)
from application.commands.verification.register_wait_request import (
    RegisterWaitRequestHandler,
    RegisterWaitRequestResult,
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
    return Mock(spec=RegisterWaitRequestHandler)


@pytest.fixture
def setup_handler(mock_handler):
    """设置 handler getter"""
    set_register_handler_getter(lambda: mock_handler)
    yield
    set_register_handler_getter(None)


class TestRegisterWaitRequestRoute:
    """POST /register 路由测试"""

    def test_register_success(self, client, mock_handler, setup_handler):
        """测试成功创建等待请求 (AC1)"""
        # 设置 mock 返回成功结果
        request_id = uuid4()
        mock_handler.handle.return_value = RegisterWaitRequestResult(
            success=True,
            request_id=request_id,
            message="Wait request created successfully",
        )

        # 发送请求
        response = client.post(
            "/register",
            json={
                "email": "test@example.com",
                "service": "claude",
                "callback_url": "https://api.example.com/callback",
            },
        )

        # 验证响应
        assert response.status_code == 201
        data = response.json()
        assert data["request_id"] == str(request_id)
        assert data["message"] == "Wait request created successfully"

        # 验证 handler 被调用
        mock_handler.handle.assert_called_once()
        command = mock_handler.handle.call_args[0][0]
        assert command.email == "test@example.com"
        assert command.service_name == "claude"
        assert "api.example.com/callback" in command.callback_url

    def test_register_mailbox_not_found(self, client, mock_handler, setup_handler):
        """测试邮箱不存在返回 404 (AC3)"""
        # 设置 mock 返回邮箱未找到结果
        mock_handler.handle.return_value = RegisterWaitRequestResult(
            success=False,
            message="Mailbox not found: test@example.com",
            error_code="MAILBOX_NOT_FOUND",
        )

        # 发送请求
        response = client.post(
            "/register",
            json={
                "email": "test@example.com",
                "service": "claude",
                "callback_url": "https://api.example.com/callback",
            },
        )

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert "Mailbox not found" in data["detail"]

    def test_register_mailbox_occupied(self, client, mock_handler, setup_handler):
        """测试邮箱已被占用返回 409 (AC2)"""
        # 设置 mock 返回邮箱已占用结果
        mock_handler.handle.return_value = RegisterWaitRequestResult(
            success=False,
            message="Mailbox already occupied by: other_service",
            error_code="MAILBOX_OCCUPIED",
        )

        # 发送请求
        response = client.post(
            "/register",
            json={
                "email": "test@example.com",
                "service": "claude",
                "callback_url": "https://api.example.com/callback",
            },
        )

        # 验证响应
        assert response.status_code == 409
        data = response.json()
        assert "already occupied" in data["detail"]

    def test_register_handler_not_configured(self, client):
        """测试 handler 未配置返回 500"""
        # 确保没有设置 handler
        set_register_handler_getter(None)

        # 发送请求
        response = client.post(
            "/register",
            json={
                "email": "test@example.com",
                "service": "claude",
                "callback_url": "https://api.example.com/callback",
            },
        )

        # 验证响应
        assert response.status_code == 500
        data = response.json()
        assert "Handler not configured" in data["detail"]


class TestRegisterWaitRequestValidation:
    """请求参数验证测试"""

    def test_missing_email(self, client, mock_handler, setup_handler):
        """测试缺少 email 参数"""
        response = client.post(
            "/register",
            json={
                "service": "claude",
                "callback_url": "https://api.example.com/callback",
            },
        )

        assert response.status_code == 422

    def test_missing_service(self, client, mock_handler, setup_handler):
        """测试缺少 service 参数"""
        response = client.post(
            "/register",
            json={
                "email": "test@example.com",
                "callback_url": "https://api.example.com/callback",
            },
        )

        assert response.status_code == 422

    def test_missing_callback_url(self, client, mock_handler, setup_handler):
        """测试缺少 callback_url 参数"""
        response = client.post(
            "/register",
            json={
                "email": "test@example.com",
                "service": "claude",
            },
        )

        assert response.status_code == 422

    def test_invalid_callback_url(self, client, mock_handler, setup_handler):
        """测试无效的 callback_url"""
        response = client.post(
            "/register",
            json={
                "email": "test@example.com",
                "service": "claude",
                "callback_url": "not-a-valid-url",
            },
        )

        assert response.status_code == 422

    def test_empty_email(self, client, mock_handler, setup_handler):
        """测试空 email"""
        response = client.post(
            "/register",
            json={
                "email": "",
                "service": "claude",
                "callback_url": "https://api.example.com/callback",
            },
        )

        assert response.status_code == 422

    def test_empty_service(self, client, mock_handler, setup_handler):
        """测试空 service"""
        response = client.post(
            "/register",
            json={
                "email": "test@example.com",
                "service": "",
                "callback_url": "https://api.example.com/callback",
            },
        )

        assert response.status_code == 422


class TestRegisterWaitRequestDTO:
    """RegisterWaitRequestDTO 测试"""

    def test_valid_dto(self):
        """测试有效的 DTO"""
        dto = RegisterWaitRequestDTO(
            email="test@example.com",
            service="claude",
            callback_url="https://api.example.com/callback",
        )

        assert dto.email == "test@example.com"
        assert dto.service == "claude"
        assert str(dto.callback_url) == "https://api.example.com/callback"

    def test_dto_with_complex_url(self):
        """测试复杂 URL"""
        dto = RegisterWaitRequestDTO(
            email="test@example.com",
            service="claude",
            callback_url="https://api.example.com/callback?token=abc&id=123",
        )

        assert "token=abc" in str(dto.callback_url)


class TestRegisterWaitResponseDTO:
    """RegisterWaitResponseDTO 测试"""

    def test_valid_response_dto(self):
        """测试有效的响应 DTO"""
        request_id = uuid4()
        dto = RegisterWaitResponseDTO(
            request_id=request_id,
            message="Wait request created successfully",
        )

        assert dto.request_id == request_id
        assert dto.message == "Wait request created successfully"
