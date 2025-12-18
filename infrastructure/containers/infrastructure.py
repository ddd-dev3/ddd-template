"""
基础设施容器（InfraContainer）

管理所有基础设施组件：数据库、工作单元、仓储实现等。
依赖 ConfigContainer 获取配置。
"""

from dependency_injector import containers, providers
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker, Session

from infrastructure.database.database_factory import DatabaseFactory
from infrastructure.database.unit_of_work import UnitOfWork
from infrastructure.mailbox.services.imap_connection_validator_impl import ImapConnectionValidatorImpl
from infrastructure.mailbox.repositories.sqlalchemy_mailbox_account_repository import SqlAlchemyMailboxAccountRepository
from infrastructure.mail.services.imap_mail_fetch_service_impl import ImapMailFetchServiceImpl
from infrastructure.mail.repositories.sqlalchemy_email_repository import SqlAlchemyEmailRepository
from infrastructure.ai.llm_verification_extractor import LlmVerificationExtractor
from infrastructure.verification.repositories.sqlalchemy_wait_request_repository import SqlAlchemyWaitRequestRepository
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

    # ============ 数据库 Session ============

    # 数据库 Session（每次请求新实例）
    db_session = providers.Factory(
        lambda session_factory: session_factory(),
        session_factory=db_session_factory
    )

    # ============ 仓储 ============

    # 邮箱账号仓储
    mailbox_account_repository = providers.Factory(
        SqlAlchemyMailboxAccountRepository,
        session=db_session
    )

    # ============ 领域服务 ============

    # IMAP 连接验证服务
    imap_connection_validator = providers.Singleton(
        ImapConnectionValidatorImpl,
        timeout=30.0
    )

    # ============ 邮件仓储 ============

    # 邮件仓储
    email_repository = providers.Factory(
        SqlAlchemyEmailRepository,
        session=db_session
    )

    # ============ 验证仓储 ============

    # 等待请求仓储
    wait_request_repository = providers.Factory(
        SqlAlchemyWaitRequestRepository,
        session=db_session
    )

    # ============ 邮件服务 ============

    # IMAP 邮件收取服务
    imap_mail_fetch_service = providers.Factory(
        ImapMailFetchServiceImpl,
        encryption_key=config.provided.settings.provided.encryption_key,
    )

    # ============ AI 服务 ============

    # LLM 验证码提取服务（单例）
    llm_verification_extractor = providers.Singleton(
        LlmVerificationExtractor,
        api_key=config.provided.settings.provided.openai_api_key,
        model=config.provided.settings.provided.openai_model,
        api_base=config.provided.settings.provided.openai_api_base,
        timeout=config.provided.settings.provided.ai_extraction_timeout,
    )

    # ============ 外部服务（后续添加）============
    # 示例：
    # email_sender = providers.Singleton(SmtpEmailSender, config=config.settings)
    # http_client = providers.Singleton(HttpClient)
