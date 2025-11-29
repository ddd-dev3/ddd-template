from abc import ABC
from dataclasses import field, dataclass
from typing import List, Any
from .base_entity import BaseEntity
import logging


@dataclass(eq=False)
class BaseAggregateRoot(BaseEntity, ABC):
    """聚合根的基类。
    
    聚合根特征：
    - 是实体的特殊形式
    - 维护聚合边界
    - 确保聚合内的一致性
    - 产生领域事件
    """

    _domain_events: List[Any] = field(default_factory=list, init=False, repr=False)
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self):
        """初始化logger，使用具体类的名称"""
        super().__post_init__() if hasattr(super(), '__post_init__') else None
        self._logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def add_domain_event(self, event: Any) -> None:
        """将领域事件添加到内部列表。
        
        Args:
            event: 要添加的领域事件
        """
        self._logger.debug(
            f"Aggregate {self.__class__.__name__} (ID: {self.id}) "
            f"adding event: {type(event).__name__}"
        )
        self._domain_events.append(event)

    def clear_domain_events(self) -> None:
        """清除内部列表中的所有领域事件。"""
        events_count = len(self._domain_events)
        if events_count > 0:
            self._logger.debug(
                f"Aggregate {self.__class__.__name__} (ID: {self.id}) "
                f"clearing {events_count} events."
            )
        self._domain_events.clear()

    def pull_domain_events(self) -> List[Any]:
        """获取并清除所有领域事件（原子操作）。
        
        Returns:
            领域事件列表
        """
        events = self._domain_events[:]
        self.clear_domain_events()
        return events

    @property
    def domain_events(self) -> List[Any]:
        """返回内部领域事件列表的副本（只读）。
        
        Returns:
            领域事件列表的副本
        """
        return self._domain_events[:]

    @property
    def has_domain_events(self) -> bool:
        """检查是否有待处理的领域事件。
        
        Returns:
            如果有待处理的事件返回True，否则返回False
        """
        return len(self._domain_events) > 0

