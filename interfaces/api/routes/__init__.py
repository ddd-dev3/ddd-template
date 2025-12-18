"""
REST API 路由

定义 REST API 端点。
"""

from interfaces.api.routes.accounts import router as accounts_router
from interfaces.api.routes.code import router as code_router
from interfaces.api.routes.register import router as register_router

__all__ = ["accounts_router", "code_router", "register_router"]
