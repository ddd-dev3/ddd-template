"""
应用配置管理

使用 pydantic-settings 管理环境变量和配置
"""

import os
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

    # ========== 日志配置 ==========
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

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
