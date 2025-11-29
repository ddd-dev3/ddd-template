"""
API 示例

演示如何使用 DDDApp 创建 REST API 和 MCP 工具。

运行：
    cd ddd-framework
    uv run python examples/api_example.py

测试 REST API：
    curl http://localhost:8000/
    curl http://localhost:8000/users/1
    curl -X POST http://localhost:8000/users -H "Content-Type: application/json" -d '{"username":"test","email":"test@test.com"}'

MCP 工具地址：
    http://localhost:8000/tools/mcp/
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional
from pydantic import BaseModel

from interfaces.api import DDDApp

# 创建 DDDApp
app = DDDApp(
    title="用户服务",
    description="演示 DDD 框架的 API 层",
    version="1.0.0",
)


# ============ Pydantic 模型 ============

class UserCreate(BaseModel):
    username: str
    email: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str


# ============ 模拟数据 ============

fake_users = {
    1: {"id": 1, "username": "张三", "email": "zhangsan@test.com"},
    2: {"id": 2, "username": "李四", "email": "lisi@test.com"},
}


# ============ REST API ============

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "用户服务",
        "version": "1.0.0",
        "endpoints": {
            "rest": ["/users", "/users/{id}"],
            "mcp": "/tools/mcp/",
        },
    }


@app.get("/users")
async def list_users():
    """获取所有用户"""
    return list(fake_users.values())


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """获取单个用户"""
    if user_id in fake_users:
        return fake_users[user_id]
    return {"error": "用户不存在"}


@app.post("/users")
async def create_user(user: UserCreate):
    """
    创建用户

    在实际项目中，这里会：
    1. 创建 CreateUserCommand
    2. 通过 Mediator 发送命令
    3. Handler 处理命令并发布 UserCreatedEvent
    4. Event Handler 发送邮件、记录日志等

    示例：
        command = CreateUserCommand(username=user.username, email=user.email)
        result = await app.mediator.send(command)
    """
    new_id = max(fake_users.keys()) + 1
    new_user = {"id": new_id, "username": user.username, "email": user.email}
    fake_users[new_id] = new_user

    # 这里可以发布事件
    # from infrastructure.events import emit
    # from application.events.example_events import UserCreatedEvent
    # emit(UserCreatedEvent(aggregate_id=uuid4(), user_id=new_id, username=user.username, email=user.email))

    return new_user


# ============ MCP 工具 ============

@app.mcp_tool
async def get_user_info(user_id: int) -> dict:
    """
    获取用户信息

    通过用户 ID 获取用户详细信息。

    Args:
        user_id: 用户 ID

    Returns:
        用户信息字典，包含 id, username, email
    """
    if user_id in fake_users:
        return fake_users[user_id]
    return {"error": f"用户 {user_id} 不存在"}


@app.mcp_tool
async def search_users(keyword: str) -> list:
    """
    搜索用户

    根据关键词搜索用户名或邮箱。

    Args:
        keyword: 搜索关键词

    Returns:
        匹配的用户列表
    """
    results = []
    for user in fake_users.values():
        if keyword.lower() in user["username"].lower() or keyword.lower() in user["email"].lower():
            results.append(user)
    return results


@app.mcp_tool
async def create_user_tool(username: str, email: str) -> dict:
    """
    创建新用户

    创建一个新用户账号。

    Args:
        username: 用户名
        email: 邮箱地址

    Returns:
        创建的用户信息
    """
    new_id = max(fake_users.keys()) + 1
    new_user = {"id": new_id, "username": username, "email": email}
    fake_users[new_id] = new_user
    return {"success": True, "user": new_user}


# ============ MCP 资源 ============

@app.mcp_resource("config://version")
def get_version():
    """获取服务版本"""
    return "1.0.0"


@app.mcp_resource("users://{user_id}/profile")
def get_user_profile(user_id: int):
    """获取用户 Profile"""
    if user_id in fake_users:
        return fake_users[user_id]
    return {"error": "用户不存在"}


# ============ MCP Prompt ============

@app.mcp_prompt
def analyze_user(user_id: int) -> str:
    """
    分析用户

    生成一个提示，让 AI 分析指定用户的信息。
    """
    if user_id in fake_users:
        user = fake_users[user_id]
        return f"""请分析以下用户信息：

用户 ID: {user['id']}
用户名: {user['username']}
邮箱: {user['email']}

请提供：
1. 用户名风格分析
2. 邮箱域名类型
3. 可能的用户画像
"""
    return f"用户 {user_id} 不存在"


# ============ 入口 ============

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 启动用户服务")
    print("=" * 50)
    print()
    print("REST API:")
    print("  GET  http://localhost:8000/")
    print("  GET  http://localhost:8000/users")
    print("  GET  http://localhost:8000/users/{id}")
    print("  POST http://localhost:8000/users")
    print()
    print("MCP 工具:")
    print("  http://localhost:8000/tools/mcp/")
    print()
    print("=" * 50)

    app.run(port=8000)
