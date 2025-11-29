from abc import ABC
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime, timezone


@dataclass(eq=False)
class BaseEntity(ABC):
    """领域实体的基类。
    
    实体特征：
    - 拥有唯一标识符(ID)
    - 基于ID的相等性比较
    - 可变状态
    - 具有生命周期
    """

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
        compare=False,
        repr=False,
    )
    updated_at: Optional[datetime] = field(
        default=None,
        compare=False,
        repr=False,
    )
    version: int = field(default=0, compare=False, repr=False)  # 用于乐观锁

    def __eq__(self, other: Any) -> bool:
        """Entities are equal if their IDs are equal."""
        if not isinstance(other, BaseEntity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Entities are hashed based on their ID."""
        return hash(self.id)

    def update_timestamp(self) -> None:
        """更新修改时间戳"""
        self.updated_at = datetime.now(timezone.utc)

