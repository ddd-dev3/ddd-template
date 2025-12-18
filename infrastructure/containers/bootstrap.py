"""
Bootstrap（组合根）

这是整个应用的组合根，负责：
1. 创建并连接所有容器
2. 提供统一的依赖访问入口
3. 支持测试时替换依赖（override）

使用方式：
    from infrastructure.containers import bootstrap

    # 生产环境
    boot = bootstrap()

    # 获取依赖
    uow = boot.infra.unit_of_work()
    settings = boot.config.settings()

    # 测试环境（替换依赖）
    boot = bootstrap(start_orm=False)
    boot.infra.unit_of_work.override(providers.Factory(FakeUnitOfWork))
"""

from typing import Optional
from dependency_injector import containers, providers

from .config import ConfigContainer
from .infrastructure import InfraContainer
from .application import AppContainer


class Bootstrap(containers.DeclarativeContainer):
    """
    组合根 - 连接所有容器的顶层容器

    职责：
    - 创建并配置所有子容器
    - 管理容器间的依赖关系
    - 提供统一的访问入口
    """

    # ============ 配置层 ============
    config = providers.Container(ConfigContainer)

    # ============ 基础设施层 ============
    infra = providers.Container(
        InfraContainer,
        config=config  # 注入配置容器
    )

    # ============ 应用层 ============
    app = providers.Container(
        AppContainer,
        config=config,  # 注入配置容器
        infra=infra  # 注入基础设施容器
    )

    # ============ Wiring 配置 ============
    # 指定哪些模块需要自动注入
    wiring_config = containers.WiringConfiguration(
        modules=[
            # "infrastructure.api.endpoints",
            # "application.handlers",
        ]
    )


# ============ 全局实例 ============

_bootstrap: Optional[Bootstrap] = None


def bootstrap(
    start_orm: bool = True,
    reset: bool = False
) -> Bootstrap:
    """
    获取或创建 Bootstrap 实例（组合根）

    Args:
        start_orm: 是否启动 ORM 映射（测试时可设为 False）
        reset: 是否重置全局实例

    Returns:
        Bootstrap 实例

    使用示例：
        # 获取实例
        boot = bootstrap()

        # 使用配置
        settings = boot.config.settings()
        print(settings.app_env)

        # 使用基础设施
        with boot.infra.unit_of_work() as uow:
            # 业务逻辑
            uow.commit()

        # 测试时替换依赖
        from dependency_injector import providers
        boot.infra.unit_of_work.override(
            providers.Factory(FakeUnitOfWork)
        )
    """
    global _bootstrap

    if _bootstrap is None or reset:
        _bootstrap = Bootstrap()

        # 可选：启动 ORM
        if start_orm:
            # 如果有 ORM 映射初始化逻辑，在这里执行
            # from infrastructure.database.orm import start_mappers
            # start_mappers()
            pass

    return _bootstrap


def get_bootstrap() -> Bootstrap:
    """获取全局 Bootstrap 实例（必须先调用 bootstrap()）"""
    if _bootstrap is None:
        raise RuntimeError(
            "Bootstrap not initialized. Call bootstrap() first."
        )
    return _bootstrap


# ============ 便捷函数 ============

def get_settings():
    """快捷获取配置"""
    return get_bootstrap().config.settings()


def get_unit_of_work():
    """快捷获取工作单元（每次调用返回新实例）"""
    return get_bootstrap().infra.unit_of_work()


def get_db_session():
    """快捷获取数据库 Session"""
    factory = get_bootstrap().infra.db_session_factory()
    return factory()
