"""
API Key 认证中间件

使用 Starlette 中间件模式，同时保护 REST API 和 FastMCP 路由。
"""

import secrets
from typing import Set, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def mask_api_key(api_key: str | None) -> str:
    """
    掩码 API Key，只显示前3位和后3位

    Args:
        api_key: 原始 API Key（可为 None）

    Returns:
        掩码后的 API Key，如 "sk-***abc"
    """
    if api_key is None or api_key == "":
        return "***"
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:3]}***{api_key[-3:]}"


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    API Key 认证中间件

    同时保护 REST API 和 FastMCP 路由（/tools/*）

    特性：
    - 使用 secrets.compare_digest 防止时序攻击
    - 支持白名单路径配置
    - 返回标准 JSON 错误响应
    """

    # 默认不需要认证的路径白名单
    DEFAULT_WHITELIST_PATHS: Set[str] = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    def __init__(
        self,
        app,
        api_key: str,
        whitelist_paths: Optional[Set[str]] = None,
        header_name: str = "X-API-Key"
    ):
        """
        初始化中间件

        Args:
            app: ASGI 应用
            api_key: 有效的 API Key
            whitelist_paths: 额外的白名单路径（可选）
            header_name: API Key header 名称，默认 "X-API-Key"
        """
        super().__init__(app)
        self.api_key = api_key
        self.header_name = header_name

        # 合并默认白名单和用户自定义白名单
        self.whitelist_paths = self.DEFAULT_WHITELIST_PATHS.copy()
        if whitelist_paths:
            self.whitelist_paths.update(whitelist_paths)

    def _is_whitelisted(self, path: str) -> bool:
        """
        检查路径是否在白名单中

        Args:
            path: 请求路径

        Returns:
            是否在白名单中
        """
        # 精确匹配
        if path in self.whitelist_paths:
            return True

        # 检查是否以白名单路径开头（支持子路径）
        for whitelist_path in self.whitelist_paths:
            if path.startswith(whitelist_path + "/"):
                return True

        return False

    async def dispatch(self, request: Request, call_next):
        """
        处理请求

        Args:
            request: HTTP 请求
            call_next: 下一个处理器

        Returns:
            HTTP 响应
        """
        # 白名单路径跳过认证
        if self._is_whitelisted(request.url.path):
            return await call_next(request)

        # 获取 API Key
        api_key = request.headers.get(self.header_name)

        # 检查 API Key 是否存在
        if api_key is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "API Key required"}
            )

        # 安全比较防止时序攻击
        if not secrets.compare_digest(api_key, self.api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API Key"}
            )

        return await call_next(request)
