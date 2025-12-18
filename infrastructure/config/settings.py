"""
应用配置管理

使用 pydantic-settings 管理环境变量和配置
"""

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类

    自动从环境变量和 .env 文件读取配置
    """

    # ========== 应用环境 ==========
    app_env: Literal["test", "dev", "staging", "prod"] = "dev"
    app_name: str = "MyDDDApp"
    app_version: str = "1.0.0"
    debug: bool = False

    # ========== 数据库配置 ==========
    # 开发环境（SQLite）
    dev_db_path: str = "data/dev.db"

    # Staging 环境（Supabase）
    staging_database_url: str = ""
    staging_db_pool_size: int = 10
    staging_db_max_overflow: int = 20

    # 生产环境（Supabase）
    prod_database_url: str = ""
    prod_db_pool_size: int = 20
    prod_db_max_overflow: int = 40

    # ========== API 认证配置 ==========
    api_key: str = "dev-api-key-change-me"  # 开发环境默认值，生产环境必须通过环境变量设置

    # ========== 加密配置 ==========
    # Fernet 密钥（32 字节 base64 编码）
    # 生成方式: from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())
    encryption_key: str = "your-32-byte-base64-encoded-key-here"  # 必须通过环境变量设置

    # ========== 日志配置 ==========
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # ========== 邮件轮询配置 ==========
    # 环境变量: MAIL_POLLING_INTERVAL
    mail_polling_interval: float = 5.0  # 邮件轮询间隔（秒）
    # 环境变量: MAIL_MAX_CONCURRENT_CONNECTIONS
    mail_max_concurrent_connections: int = 10  # 最大并发 IMAP 连接数
    # 环境变量: MAIL_POLL_TIMEOUT
    mail_poll_timeout: float = 30.0  # 单邮箱轮询超时（秒）

    # ========== AI 配置 ==========
    # 环境变量: OPENAI_API_KEY
    openai_api_key: str = ""  # 必须通过环境变量设置，不记录到日志
    # 环境变量: OPENAI_API_BASE
    openai_api_base: str = "https://api.openai.com/v1"
    # 环境变量: OPENAI_MODEL
    openai_model: str = "gpt-4o-mini"
    # 环境变量: AI_EXTRACTION_TIMEOUT
    ai_extraction_timeout: float = 30.0  # AI 提取超时（秒）

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 忽略未定义的环境变量
    )

    @property
    def is_test(self) -> bool:
        """是否为测试环境"""
        return self.app_env == "test"

    @property
    def is_dev(self) -> bool:
        """是否为开发环境"""
        return self.app_env == "dev"

    @property
    def is_staging(self) -> bool:
        """是否为 staging 环境"""
        return self.app_env == "staging"

    @property
    def is_prod(self) -> bool:
        """是否为生产环境"""
        return self.app_env == "prod"

    @property
    def database_url(self) -> str:
        """获取当前环境的数据库 URL"""
        if self.is_test:
            return "sqlite:///:memory:"
        elif self.is_dev:
            return f"sqlite:///{self.dev_db_path}"
        elif self.is_staging:
            return self.staging_database_url
        else:  # prod
            return self.prod_database_url


# 全局配置实例（单例）
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    获取配置实例（单例模式）

    Returns:
        Settings 实例
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# 便捷导出
settings = get_settings()
