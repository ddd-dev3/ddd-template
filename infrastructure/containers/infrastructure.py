"""
基础设施容器（InfraContainer）

管理所有基础设施组件：数据库、工作单元、仓储实现等。
依赖 ConfigContainer 获取配置。
"""

from dependency_injector import containers, providers
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from infrastructure.database.database_factory import DatabaseFactory
from infrastructure.database.unit_of_work import UnitOfWork
from .config import ConfigContainer


class InfraContainer(containers.DeclarativeContainer):
    """基础设施容器 - 管理技术实现"""

    # 依赖配置容器
    config = providers.DependenciesContainer()

    # ============ 数据库 ============

    # 数据库引擎（单例）
    db_engine: providers.Singleton[Engine] = providers.Singleton(
        DatabaseFactory.create_engine
    )

    # Session 工厂（单例）
    db_session_factory: providers.Singleton[sessionmaker] = providers.Singleton(
        DatabaseFactory.create_session_factory,
        engine=db_engine
    )

    # ============ 工作单元 ============

    # 工作单元（每次请求新实例）
    unit_of_work = providers.Factory(
        UnitOfWork,
        session_factory=db_session_factory
    )

    # ============ 仓储（后续添加）============
    # 示例：
    # user_repository = providers.Factory(
    #     SqlAlchemyUserRepository,
    #     session_factory=db_session_factory
    # )

    # ============ 外部服务（后续添加）============
    # 示例：
    # email_sender = providers.Singleton(SmtpEmailSender, config=config.settings)
    # http_client = providers.Singleton(HttpClient)
