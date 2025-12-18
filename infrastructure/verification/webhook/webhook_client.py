"""HTTP Webhook 客户端实现"""

import time
import logging
from typing import Optional, Dict, Any, List

import httpx

from domain.verification.services.webhook_client import WebhookClient, WebhookResult


class HttpWebhookClient(WebhookClient):
    """HTTP Webhook 客户端实现

    使用 httpx 库发送 HTTP POST 请求，支持指数退避重试机制。

    Attributes:
        RETRY_INTERVALS: 重试间隔列表（秒）
        TIMEOUT: 请求超时时间（秒）
    """

    RETRY_INTERVALS: List[int] = [1, 5, 15]  # 重试间隔：1秒, 5秒, 15秒
    TIMEOUT: int = 10  # 请求超时时间

    def __init__(self, logger: Optional[logging.Logger] = None):
        """初始化客户端

        Args:
            logger: 日志记录器（可选）
        """
        self._logger = logger or logging.getLogger(__name__)

    def send(self, url: str, payload: Dict[str, Any]) -> WebhookResult:
        """发送 Webhook 请求，支持重试

        实现指数退避重试策略：
        - 首次失败后等待 1 秒重试
        - 二次失败后等待 5 秒重试
        - 三次失败后等待 15 秒重试
        - 全部失败后返回失败结果

        Args:
            url: 回调 URL
            payload: JSON 载荷

        Returns:
            WebhookResult 包含调用结果
        """
        last_error = ""
        last_status_code: Optional[int] = None

        # 首次尝试 + 3 次重试 = 总共 4 次
        for attempt in range(len(self.RETRY_INTERVALS) + 1):
            try:
                response = httpx.post(
                    url,
                    json=payload,
                    timeout=self.TIMEOUT,
                    headers={"Content-Type": "application/json"},
                )

                last_status_code = response.status_code

                if 200 <= response.status_code < 300:
                    self._logger.info(
                        f"Webhook successful: {url} (attempt {attempt + 1}, "
                        f"status {response.status_code})"
                    )
                    return WebhookResult(
                        success=True,
                        status_code=response.status_code,
                        retry_count=attempt,
                    )
                else:
                    last_error = f"HTTP {response.status_code}"
                    self._logger.warning(
                        f"Webhook failed: {url} - {last_error} (attempt {attempt + 1})"
                    )

            except httpx.TimeoutException:
                last_error = "Request timeout"
                self._logger.warning(
                    f"Webhook timeout: {url} (attempt {attempt + 1})"
                )

            except httpx.RequestError as e:
                last_error = f"Request error: {str(e)}"
                self._logger.warning(
                    f"Webhook error: {url} - {last_error} (attempt {attempt + 1})"
                )

            # 如果不是最后一次尝试，等待后重试
            if attempt < len(self.RETRY_INTERVALS):
                wait_time = self.RETRY_INTERVALS[attempt]
                self._logger.debug(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

        # 所有重试都失败
        total_attempts = len(self.RETRY_INTERVALS) + 1
        self._logger.error(
            f"Webhook failed after {total_attempts} attempts: {url} - {last_error}"
        )
        return WebhookResult(
            success=False,
            status_code=last_status_code,
            retry_count=total_attempts - 1,
            error_message=last_error,
        )
