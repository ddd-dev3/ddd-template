"""
事件系统（Events）

基于 pyventus 库提供领域事件的发布/订阅机制。

使用方式：
    from infrastructure.events import event_emitter, on_event

    # 1. 定义事件（在 domain 层，继承 DomainEvent）
    @dataclass
    class UserCreatedEvent(DomainEvent):
        user_id: int
        username: str

    # 2. 定义事件处理器
    @on_event(UserCreatedEvent)
    async def on_user_created(event: UserCreatedEvent):
        print(f"User created: {event.username}")

    # 3. 发布事件
    emit(UserCreatedEvent(aggregate_id=uuid4(), user_id=1, username="test"))
"""

from .event_bus import (
    event_emitter,
    on_event,
    get_event_emitter,
    emit,
)

__all__ = [
    "event_emitter",
    "on_event",
    "get_event_emitter",
    "emit",
]

