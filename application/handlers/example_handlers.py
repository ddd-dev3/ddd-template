"""
示例处理器

演示两种 Handler 定义方式：
1. 函数式 - 简单场景，无需依赖注入
2. 类式 - 需要依赖注入（如 UoW、Repository）
"""

from mediatr import Mediator
from application.commands import CommandResult
from application.commands.example_commands import CreateUserCommand, UpdateUserCommand
from infrastructure.database.unit_of_work import UnitOfWork


# ============ 方式 1：函数式 Handler ============
# 适用于简单逻辑，无需依赖注入

@Mediator.handler
async def handle_update_user(request: UpdateUserCommand) -> CommandResult:
    """
    更新用户处理器（函数式）

    无需依赖注入的简单场景。
    """
    # 这里只是示例，实际需要调用仓储
    print(f"Updating user {request.user_id}: name={request.name}, email={request.email}")
    return CommandResult.ok({"user_id": request.user_id, "updated": True})


# ============ 方式 2：类式 Handler ============
# 适用于需要依赖注入的场景

@Mediator.handler
class CreateUserHandler:
    """
    创建用户处理器（类式）

    需要依赖注入 UnitOfWork。
    在 AppContainer 中注册后，依赖会自动注入。
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def handle(self, request: CreateUserCommand) -> CommandResult:
        """处理创建用户命令"""
        # 这里只是示例，实际需要：
        # 1. 创建 User 实体
        # 2. 通过 Repository 保存
        # 3. 提交事务

        print(f"Creating user: name={request.name}, email={request.email}")
        print(f"Using UoW: {self.uow}")

        # 模拟创建成功
        user_id = 1
        return CommandResult.ok({"id": user_id, "name": request.name, "email": request.email})
