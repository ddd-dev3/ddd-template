"""
处理器（Handlers）

处理器负责执行命令和查询的具体逻辑。

两种定义方式：

1. 函数式（简单，无需依赖注入）：
    @Mediator.handler
    async def handle_create_user(request: CreateUserCommand):
        return {"id": 1}

2. 类式（需要依赖注入）：
    @Mediator.handler
    class CreateUserHandler:
        def __init__(self, uow: UnitOfWork):
            self.uow = uow

        async def handle(self, request: CreateUserCommand):
            return {"id": 1}
"""
