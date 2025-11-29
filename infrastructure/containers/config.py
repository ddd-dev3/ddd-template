"""
配置容器（ConfigContainer）

管理应用配置，从环境变量和配置文件加载设置。
这是最底层的容器，不依赖其他容器。
"""

from dependency_injector import containers, providers

from infrastructure.config.settings import Settings


class ConfigContainer(containers.DeclarativeContainer):
    """配置容器 - 管理所有配置"""

    # 应用配置（单例）
    settings = providers.Singleton(Settings)

    # 便捷访问常用配置
    app_env = providers.Callable(
        lambda s: s.app_env,
        s=settings
    )

    database_url = providers.Callable(
        lambda s: s.database_url,
        s=settings
    )

    debug = providers.Callable(
        lambda s: s.debug,
        s=settings
    )
