"""
日志模块

支持多种日志后端：
- simple: Python 标准 logging
- loguru: Loguru（推荐）
- logfire: Logfire（现代化可观测性）

使用方式：
    from shared.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Hello, world!")

切换后端：
    # 方式 1：环境变量
    export LOG_BACKEND=loguru

    # 方式 2：代码
    from shared.logging import set_log_backend
    set_log_backend("logfire")
"""

from .logger_factory import get_logger, set_log_backend, LogBackend

__all__ = ["get_logger", "set_log_backend", "LogBackend"]
