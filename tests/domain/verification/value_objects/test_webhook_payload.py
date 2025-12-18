"""Tests for WebhookPayload value object"""

import pytest
from datetime import datetime
from uuid import UUID

from domain.verification.value_objects.webhook_payload import WebhookPayload


class TestWebhookPayloadCreation:
    """WebhookPayload 创建测试"""

    def test_create_webhook_payload(self):
        """测试创建 WebhookPayload"""
        request_id = UUID("12345678-1234-5678-1234-567812345678")
        received_at = datetime(2024, 1, 15, 10, 30, 0)

        payload = WebhookPayload(
            request_id=request_id,
            type="code",
            value="123456",
            email="test@example.com",
            service="claude",
            received_at=received_at,
        )

        assert payload.request_id == request_id
        assert payload.type == "code"
        assert payload.value == "123456"
        assert payload.email == "test@example.com"
        assert payload.service == "claude"
        assert payload.received_at == received_at

    def test_create_link_type_payload(self):
        """测试创建 link 类型的 WebhookPayload"""
        request_id = UUID("12345678-1234-5678-1234-567812345678")
        received_at = datetime(2024, 1, 15, 10, 30, 0)

        payload = WebhookPayload(
            request_id=request_id,
            type="link",
            value="https://example.com/verify?token=abc123",
            email="test@example.com",
            service="github",
            received_at=received_at,
        )

        assert payload.type == "link"
        assert payload.value == "https://example.com/verify?token=abc123"
        assert payload.service == "github"


class TestWebhookPayloadToDict:
    """WebhookPayload to_dict() 测试"""

    def test_to_dict_returns_correct_structure(self):
        """测试 to_dict() 返回正确的字典结构"""
        request_id = UUID("12345678-1234-5678-1234-567812345678")
        received_at = datetime(2024, 1, 15, 10, 30, 0)

        payload = WebhookPayload(
            request_id=request_id,
            type="code",
            value="123456",
            email="test@example.com",
            service="claude",
            received_at=received_at,
        )

        result = payload.to_dict()

        assert result["request_id"] == "12345678-1234-5678-1234-567812345678"
        assert result["type"] == "code"
        assert result["value"] == "123456"
        assert result["email"] == "test@example.com"
        assert result["service"] == "claude"
        assert result["received_at"] == "2024-01-15T10:30:00"

    def test_to_dict_with_microseconds(self):
        """测试带微秒的时间戳转换"""
        request_id = UUID("12345678-1234-5678-1234-567812345678")
        received_at = datetime(2024, 1, 15, 10, 30, 0, 123456)

        payload = WebhookPayload(
            request_id=request_id,
            type="code",
            value="123456",
            email="test@example.com",
            service="claude",
            received_at=received_at,
        )

        result = payload.to_dict()

        assert result["received_at"] == "2024-01-15T10:30:00.123456"


class TestWebhookPayloadImmutability:
    """WebhookPayload 不可变性测试"""

    def test_payload_is_frozen(self):
        """测试 WebhookPayload 是不可变的"""
        payload = WebhookPayload(
            request_id=UUID("12345678-1234-5678-1234-567812345678"),
            type="code",
            value="123456",
            email="test@example.com",
            service="claude",
            received_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            payload.value = "654321"


class TestWebhookPayloadEquality:
    """WebhookPayload 相等性测试"""

    def test_same_values_are_equal(self):
        """测试相同值的 WebhookPayload 相等"""
        request_id = UUID("12345678-1234-5678-1234-567812345678")
        received_at = datetime(2024, 1, 15, 10, 30, 0)

        payload1 = WebhookPayload(
            request_id=request_id,
            type="code",
            value="123456",
            email="test@example.com",
            service="claude",
            received_at=received_at,
        )
        payload2 = WebhookPayload(
            request_id=request_id,
            type="code",
            value="123456",
            email="test@example.com",
            service="claude",
            received_at=received_at,
        )

        assert payload1 == payload2

    def test_different_values_are_not_equal(self):
        """测试不同值的 WebhookPayload 不相等"""
        request_id = UUID("12345678-1234-5678-1234-567812345678")
        received_at = datetime(2024, 1, 15, 10, 30, 0)

        payload1 = WebhookPayload(
            request_id=request_id,
            type="code",
            value="123456",
            email="test@example.com",
            service="claude",
            received_at=received_at,
        )
        payload2 = WebhookPayload(
            request_id=request_id,
            type="code",
            value="654321",  # 不同的值
            email="test@example.com",
            service="claude",
            received_at=received_at,
        )

        assert payload1 != payload2
