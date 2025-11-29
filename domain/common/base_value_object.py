from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class BaseValueObject(ABC):
    """值对象的基类。
    
    值对象特征：
    - 不可变（frozen=True）
    - 基于值的相等性（dataclass默认行为）
    - 没有身份标识
    - 可替换性
    """

    def __post_init__(self):
        """子类可以在这里添加验证逻辑"""
        self.validate()

    def validate(self) -> None:
        """验证值对象的有效性，子类应该重写此方法"""
        pass

