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

# 导入邮箱 Handlers
from application.handlers.mailbox.add_mailbox_account_handler import AddMailboxAccountHandler
from application.handlers.mailbox.list_mailbox_accounts_handler import ListMailboxAccountsHandler
from application.handlers.mailbox.delete_mailbox_account_handler import DeleteMailboxAccountHandler

# 导入邮件应用服务
from application.mail.services.async_mail_polling_service import AsyncMailPollingService

# 导入 AI 应用服务
from application.ai.services.ai_extraction_service import AiExtractionService

# 导入验证 Handlers
from application.commands.verification import (
    RegisterWaitRequestHandler,
    CancelWaitRequestHandler,
)
from application.handlers.verification import GetCodeHandler

if TYPE_CHECKING:
    from .infrastructure import InfraContainer


class AppContainer(containers.DeclarativeContainer):
    """应用容器 - 管理应用层服务"""

    # 依赖配置容器
    config = providers.DependenciesContainer()

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

    # 邮箱 Handler
    add_mailbox_account_handler = providers.Factory(
        AddMailboxAccountHandler,
        repository=infra.mailbox_account_repository,
        imap_validator=infra.imap_connection_validator,
        encryption_key=config.settings.provided.encryption_key,
    )

    # 删除邮箱 Handler
    delete_mailbox_account_handler = providers.Factory(
        DeleteMailboxAccountHandler,
        repository=infra.mailbox_account_repository,
    )

    # ============ 查询处理器 ============
    # 邮箱查询 Handler
    list_mailbox_accounts_handler = providers.Factory(
        ListMailboxAccountsHandler,
        repository=infra.mailbox_account_repository,
    )

    # ============ 验证处理器 ============
    # 注册等待请求 Handler
    register_wait_request_handler = providers.Factory(
        RegisterWaitRequestHandler,
        mailbox_repo=infra.mailbox_account_repository,
        wait_request_repo=infra.wait_request_repository,
    )

    # 取消等待请求 Handler
    cancel_wait_request_handler = providers.Factory(
        CancelWaitRequestHandler,
        wait_request_repo=infra.wait_request_repository,
        mailbox_repo=infra.mailbox_account_repository,
    )

    # 查询验证码 Handler
    get_code_handler = providers.Factory(
        GetCodeHandler,
        wait_request_repo=infra.wait_request_repository,
    )

    # ============ 应用服务 ============
    # 示例：
    # user_service = providers.Factory(
    #     UserService,
    #     uow=infra.unit_of_work,
    #     email_sender=infra.email_sender
    # )

    # 邮件轮询服务（单例，整个应用只需一个实例）
    # 注意: email_repository 使用 .provider 传递工厂，确保线程安全
    mail_polling_service = providers.Singleton(
        AsyncMailPollingService,
        mailbox_repository=infra.mailbox_account_repository,
        imap_service=infra.imap_mail_fetch_service,
        email_repository=infra.email_repository.provider,  # 传递工厂函数，而非实例
        interval=config.settings.provided.mail_polling_interval,
        max_concurrent_connections=config.settings.provided.mail_max_concurrent_connections,
        mailbox_poll_timeout=config.settings.provided.mail_poll_timeout,
    )

    # AI 提取服务（单例）
    ai_extraction_service = providers.Singleton(
        AiExtractionService,
        extractor=infra.llm_verification_extractor,
    )


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

    # 注册邮箱 Handlers
    factory.register_handler(AddMailboxAccountHandler, container.add_mailbox_account_handler)
    factory.register_handler(ListMailboxAccountsHandler, container.list_mailbox_accounts_handler)
    factory.register_handler(DeleteMailboxAccountHandler, container.delete_mailbox_account_handler)

    # 注册验证 Handlers
    factory.register_handler(RegisterWaitRequestHandler, container.register_wait_request_handler)
    factory.register_handler(CancelWaitRequestHandler, container.cancel_wait_request_handler)
    factory.register_handler(GetCodeHandler, container.get_code_handler)
