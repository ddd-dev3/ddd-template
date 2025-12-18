"""Webhook 回调载荷值对象"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from domain.common.base_value_object import BaseValueObject


@dataclass(frozen=True)
class WebhookPayload(BaseValueObject):
    """Webhook 回调载荷值对象

    封装发送给消费者的回调数据。

    Attributes:
        request_id: 等待请求 ID
        type: 提取类型 ("code" 或 "link")
        value: 提取的验证码或链接
        email: 邮箱地址
        service: 服务名称
        received_at: 邮件接收时间
    """

    request_id: UUID
    type: str
    value: str
    email: str
    service: str
    received_at: datetime

    def validate(self) -> None:
        """验证载荷有效性"""
        if self.type not in ("code", "link"):
            raise ValueError(f"Invalid type: {self.type}. Must be 'code' or 'link'")
        if not self.value:
            raise ValueError("Value cannot be empty")
        if not self.email:
            raise ValueError("Email cannot be empty")
        if not self.service:
            raise ValueError("Service cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """转换为 JSON 可序列化字典

        Returns:
            包含所有字段的字典，适合 JSON 序列化
        """
        return {
            "request_id": str(self.request_id),
            "type": self.type,
            "value": self.value,
            "email": self.email,
            "service": self.service,
            "received_at": self.received_at.isoformat(),
        }
