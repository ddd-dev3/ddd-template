"""
日志工厂 - 基于 Loguru 的日志系统

默认使用 Loguru，可选 Logfire（后期集成）

后端：
- loguru: Loguru（默认，推荐）
- logfire: Logfire（可选，现代化可观测性）
"""

import os
import sys
from typing import Literal, Any

LogBackend = Literal["loguru", "logfire"]


class LoggerFactory:
    """日志工厂"""

    _backend: LogBackend = None
    _initialized: bool = False

    @classmethod
    def get_backend(cls) -> LogBackend:
        """
        获取当前日志后端（自动根据环境选择）

        规则：
        - test/dev → loguru（本地日志）
        - staging/prod → logfire（云端监控）

        可通过 LOG_BACKEND 环境变量覆盖自动选择
        """
        if cls._backend is None:
            # 优先使用明确指定的后端
            backend = os.getenv("LOG_BACKEND")

            if backend is None:
                # 根据 APP_ENV 自动选择
                app_env = os.getenv("APP_ENV", "dev")

                if app_env in ["test", "dev"]:
                    backend = "loguru"  # 本地环境用 loguru
                elif app_env in ["staging", "prod"]:
                    backend = "logfire"  # 生产环境用 logfire
                else:
                    backend = "loguru"  # 默认 loguru

            # 验证后端有效性
            if backend not in ["loguru", "logfire"]:
                print(
                    f"⚠️  Invalid LOG_BACKEND: {backend}, falling back to loguru",
                    file=sys.stderr,
                )
                backend = "loguru"

            cls._backend = backend
        return cls._backend

    @classmethod
    def set_backend(cls, backend: LogBackend):
        """设置日志后端"""
        cls._backend = backend
        cls._initialized = False

    @classmethod
    def get_logger(cls, name: str) -> Any:
        """
        获取日志器

        Args:
            name: 日志器名称（通常是 __name__）

        Returns:
            日志器实例（Loguru 或 Logfire）
        """
        backend = cls.get_backend()

        if backend == "loguru":
            return cls._get_loguru_logger(name)
        elif backend == "logfire":
            return cls._get_logfire_logger(name)

    @classmethod
    def _get_loguru_logger(cls, name: str):
        """获取 Loguru 日志器"""
        try:
            from loguru import logger
        except ImportError:
            raise ImportError(
                "Loguru is required but not installed. "
                "Install it with: pip install loguru"
            )

        if not cls._initialized:
            # 移除默认 handler
            logger.remove()

            # 添加自定义 handler
            logger.add(
                sys.stderr,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                level=os.getenv("LOG_LEVEL", "INFO"),
            )

            # 可选：添加文件 handler
            log_file = os.getenv("LOG_FILE")
            if log_file:
                logger.add(
                    log_file,
                    rotation="500 MB",
                    retention="10 days",
                    level=os.getenv("LOG_LEVEL", "INFO"),
                )

            cls._initialized = True

        # Loguru 是全局的，但可以绑定上下文
        return logger.bind(name=name)

    @classmethod
    def _get_logfire_logger(cls, name: str):
        """
        获取 Logfire 日志器（集成 Loguru）

        Logfire 会自动捕获 Loguru 的日志，同时提供可观测性功能
        """
        try:
            import logfire
            from loguru import logger
        except ImportError as e:
            print(
                f"⚠️  {e}",
                file=sys.stderr,
            )
            print("   Logfire requires both logfire and loguru", file=sys.stderr)
            print("   Install with: pip install logfire loguru", file=sys.stderr)
            print("   Falling back to loguru", file=sys.stderr)
            return cls._get_loguru_logger(name)

        if not cls._initialized:
            try:
                # 配置 Logfire
                logfire.configure()

                # 集成 Loguru（可选，让 loguru 的日志也发送到 Logfire）
                try:
                    logfire.integrate_loguru()
                    print("✅ Logfire integrated with Loguru", file=sys.stderr)
                except Exception as e:
                    print(f"⚠️  Logfire-Loguru integration failed: {e}", file=sys.stderr)

                cls._initialized = True
            except Exception as e:
                print(f"⚠️  Failed to configure Logfire: {e}", file=sys.stderr)
                print("   Make sure to run: logfire auth", file=sys.stderr)
                print("   Falling back to loguru", file=sys.stderr)
                return cls._get_loguru_logger(name)

        # 返回 logfire（它也可以像 logger 一样使用）
        return logfire


# 便捷函数

def get_logger(name: str = __name__) -> Any:
    """
    获取日志器（便捷函数）

    用法：
        from shared.logging import get_logger

        logger = get_logger(__name__)
        logger.info("Hello, world!")
    """
    return LoggerFactory.get_logger(name)


def set_log_backend(backend: LogBackend):
    """
    设置日志后端

    用法：
        from shared.logging import set_log_backend

        set_log_backend("loguru")
    """
    LoggerFactory.set_backend(backend)
