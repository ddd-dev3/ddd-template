"""
数据库工厂 - 根据环境自动选择数据库

支持环境：
- test: SQLite 内存数据库（快速测试）
- dev: SQLite 文件数据库（本地开发）
- staging/prod: Supabase/PostgreSQL（生产环境）
"""

import os
from typing import Literal, Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

Environment = Literal["test", "dev", "staging", "prod"]


class DatabaseFactory:
    """数据库工厂 - 统一的数据库创建接口"""

    @staticmethod
    def create_engine(env: Optional[Environment] = None) -> Engine:
        """
        根据环境创建数据库引擎

        Args:
            env: 环境类型，如果不指定则从环境变量 APP_ENV 读取

        Returns:
            SQLAlchemy Engine 实例

        环境优先级：
        1. 参数传入的 env
        2. 环境变量 APP_ENV
        3. 默认 'dev'
        """
        if env is None:
            env = DatabaseFactory.get_current_env()

        if env == "test":
            return DatabaseFactory._create_test_engine()
        elif env == "dev":
            return DatabaseFactory._create_dev_engine()
        elif env == "staging":
            return DatabaseFactory._create_supabase_engine("staging")
        elif env == "prod":
            return DatabaseFactory._create_supabase_engine("prod")
        else:
            raise ValueError(f"Unknown environment: {env}")

    @staticmethod
    def _create_test_engine() -> Engine:
        """
        测试环境：SQLite 内存数据库

        特点：
        - 超快速（在内存中）
        - 每次运行都是全新的
        - 适合单元测试和集成测试
        """
        return create_engine(
            "sqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,  # 内存数据库使用静态连接池
        )

    @staticmethod
    def _create_dev_engine() -> Engine:
        """
        开发环境：SQLite 文件数据库

        特点：
        - 数据持久化到文件
        - 方便本地调试
        - 适合本地开发
        """
        db_path = os.getenv("DEV_DB_PATH", "data/dev.db")

        # 确保目录存在
        import pathlib
        pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        return create_engine(
            f"sqlite:///{db_path}",
            echo=True,  # 开发环境显示 SQL 语句
            connect_args={"check_same_thread": False},
        )

    @staticmethod
    def _create_supabase_engine(env: str) -> Engine:
        """
        生产环境：Supabase (PostgreSQL)

        Args:
            env: 'staging' 或 'prod'

        环境变量：
        - STAGING_DATABASE_URL: staging 环境数据库 URL
        - PROD_DATABASE_URL: prod 环境数据库 URL

        URL 格式：
        postgresql://user:password@host:port/database
        """
        env_var = f"{env.upper()}_DATABASE_URL"
        db_url = os.getenv(env_var)

        if not db_url:
            raise ValueError(
                f"Missing database URL for {env} environment. "
                f"Please set environment variable: {env_var}"
            )

        return create_engine(
            db_url,
            pool_size=int(os.getenv(f"{env.upper()}_DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv(f"{env.upper()}_DB_MAX_OVERFLOW", "20")),
            pool_pre_ping=True,  # 自动检测连接是否有效
            echo=False,  # 生产环境不显示 SQL
        )

    @staticmethod
    def create_session_factory(engine: Engine) -> sessionmaker:
        """
        创建 Session 工厂

        Args:
            engine: SQLAlchemy Engine

        Returns:
            sessionmaker 实例
        """
        return sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    @staticmethod
    def create_session(engine: Engine) -> Session:
        """
        创建单个 Session

        Args:
            engine: SQLAlchemy Engine

        Returns:
            Session 实例
        """
        factory = DatabaseFactory.create_session_factory(engine)
        return factory()

    @staticmethod
    def get_current_env() -> Environment:
        """
        获取当前环境

        Returns:
            环境类型（test/dev/staging/prod）
        """
        env = os.getenv("APP_ENV", "dev")

        if env not in ["test", "dev", "staging", "prod"]:
            raise ValueError(
                f"Invalid APP_ENV value: {env}. "
                f"Must be one of: test, dev, staging, prod"
            )

        return env

    @staticmethod
    def get_database_url(env: Optional[Environment] = None) -> str:
        """
        获取当前环境的数据库 URL（用于显示或日志）

        Args:
            env: 环境类型

        Returns:
            数据库连接字符串（隐藏密码）
        """
        if env is None:
            env = DatabaseFactory.get_current_env()

        if env == "test":
            return "sqlite:///:memory:"
        elif env == "dev":
            return f"sqlite:///{os.getenv('DEV_DB_PATH', 'data/dev.db')}"
        else:
            env_var = f"{env.upper()}_DATABASE_URL"
            url = os.getenv(env_var, "")
            # 隐藏密码
            if url and "@" in url:
                parts = url.split("@")
                user_part = parts[0].split("://")[0] + "://***:***"
                return user_part + "@" + parts[1]
            return url or f"<未设置 {env_var}>"


# 便捷函数

def get_engine(env: Optional[Environment] = None) -> Engine:
    """便捷函数：创建数据库引擎"""
    return DatabaseFactory.create_engine(env)


def get_session_factory(env: Optional[Environment] = None) -> sessionmaker:
    """便捷函数：创建 Session 工厂"""
    engine = get_engine(env)
    return DatabaseFactory.create_session_factory(engine)


def get_session(env: Optional[Environment] = None) -> Session:
    """便捷函数：创建 Session"""
    engine = get_engine(env)
    return DatabaseFactory.create_session(engine)


def init_database(engine: Optional[Engine] = None) -> None:
    """
    初始化数据库（创建所有表）

    在应用启动时调用，自动创建所有已注册的表。
    如果表已存在则跳过。

    Args:
        engine: SQLAlchemy Engine，如果不传则自动创建
    """
    if engine is None:
        engine = get_engine()

    # 导入所有模型，确保它们注册到 Base.metadata
    from infrastructure.mailbox.models.mailbox_account_model import Base
    # 以下导入确保模型被注册（即使不直接使用）
    from infrastructure.mailbox.models.mailbox_account_model import MailboxAccountModel  # noqa: F401
    from infrastructure.mail.models.email_model import EmailModel  # noqa: F401
    from infrastructure.verification.models.wait_request_model import WaitRequestModel  # noqa: F401

    # 创建所有表（如果不存在）
    Base.metadata.create_all(bind=engine)
