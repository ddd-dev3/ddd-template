"""
事件总线（Event Bus）

基于 pyventus 库实现事件的发布和分发。

特点：
- 一个事件可以有多个处理器
- 支持同步和异步处理器
- 支持事件对象（推荐）和字符串事件名
- 简洁的装饰器 API
"""

from typing import Type, Optional, Callable, Union
from pyventus.events import EventLinker, AsyncIOEventEmitter

from domain.common.base_event import DomainEvent


# ============ 全局事件发射器 ============

_event_emitter: Optional[AsyncIOEventEmitter] = None


def get_event_emitter() -> AsyncIOEventEmitter:
    """获取全局事件发射器"""
    global _event_emitter
    if _event_emitter is None:
        _event_emitter = AsyncIOEventEmitter()
    return _event_emitter


# 便捷访问
event_emitter = get_event_emitter()


# ============ 装饰器 ============

def on_event(event_type: Union[Type[DomainEvent], str]):
    """
    事件处理器装饰器

    用法：
        # 方式1：使用事件类（推荐）
        @on_event(UserCreatedEvent)
        async def on_user_created(event: UserCreatedEvent):
            print(f"User created: {event.username}")

        # 方式2：使用字符串事件名
        @on_event("UserCreated")
        async def on_user_created(event):
            print(f"User created: {event}")

        # 同步处理器也支持
        @on_event(UserCreatedEvent)
        def on_user_created_sync(event: UserCreatedEvent):
            print(f"User created: {event.username}")
    """
    return EventLinker.on(event_type)


# ============ 便捷函数 ============

def emit(event: DomainEvent) -> None:
    """
    发布事件

    pyventus 的 emit 是同步调用，但内部会处理异步 handler。

    用法：
        event_emitter.emit(UserCreatedEvent(aggregate_id=uuid4(), user_id=1, username="test"))
        # 或
        emit(UserCreatedEvent(...))
    """
    get_event_emitter().emit(event)
