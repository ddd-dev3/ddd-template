"""
API Key 认证中间件测试

测试验收标准：
- AC1: 有效 API Key 请求成功
- AC2: 无效 API Key 请求拒绝
- AC3: 缺少 API Key 请求拒绝
- AC4: API Key 不在日志中明文记录
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from interfaces.api.middleware.api_key_middleware import APIKeyMiddleware, mask_api_key


# 测试用的 API Key
TEST_API_KEY = "test-api-key-12345"


@pytest.fixture
def app():
    """创建测试用 FastAPI 应用"""
    app = FastAPI()

    # 添加 API Key 中间件
    app.add_middleware(
        APIKeyMiddleware,
        api_key=TEST_API_KEY,
    )

    # 添加测试路由
    @app.get("/test")
    def test_endpoint():
        return {"message": "success"}

    @app.get("/health")
    def health_endpoint():
        return {"status": "healthy"}

    @app.get("/docs")
    def docs_endpoint():
        return {"docs": "swagger"}

    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


class TestAPIKeyMiddleware:
    """API Key 中间件测试类"""

    def test_valid_api_key_allows_request(self, client):
        """
        AC1: 有效 API Key 请求成功

        Given: 请求携带有效的 X-API-Key header
        When: 发送 API 请求
        Then: 请求被允许继续处理，返回正常响应
        """
        response = client.get(
            "/test",
            headers={"X-API-Key": TEST_API_KEY}
        )

        assert response.status_code == 200
        assert response.json() == {"message": "success"}

    def test_invalid_api_key_returns_401(self, client):
        """
        AC2: 无效 API Key 请求拒绝

        Given: 请求携带无效的 X-API-Key header
        When: 发送 API 请求
        Then: 返回 401 Unauthorized，响应体包含错误信息
        """
        response = client.get(
            "/test",
            headers={"X-API-Key": "invalid-key"}
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid API Key"}

    def test_missing_api_key_returns_401(self, client):
        """
        AC3: 缺少 API Key 请求拒绝

        Given: 请求缺少 X-API-Key header
        When: 发送 API 请求
        Then: 返回 401 Unauthorized，响应体包含错误信息
        """
        response = client.get("/test")

        assert response.status_code == 401
        assert response.json() == {"detail": "API Key required"}

    def test_whitelist_path_health_bypasses_auth(self, client):
        """
        白名单路径 /health 跳过认证
        """
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_whitelist_path_docs_bypasses_auth(self, client):
        """
        白名单路径 /docs 跳过认证

        注意：FastAPI 内置的 /docs 返回 Swagger UI HTML
        """
        response = client.get("/docs")

        # FastAPI 内置 /docs 返回 200 (Swagger UI HTML) 或重定向
        # 关键是不返回 401 Unauthorized
        assert response.status_code in (200, 307)


class TestMaskApiKey:
    """API Key 掩码函数测试类"""

    def test_mask_normal_api_key(self):
        """
        AC4: 正常长度 API Key 掩码

        只显示前3位和后3位
        """
        api_key = "sk-test-api-key-12345"
        masked = mask_api_key(api_key)

        assert masked == "sk-***345"
        assert "test-api-key" not in masked  # 中间部分不应出现

    def test_mask_short_api_key(self):
        """
        短 API Key（<=8字符）完全掩码
        """
        short_key = "12345678"
        masked = mask_api_key(short_key)

        assert masked == "***"

    def test_mask_very_short_api_key(self):
        """
        非常短的 API Key 完全掩码
        """
        short_key = "abc"
        masked = mask_api_key(short_key)

        assert masked == "***"

    def test_mask_empty_api_key(self):
        """
        空 API Key 返回掩码
        """
        masked = mask_api_key("")

        assert masked == "***"

    def test_mask_none_api_key(self):
        """
        None API Key 返回掩码
        """
        masked = mask_api_key(None)

        assert masked == "***"

    def test_mask_9_char_api_key(self):
        """
        9字符 API Key 显示前3后3
        """
        api_key = "123456789"
        masked = mask_api_key(api_key)

        assert masked == "123***789"

    def test_masked_key_not_in_original(self):
        """
        AC4: 掩码后的 API Key 不包含原始敏感部分

        确保日志安全
        """
        original = "super-secret-api-key-abc123"
        masked = mask_api_key(original)

        # 中间敏感部分不应出现在掩码版本中
        assert "secret" not in masked
        assert "api-key" not in masked

        # 只有前3和后3字符
        assert masked == "sup***123"


class TestAPIKeyMiddlewareWithCustomWhitelist:
    """自定义白名单测试"""

    @pytest.fixture
    def app_with_custom_whitelist(self):
        """创建带自定义白名单的应用"""
        app = FastAPI()

        app.add_middleware(
            APIKeyMiddleware,
            api_key=TEST_API_KEY,
            whitelist_paths={"/custom", "/public"},
        )

        @app.get("/custom")
        def custom_endpoint():
            return {"custom": True}

        @app.get("/public")
        def public_endpoint():
            return {"public": True}

        @app.get("/private")
        def private_endpoint():
            return {"private": True}

        return app

    @pytest.fixture
    def custom_client(self, app_with_custom_whitelist):
        return TestClient(app_with_custom_whitelist)

    def test_custom_whitelist_bypasses_auth(self, custom_client):
        """自定义白名单路径跳过认证"""
        response = custom_client.get("/custom")
        assert response.status_code == 200

        response = custom_client.get("/public")
        assert response.status_code == 200

    def test_non_whitelist_requires_auth(self, custom_client):
        """非白名单路径需要认证"""
        response = custom_client.get("/private")
        assert response.status_code == 401

        # 带有效 API Key 可以访问
        response = custom_client.get(
            "/private",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200


class TestAPIKeyMiddlewareMCPProtection:
    """MCP 路由保护测试"""

    @pytest.fixture
    def app_with_mcp_route(self):
        """创建带 MCP 路由的应用"""
        app = FastAPI()
        app.add_middleware(APIKeyMiddleware, api_key=TEST_API_KEY)

        # 模拟 MCP 路由
        @app.get("/mcp/tools")
        def mcp_tools():
            return {"tools": []}

        @app.get("/mcp/sse")
        def mcp_sse():
            return {"sse": True}

        return app

    @pytest.fixture
    def mcp_client(self, app_with_mcp_route):
        return TestClient(app_with_mcp_route)

    def test_mcp_route_requires_auth(self, mcp_client):
        """MCP 路由需要认证"""
        response = mcp_client.get("/mcp/tools")
        assert response.status_code == 401

    def test_mcp_route_with_valid_key(self, mcp_client):
        """MCP 路由带有效 Key 可访问"""
        response = mcp_client.get(
            "/mcp/tools",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200


class TestAPIKeyMiddlewareSecurityComparison:
    """安全比较测试（时序攻击防护）"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.add_middleware(APIKeyMiddleware, api_key=TEST_API_KEY)

        @app.get("/test")
        def test_endpoint():
            return {"ok": True}

        return app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_similar_key_rejected(self, client):
        """相似但不同的 Key 被拒绝"""
        # 只差一个字符
        similar_key = TEST_API_KEY[:-1] + "X"

        response = client.get(
            "/test",
            headers={"X-API-Key": similar_key}
        )

        assert response.status_code == 401

    def test_empty_key_rejected(self, client):
        """空字符串 Key 被拒绝"""
        response = client.get(
            "/test",
            headers={"X-API-Key": ""}
        )

        assert response.status_code == 401

    def test_whitespace_key_rejected(self, client):
        """空白字符 Key 被拒绝"""
        response = client.get(
            "/test",
            headers={"X-API-Key": "   "}
        )

        assert response.status_code == 401
