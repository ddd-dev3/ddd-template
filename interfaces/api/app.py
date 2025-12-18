"""
DDDApp - DDD 框架的 API 入口

集成 FastAPI 和 FastMCP，提供统一的 API 层。

特点：
- 自动集成 DDD 容器（Bootstrap）
- 同时支持 REST API 和 MCP 工具
- 通过 Mediator 处理 Command/Query
- 支持 Event 发布

用法：
    from interfaces.api import DDDApp

    app = DDDApp("MyService")

    # 定义 REST API
    @app.get("/users/{user_id}")
    async def get_user(user_id: int):
        query = GetUserQuery(user_id=user_id)
        return await app.mediator.send(query)

    # 定义 MCP 工具
    @app.mcp_tool
    async def create_user(username: str, email: str) -> dict:
        '''创建用户'''
        command = CreateUserCommand(username=username, email=email)
        return await app.mediator.send(command)

    # 运行
    app.run()
"""

from typing import Optional, Callable, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastmcp import FastMCP

from infrastructure.containers.bootstrap import bootstrap, Bootstrap
from infrastructure.config.settings import get_settings
from infrastructure.database.database_factory import init_database
from interfaces.api.middleware.api_key_middleware import APIKeyMiddleware


class DDDApp:
    """
    DDD 框架的统一 API 入口

    封装 FastAPI 和 FastMCP，提供便捷的 API 定义方式。
    """

    def __init__(
        self,
        title: str = "DDD Service",
        description: str = "",
        version: str = "1.0.0",
        mcp_path: str = "/mcp",
        enable_api_key_auth: bool = True,
        api_key_whitelist_paths: Optional[Set[str]] = None,
    ):
        self.title = title
        self.description = description
        self.version = version
        self.mcp_path = mcp_path
        self.enable_api_key_auth = enable_api_key_auth
        self.api_key_whitelist_paths = api_key_whitelist_paths

        # 初始化 Bootstrap（DDD 容器）
        self._bootstrap: Optional[Bootstrap] = None

        # 创建 FastMCP
        self._mcp = FastMCP(title)

        # 创建 FastAPI（稍后在 lifespan 中初始化）
        self._fastapi: Optional[FastAPI] = None

    @property
    def bootstrap(self) -> Bootstrap:
        """获取 Bootstrap 容器"""
        if self._bootstrap is None:
            self._bootstrap = bootstrap()
        return self._bootstrap

    @property
    def mediator(self):
        """获取 Mediator 实例"""
        return self.bootstrap.app().mediator()

    @property
    def fastapi(self) -> FastAPI:
        """获取 FastAPI 实例"""
        if self._fastapi is None:
            self._fastapi = self._create_fastapi()
        return self._fastapi

    @property
    def mcp(self) -> FastMCP:
        """获取 FastMCP 实例"""
        return self._mcp

    def _create_fastapi(self) -> FastAPI:
        """创建 FastAPI 实例并挂载 MCP"""
        # 获取 MCP ASGI 应用
        mcp_app = self._mcp.http_app(path=self.mcp_path)

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # 初始化 Bootstrap
            self._bootstrap = bootstrap()
            # 初始化数据库（自动创建表）
            engine = self._bootstrap.infra.db_engine()
            init_database(engine)
            # 使用 MCP 的 lifespan
            async with mcp_app.lifespan(app):
                yield

        app = FastAPI(
            title=self.title,
            description=self.description,
            version=self.version,
            lifespan=lifespan,
        )

        # 添加 API Key 认证中间件（保护所有路由包括 /tools）
        if self.enable_api_key_auth:
            settings = get_settings()
            app.add_middleware(
                APIKeyMiddleware,
                api_key=settings.api_key,
                whitelist_paths=self.api_key_whitelist_paths,
            )

        # 挂载 MCP（在中间件之后，受保护）
        app.mount(self.mcp_path, mcp_app)

        return app

    # ============ FastAPI 路由装饰器代理 ============

    def get(self, path: str, **kwargs):
        """GET 路由装饰器"""
        return self.fastapi.get(path, **kwargs)

    def post(self, path: str, **kwargs):
        """POST 路由装饰器"""
        return self.fastapi.post(path, **kwargs)

    def put(self, path: str, **kwargs):
        """PUT 路由装饰器"""
        return self.fastapi.put(path, **kwargs)

    def delete(self, path: str, **kwargs):
        """DELETE 路由装饰器"""
        return self.fastapi.delete(path, **kwargs)

    def patch(self, path: str, **kwargs):
        """PATCH 路由装饰器"""
        return self.fastapi.patch(path, **kwargs)

    # ============ FastMCP 装饰器代理 ============

    def mcp_tool(self, func: Optional[Callable] = None, **kwargs):
        """
        MCP 工具装饰器

        用法：
            @app.mcp_tool
            async def my_tool(param: str) -> dict:
                '''工具描述'''
                return {"result": param}
        """
        return self._mcp.tool(func, **kwargs) if func else self._mcp.tool(**kwargs)

    def mcp_resource(self, uri: str, **kwargs):
        """
        MCP 资源装饰器

        用法：
            @app.mcp_resource("config://version")
            def get_version():
                return "1.0.0"
        """
        return self._mcp.resource(uri, **kwargs)

    def mcp_prompt(self, func: Optional[Callable] = None, **kwargs):
        """
        MCP Prompt 装饰器

        用法：
            @app.mcp_prompt
            def summarize(text: str) -> str:
                '''生成摘要提示'''
                return f"请总结以下内容：{text}"
        """
        return self._mcp.prompt(func, **kwargs) if func else self._mcp.prompt(**kwargs)

    # ============ 运行 ============

    def run(self, host: str = "0.0.0.0", port: int = 8000, **kwargs):
        """
        运行服务

        Args:
            host: 主机地址
            port: 端口号
        """
        import uvicorn

        uvicorn.run(self.fastapi, host=host, port=port, **kwargs)

    def get_asgi_app(self) -> FastAPI:
        """获取 ASGI 应用（用于部署）"""
        return self.fastapi


def create_app(
    title: str = "DDD Service",
    description: str = "",
    version: str = "1.0.0",
) -> DDDApp:
    """
    创建 DDDApp 实例的工厂函数

    Args:
        title: 服务名称
        description: 服务描述
        version: 版本号

    Returns:
        DDDApp 实例
    """
    return DDDApp(title=title, description=description, version=version)
