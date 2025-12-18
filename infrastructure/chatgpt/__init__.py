"""
ChatGPT Team API 基础设施层

提供与 ChatGPT API 交互的客户端实现。
"""

from .api_client import ChatGPTApiClient, ChatGPTAPIError

__all__ = [
    "ChatGPTApiClient",
    "ChatGPTAPIError",
]
