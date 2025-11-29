from abc import ABC
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class DomainEvent(ABC):
    """领域事件的基类。
    
    领域事件特征：
    - 不可变（frozen=True）
    - 记录已发生的事实
    - 包含事件发生的时间
    - 可追踪（通过correlation_id和causation_id）
    """

    # 必需字段
    aggregate_id: UUID  # 关联的聚合根ID
    
    # 自动生成字段
    event_id: UUID = field(default_factory=uuid4, init=False)
    occurred_on: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), 
        init=False
    )
    
    # 可选字段
    correlation_id: Optional[UUID] = field(default=None)  # 用于跟踪相关事件链
    causation_id: Optional[UUID] = field(default=None)  # 触发此事件的事件ID
    metadata: Optional[Dict[str, Any]] = field(default=None)  # 额外元数据

    @property
    def event_name(self) -> str:
        """返回事件名称（默认为类名）"""
        return self.__class__.__name__

    @property
    def event_version(self) -> str:
        """返回事件版本，子类可覆盖"""
        return "1.0"

