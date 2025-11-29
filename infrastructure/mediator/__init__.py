"""
Mediator 模块

提供 CQRS 模式支持，将 Command/Query 分发到对应的 Handler。

使用 mediatr-py 库，与 dependency-injector 容器集成。

使用示例：
    from mediatr import Mediator
    from infrastructure.mediator import create_mediator, register_handler

    # 注册 Handler
    register_handler(CreateUserHandler, container.create_user_handler)

    # 创建 Mediator
    mediator = create_mediator()

    # 发送命令
    result = await mediator.send_async(CreateUserCommand(name="test"))
"""

from mediatr import Mediator

from .setup import (
    MediatorFactory,
    get_mediator_factory,
    create_mediator,
    register_handler,
)

__all__ = [
    # 来自 mediatr
    "Mediator",
    # 本模块
    "MediatorFactory",
    "get_mediator_factory",
    "create_mediator",
    "register_handler",
]
