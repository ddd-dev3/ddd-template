from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List

try:
    # Prefer local import path if available
    from .specifications.specification import Specification  # type: ignore
except Exception:  # pragma: no cover - fallback for early scaffolding
    class Specification:  # minimal placeholder
        def is_satisfied_by(self, candidate: object) -> bool:  # noqa: D401
            return True


TEntity = TypeVar("TEntity")
TId = TypeVar("TId")


class BaseRepository(ABC, Generic[TEntity, TId]):
    """通用仓储接口（领域层）。

    - 仅定义抽象契约，不依赖具体存储技术
    - 具体实现放在基础设施层（infrastructure）
    """

    @abstractmethod
    def add(self, entity: TEntity) -> None:
        """添加实体"""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, entity_id: TId) -> Optional[TEntity]:
        """根据ID获取实体"""
        raise NotImplementedError

    @abstractmethod
    def remove(self, entity: TEntity) -> None:
        """移除实体"""
        raise NotImplementedError

    def list(self, specification: Optional[Specification] = None) -> List[TEntity]:
        """按规约列出实体；默认返回空列表，子类可覆盖实现"""
        return []

