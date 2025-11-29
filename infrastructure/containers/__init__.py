"""
依赖注入容器

三层容器架构：
- ConfigContainer: 配置管理
- InfraContainer: 基础设施（数据库、UoW、仓储）
- AppContainer: 应用层（Mediator、Handlers）

使用 Bootstrap 作为组合根，连接所有容器。

使用示例：
    from infrastructure.containers import bootstrap, get_unit_of_work

    # 初始化
    boot = bootstrap()

    # 获取配置
    settings = boot.config.settings()

    # 获取工作单元
    with get_unit_of_work() as uow:
        # 业务逻辑
        uow.commit()
"""

from .config import ConfigContainer
from .infrastructure import InfraContainer
from .application import AppContainer
from .bootstrap import (
    Bootstrap,
    bootstrap,
    get_bootstrap,
    get_settings,
    get_unit_of_work,
    get_db_session,
)

__all__ = [
    # 容器
    "ConfigContainer",
    "InfraContainer",
    "AppContainer",
    "Bootstrap",
    # 便捷函数
    "bootstrap",
    "get_bootstrap",
    "get_settings",
    "get_unit_of_work",
    "get_db_session",
]
