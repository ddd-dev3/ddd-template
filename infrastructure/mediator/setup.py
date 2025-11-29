"""
Mediator 配置与工厂

将 mediatr-py 与 dependency-injector 容器集成。

核心思路：
1. Handler 类在 AppContainer 中注册为 Provider
2. Mediator 通过 handler_class_manager 从容器获取 Handler 实例
3. 这样 Handler 的依赖会被自动注入

使用示例：
    # 1. 定义 Command
    @dataclass
    class CreateUserCommand:
        name: str
        email: str

    # 2. 定义 Handler（需要依赖注入）
    @Mediator.handler
    class CreateUserHandler:
        def __init__(self, uow: UnitOfWork):
            self.uow = uow

        async def handle(self, request: CreateUserCommand):
            # 业务逻辑
            return {"id": 1}

    # 3. 在容器中注册 Handler
    class AppContainer(containers.DeclarativeContainer):
        create_user_handler = providers.Factory(
            CreateUserHandler,
            uow=infra.unit_of_work
        )

    # 4. 使用
    mediator = boot.app.mediator()
    result = await mediator.send_async(CreateUserCommand(name="test", email="test@test.com"))
"""

from typing import Type, Any, Dict, Optional, Callable
from mediatr import Mediator



class MediatorFactory:
    """
    Mediator 工厂

    负责创建与 DI 容器集成的 Mediator 实例。
    """

    def __init__(self):
        # Handler 类 -> Provider 的映射
        self._handler_providers: Dict[Type, Callable[[], Any]] = {}

    def register_handler(self, handler_class: Type, provider: Callable[[], Any]) -> None:
        """
        注册 Handler 的 Provider

        Args:
            handler_class: Handler 类
            provider: 返回 Handler 实例的 Provider（来自容器）
        """
        self._handler_providers[handler_class] = provider

    def register_handlers(self, handlers: Dict[Type, Callable[[], Any]]) -> None:
        """批量注册 Handlers"""
        self._handler_providers.update(handlers)

    def _handler_class_manager(self, handler_class: Type, is_behavior: bool = False) -> Any:
        """
        Handler 类管理器 - 供 Mediator 使用

        当 Mediator 需要实例化 Handler 时调用此函数。
        优先从注册的 Provider 获取，否则直接实例化（无依赖的 Handler）。
        """
        if handler_class in self._handler_providers:
            # 从容器获取（依赖会被注入）
            return self._handler_providers[handler_class]()
        else:
            # 直接实例化（无依赖的简单 Handler 或函数式 Handler）
            return handler_class()

    def create_mediator(self) -> Mediator:
        """创建 Mediator 实例"""
        return Mediator(handler_class_manager=self._handler_class_manager)


# ============ 全局工厂实例 ============

_factory: Optional[MediatorFactory] = None


def get_mediator_factory() -> MediatorFactory:
    """获取全局 MediatorFactory 实例"""
    global _factory
    if _factory is None:
        _factory = MediatorFactory()
    return _factory


def create_mediator() -> Mediator:
    """创建 Mediator 实例（便捷函数）"""
    return get_mediator_factory().create_mediator()


def register_handler(handler_class: Type, provider: Callable[[], Any]) -> None:
    """注册 Handler（便捷函数）"""
    get_mediator_factory().register_handler(handler_class, provider)
