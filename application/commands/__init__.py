"""
命令定义（Commands）

命令代表一个写操作的意图，例如：
- CreateUserCommand
- UpdateOrderCommand
- DeleteProductCommand

命令通常包含执行操作所需的数据。
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Command:
    """命令基类（可选继承）"""
    pass


@dataclass
class CommandResult:
    """命令执行结果"""
    success: bool
    data: Any = None
    error: str = None

    @classmethod
    def ok(cls, data: Any = None) -> "CommandResult":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "CommandResult":
        return cls(success=False, error=error)
