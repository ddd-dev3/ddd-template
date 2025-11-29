from abc import ABC, abstractmethod
from typing import Generic, TypeVar


T = TypeVar('T')


class Specification(ABC, Generic[T]):
    """规约模式的基类，用于封装业务规则。
    
    规约模式用于：
    - 将业务规则封装为独立的对象
    - 支持规则的组合（与、或、非）
    - 提高代码的可读性和可维护性
    """

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """检查候选对象是否满足规约
        
        Args:
            candidate: 要检查的候选对象
            
        Returns:
            如果满足规约返回True，否则返回False
        """
        raise NotImplementedError

    def and_(self, other: 'Specification[T]') -> 'AndSpecification[T]':
        """与操作：两个规约都必须满足"""
        return AndSpecification(self, other)

    def or_(self, other: 'Specification[T]') -> 'OrSpecification[T]':
        """或操作：至少一个规约必须满足"""
        return OrSpecification(self, other)

    def not_(self) -> 'NotSpecification[T]':
        """非操作：规约不能满足"""
        return NotSpecification(self)
    
    def __and__(self, other: 'Specification[T]') -> 'AndSpecification[T]':
        """支持 & 操作符"""
        return self.and_(other)
    
    def __or__(self, other: 'Specification[T]') -> 'OrSpecification[T]':
        """支持 | 操作符"""
        return self.or_(other)
    
    def __invert__(self) -> 'NotSpecification[T]':
        """支持 ~ 操作符"""
        return self.not_()


class AndSpecification(Specification[T]):
    """与规约：两个规约都必须满足"""

    def __init__(self, left: Specification[T], right: Specification[T]):
        self.left = left
        self.right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        return (
            self.left.is_satisfied_by(candidate)
            and self.right.is_satisfied_by(candidate)
        )
    
    def __repr__(self) -> str:
        return f"({self.left} AND {self.right})"


class OrSpecification(Specification[T]):
    """或规约：至少一个规约必须满足"""

    def __init__(self, left: Specification[T], right: Specification[T]):
        self.left = left
        self.right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        return (
            self.left.is_satisfied_by(candidate)
            or self.right.is_satisfied_by(candidate)
        )
    
    def __repr__(self) -> str:
        return f"({self.left} OR {self.right})"


class NotSpecification(Specification[T]):
    """非规约：规约不能满足"""

    def __init__(self, spec: Specification[T]):
        self.spec = spec

    def is_satisfied_by(self, candidate: T) -> bool:
        return not self.spec.is_satisfied_by(candidate)
    
    def __repr__(self) -> str:
        return f"(NOT {self.spec})"


# 常用的复合规约
class AlwaysTrueSpecification(Specification[T]):
    """总是满足的规约"""
    
    def is_satisfied_by(self, candidate: T) -> bool:
        return True
    
    def __repr__(self) -> str:
        return "AlwaysTrue"


class AlwaysFalseSpecification(Specification[T]):
    """总是不满足的规约"""
    
    def is_satisfied_by(self, candidate: T) -> bool:
        return False
    
    def __repr__(self) -> str:
        return "AlwaysFalse"


__all__ = [
    'Specification',
    'AndSpecification',
    'OrSpecification',
    'NotSpecification',
    'AlwaysTrueSpecification',
    'AlwaysFalseSpecification',
]