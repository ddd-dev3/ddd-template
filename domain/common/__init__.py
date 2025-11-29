"""
领域层通用基础类

提供 DDD 战术设计的基础抽象。
"""

from .base_entity import BaseEntity
from .base_aggregate import BaseAggregateRoot
from .base_value_object import BaseValueObject
from .base_event import DomainEvent
from .base_repository import BaseRepository
from .domain_service import DomainService
from .specification import Specification
from .exceptions import (
    DomainException,
    EntityNotFoundException,
    BusinessRuleViolationException,
    DomainValidationException,
)

# 别名（更简洁的命名）
Entity = BaseEntity
AggregateRoot = BaseAggregateRoot
Aggregate = BaseAggregateRoot
ValueObject = BaseValueObject
Repository = BaseRepository

__all__ = [
    # 基础类
    "BaseEntity",
    "BaseAggregateRoot",
    "BaseValueObject",
    "DomainEvent",
    "BaseRepository",
    "DomainService",
    "Specification",
    # 别名
    "Entity",
    "AggregateRoot",
    "Aggregate",
    "ValueObject",
    "Repository",
    # 异常
    "DomainException",
    "EntityNotFoundException",
    "BusinessRuleViolationException",
    "DomainValidationException",
]
