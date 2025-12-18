"""Webhook 客户端接口"""

from dataclasses import dataclass
from typing import Optional, Protocol, Dict, Any


@dataclass
class WebhookResult:
    """Webhook 调用结果

    Attributes:
        success: 是否成功（收到 2xx 响应）
        status_code: HTTP 状态码（如果有响应）
        retry_count: 重试次数
        error_message: 错误信息（失败时）
    """

    success: bool
    status_code: Optional[int] = None
    retry_count: int = 0
    error_message: str = ""


class WebhookClient(Protocol):
    """Webhook 客户端接口

    定义发送 Webhook 请求的契约。
    实现类应该处理重试逻辑和错误处理。
    """

    def send(self, url: str, payload: Dict[str, Any]) -> WebhookResult:
        """发送 Webhook 请求

        Args:
            url: 回调 URL（必须是 HTTPS）
            payload: JSON 载荷字典

        Returns:
            WebhookResult 包含调用结果
        """
        ...
