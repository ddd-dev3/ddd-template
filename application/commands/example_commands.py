"""
示例命令

演示如何定义命令。
"""

from dataclasses import dataclass
from . import Command


@dataclass
class CreateUserCommand(Command):
    """创建用户命令"""
    name: str
    email: str


@dataclass
class UpdateUserCommand(Command):
    """更新用户命令"""
    user_id: int
    name: str = None
    email: str = None
