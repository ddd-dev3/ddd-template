"""Tests for HttpWebhookClient implementation"""

import pytest
from unittest.mock import patch, MagicMock
import httpx

from infrastructure.verification.webhook.webhook_client import HttpWebhookClient


class TestHttpWebhookClientSuccess:
    """HttpWebhookClient 成功场景测试"""

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    def test_successful_send_returns_success(self, mock_post: MagicMock):
        """测试成功发送 Webhook 返回成功结果"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = HttpWebhookClient()
        result = client.send(
            url="https://example.com/webhook",
            payload={"request_id": "123", "type": "code", "value": "123456"},
        )

        assert result.success is True
        assert result.status_code == 200
        assert result.retry_count == 0
        assert result.error_message == ""
        mock_post.assert_called_once()

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    def test_successful_send_with_201_status(self, mock_post: MagicMock):
        """测试 201 状态码也视为成功"""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        client = HttpWebhookClient()
        result = client.send(
            url="https://example.com/webhook",
            payload={"request_id": "123"},
        )

        assert result.success is True
        assert result.status_code == 201

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    def test_send_uses_correct_headers(self, mock_post: MagicMock):
        """测试发送时使用正确的 Content-Type 头"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = HttpWebhookClient()
        client.send(
            url="https://example.com/webhook",
            payload={"test": "data"},
        )

        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["headers"]["Content-Type"] == "application/json"

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    def test_send_uses_correct_timeout(self, mock_post: MagicMock):
        """测试发送时使用正确的超时时间"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = HttpWebhookClient()
        client.send(
            url="https://example.com/webhook",
            payload={"test": "data"},
        )

        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["timeout"] == HttpWebhookClient.TIMEOUT


class TestHttpWebhookClientHttpErrors:
    """HttpWebhookClient HTTP 错误测试"""

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    @patch("infrastructure.verification.webhook.webhook_client.time.sleep")
    def test_http_400_error_after_retries(
        self, mock_sleep: MagicMock, mock_post: MagicMock
    ):
        """测试 400 错误在所有重试后返回失败"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        client = HttpWebhookClient()
        result = client.send(
            url="https://example.com/webhook",
            payload={"test": "data"},
        )

        assert result.success is False
        assert result.status_code == 400
        assert "HTTP 400" in result.error_message
        # 首次 + 3 次重试 = 4 次调用
        assert mock_post.call_count == 4
        # 3 次重试间等待
        assert mock_sleep.call_count == 3

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    @patch("infrastructure.verification.webhook.webhook_client.time.sleep")
    def test_http_500_error_after_retries(
        self, mock_sleep: MagicMock, mock_post: MagicMock
    ):
        """测试 500 服务器错误在所有重试后返回失败"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        client = HttpWebhookClient()
        result = client.send(
            url="https://example.com/webhook",
            payload={"test": "data"},
        )

        assert result.success is False
        assert result.status_code == 500
        assert "HTTP 500" in result.error_message


class TestHttpWebhookClientNetworkErrors:
    """HttpWebhookClient 网络错误测试"""

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    @patch("infrastructure.verification.webhook.webhook_client.time.sleep")
    def test_timeout_exception_after_retries(
        self, mock_sleep: MagicMock, mock_post: MagicMock
    ):
        """测试超时异常在所有重试后返回失败"""
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")

        client = HttpWebhookClient()
        result = client.send(
            url="https://example.com/webhook",
            payload={"test": "data"},
        )

        assert result.success is False
        assert result.status_code is None
        assert "Request timeout" in result.error_message
        assert mock_post.call_count == 4  # 首次 + 3 次重试

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    @patch("infrastructure.verification.webhook.webhook_client.time.sleep")
    def test_request_error_after_retries(
        self, mock_sleep: MagicMock, mock_post: MagicMock
    ):
        """测试请求错误在所有重试后返回失败"""
        mock_post.side_effect = httpx.RequestError("Connection refused")

        client = HttpWebhookClient()
        result = client.send(
            url="https://example.com/webhook",
            payload={"test": "data"},
        )

        assert result.success is False
        assert result.status_code is None
        assert "Request error" in result.error_message


class TestHttpWebhookClientRetryBehavior:
    """HttpWebhookClient 重试行为测试"""

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    @patch("infrastructure.verification.webhook.webhook_client.time.sleep")
    def test_retry_intervals_are_correct(
        self, mock_sleep: MagicMock, mock_post: MagicMock
    ):
        """测试重试间隔符合预期 (1s, 5s, 15s)"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        client = HttpWebhookClient()
        client.send(url="https://example.com/webhook", payload={})

        # 检查重试间隔
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [1, 5, 15]

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    @patch("infrastructure.verification.webhook.webhook_client.time.sleep")
    def test_success_on_second_attempt(
        self, mock_sleep: MagicMock, mock_post: MagicMock
    ):
        """测试第二次尝试成功"""
        fail_response = MagicMock()
        fail_response.status_code = 500

        success_response = MagicMock()
        success_response.status_code = 200

        mock_post.side_effect = [fail_response, success_response]

        client = HttpWebhookClient()
        result = client.send(url="https://example.com/webhook", payload={})

        assert result.success is True
        assert result.retry_count == 1  # 一次重试后成功
        assert mock_post.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    @patch("infrastructure.verification.webhook.webhook_client.time.sleep")
    def test_success_on_third_attempt(
        self, mock_sleep: MagicMock, mock_post: MagicMock
    ):
        """测试第三次尝试成功"""
        fail_response = MagicMock()
        fail_response.status_code = 500

        success_response = MagicMock()
        success_response.status_code = 200

        mock_post.side_effect = [fail_response, fail_response, success_response]

        client = HttpWebhookClient()
        result = client.send(url="https://example.com/webhook", payload={})

        assert result.success is True
        assert result.retry_count == 2  # 两次重试后成功
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    @patch("infrastructure.verification.webhook.webhook_client.time.sleep")
    def test_success_on_fourth_attempt(
        self, mock_sleep: MagicMock, mock_post: MagicMock
    ):
        """测试第四次尝试（最后一次重试）成功"""
        fail_response = MagicMock()
        fail_response.status_code = 500

        success_response = MagicMock()
        success_response.status_code = 200

        mock_post.side_effect = [
            fail_response,
            fail_response,
            fail_response,
            success_response,
        ]

        client = HttpWebhookClient()
        result = client.send(url="https://example.com/webhook", payload={})

        assert result.success is True
        assert result.retry_count == 3  # 三次重试后成功
        assert mock_post.call_count == 4
        assert mock_sleep.call_count == 3

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    @patch("infrastructure.verification.webhook.webhook_client.time.sleep")
    def test_retry_count_on_all_failures(
        self, mock_sleep: MagicMock, mock_post: MagicMock
    ):
        """测试所有尝试都失败时的重试次数"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        client = HttpWebhookClient()
        result = client.send(url="https://example.com/webhook", payload={})

        assert result.success is False
        assert result.retry_count == 3  # 总共重试了 3 次


class TestHttpWebhookClientLogging:
    """HttpWebhookClient 日志测试"""

    @patch("infrastructure.verification.webhook.webhook_client.httpx.post")
    def test_custom_logger(self, mock_post: MagicMock):
        """测试使用自定义日志记录器"""
        import logging

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        custom_logger = logging.getLogger("custom_webhook")
        client = HttpWebhookClient(logger=custom_logger)

        result = client.send(url="https://example.com/webhook", payload={})

        assert result.success is True
