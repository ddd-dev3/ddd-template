"""
通用模块（Common）

包含跨层使用的通用工具、安全、日志等功能。
这是技术性的通用代码，不是 DDD 的 Shared Kernel。
"""

# 导出常用功能
from .logging import get_logger, set_log_backend

__all__ = [
    "get_logger",
    "set_log_backend",
]
