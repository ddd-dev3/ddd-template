"""
Mail Service - 验证码服务 API 入口

运行：
    uv run python main.py

或使用 uvicorn：
    uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

API 文档：
    http://localhost:8000/docs
"""

from interfaces.api import DDDApp
from interfaces.api.routes import accounts_router, code_router, register_router

# 导入 handler getter 设置函数
from interfaces.api.routes.accounts import (
    set_handler_getter as set_add_handler,
    set_list_handler_getter,
    set_delete_handler_getter,
)
from interfaces.api.routes.register import (
    set_register_handler_getter,
    set_cancel_handler_getter,
)
from interfaces.api.routes.code import set_get_code_handler_getter

# 创建 DDDApp
ddd_app = DDDApp(
    title="Mail Service",
    description="邮箱验证码提取服务 - 自动收取邮件、提取验证码/链接、Webhook 回调",
    version="1.0.0",
    enable_api_key_auth=True,
    api_key_whitelist_paths={"/docs", "/openapi.json", "/redoc"},
)

# 获取 DI 容器
container = ddd_app.bootstrap.app

# 注册 Handler Getters（关键！连接 DI 容器到路由）
# 邮箱账号 handlers
set_add_handler(container.add_mailbox_account_handler)
set_list_handler_getter(container.list_mailbox_accounts_handler)
set_delete_handler_getter(container.delete_mailbox_account_handler)

# 验证请求 handlers
set_register_handler_getter(container.register_wait_request_handler)
set_cancel_handler_getter(container.cancel_wait_request_handler)
set_get_code_handler_getter(container.get_code_handler)

# 注册路由
ddd_app.fastapi.include_router(accounts_router, prefix="/api/v1", tags=["邮箱账号"])
ddd_app.fastapi.include_router(register_router, prefix="/api/v1", tags=["等待请求"])
ddd_app.fastapi.include_router(code_router, prefix="/api/v1", tags=["验证码查询"])


# 根路由
@ddd_app.get("/")
async def root():
    """服务信息"""
    return {
        "service": "Mail Service",
        "version": "1.0.0",
        "description": "邮箱验证码提取服务",
        "docs": "/docs",
        "endpoints": {
            "accounts": "/api/v1/accounts",
            "register": "/api/v1/register",
            "code": "/api/v1/code/{request_id}",
        },
    }


# 健康检查
@ddd_app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


# 导出 FastAPI app (用于 uvicorn)
app = ddd_app.fastapi


if __name__ == "__main__":
    print("=" * 50)
    print("启动 Mail Service")
    print("=" * 50)
    print()
    print("API 端点:")
    print("  POST /api/v1/accounts     - 添加邮箱账号")
    print("  GET  /api/v1/accounts     - 查询邮箱列表")
    print("  DELETE /api/v1/accounts/{id} - 删除邮箱")
    print()
    print("  POST /api/v1/register     - 注册等待请求")
    print("  DELETE /api/v1/register/{id} - 取消等待")
    print()
    print("  GET  /api/v1/code/{id}    - 查询验证码")
    print()
    print("文档: http://localhost:8000/docs")
    print("=" * 50)

    ddd_app.run(host="0.0.0.0", port=8000)
