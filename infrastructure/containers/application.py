"""
应用容器（AppContainer）

管理应用层组件：Mediator、命令/查询处理器、应用服务等。
依赖 InfraContainer 获取基础设施。

Handler 注册流程：
1. 在此容器中定义 Handler 的 Provider
2. 在 wire_handlers() 中注册到 MediatorFactory
3. Mediator 会自动从容器获取 Handler 实例（依赖已注入）
"""

from typing import TYPE_CHECKING
from dependency_injector import containers, providers

from infrastructure.mediator import create_mediator, get_mediator_factory

# 导入示例 Handlers
from application.handlers.example_handlers import CreateUserHandler

if TYPE_CHECKING:
    from .infrastructure import InfraContainer


class AppContainer(containers.DeclarativeContainer):
    """应用容器 - 管理应用层服务"""

    # 依赖基础设施容器
    infra = providers.DependenciesContainer()

    # ============ Mediator ============
    mediator = providers.Singleton(create_mediator)

    # ============ 命令处理器 ============
    # 需要依赖注入的 Handler 在这里注册

    # 示例：CreateUserHandler 需要注入 UnitOfWork
    create_user_handler = providers.Factory(
        CreateUserHandler,
        uow=infra.unit_of_work
    )

    # ============ 查询处理器 ============
    # 示例：
    # get_user_handler = providers.Factory(
    #     GetUserHandler,
    #     session_factory=infra.db_session_factory
    # )

    # ============ 应用服务 ============
    # 示例：
    # user_service = providers.Factory(
    #     UserService,
    #     uow=infra.unit_of_work,
    #     email_sender=infra.email_sender
    # )


def wire_handlers(container: AppContainer) -> None:
    """
    将 Handler Provider 注册到 MediatorFactory

    在应用启动时调用此函数，将容器中的 Handler 与 Mediator 连接。

    使用示例：
        from infrastructure.containers import bootstrap
        from infrastructure.containers.application import wire_handlers

        boot = bootstrap()
        wire_handlers(boot.app)

    添加新 Handler 的步骤：
        1. 在 AppContainer 中添加 Handler Provider
        2. 在此函数中注册到 factory
    """
    factory = get_mediator_factory()

    # 注册需要 DI 的 Handlers
    factory.register_handler(CreateUserHandler, container.create_user_handler)

    # 添加更多 Handler：
    # factory.register_handler(GetUserHandler, container.get_user_handler)
