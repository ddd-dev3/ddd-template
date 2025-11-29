"""
示例事件

演示如何定义领域事件。
事件表示"已经发生的事情"，用过去时态命名。

注意：由于 DomainEvent 基类有可选字段（有默认值），
子类的字段也必须有默认值，或使用 field(default=...) 定义。
"""

from dataclasses import dataclass, field
from uuid import UUID

from domain.common.base_event import DomainEvent


@dataclass(frozen=True)
class UserCreatedEvent(DomainEvent):
    """用户创建事件"""
    user_id: int = field(default=0)
    username: str = field(default="")
    email: str = field(default="")


@dataclass(frozen=True)
class UserUpdatedEvent(DomainEvent):
    """用户更新事件"""
    user_id: int = field(default=0)
    old_username: str = field(default=None)
    new_username: str = field(default=None)
