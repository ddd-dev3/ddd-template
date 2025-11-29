"""
示例事件处理器

演示如何订阅和处理领域事件。
一个事件可以有多个处理器（与 Command 不同）。
"""

from infrastructure.events import on_event
from application.events.example_events import UserCreatedEvent, UserUpdatedEvent


# ============ UserCreatedEvent 的多个处理器 ============

@on_event(UserCreatedEvent)
async def send_welcome_email(event: UserCreatedEvent):
    """
    处理器1：发送欢迎邮件

    当用户创建后，发送欢迎邮件。
    """
    print(f"📧 [邮件服务] 发送欢迎邮件给: {event.email}")
    # 实际实现：调用邮件服务
    # await email_service.send_welcome(event.email, event.username)


@on_event(UserCreatedEvent)
async def log_user_creation(event: UserCreatedEvent):
    """
    处理器2：记录日志

    当用户创建后，记录审计日志。
    """
    print(f"📝 [审计日志] 用户创建: id={event.user_id}, username={event.username}")
    # 实际实现：写入审计日志
    # await audit_log.record("USER_CREATED", event)


@on_event(UserCreatedEvent)
async def notify_admin(event: UserCreatedEvent):
    """
    处理器3：通知管理员

    当用户创建后，通知管理员（可选）。
    """
    print(f"🔔 [通知服务] 新用户注册: {event.username}")
    # 实际实现：发送通知
    # await notification_service.notify_admin(f"New user: {event.username}")


# ============ UserUpdatedEvent 处理器 ============

@on_event(UserUpdatedEvent)
async def log_user_update(event: UserUpdatedEvent):
    """
    记录用户更新日志
    """
    print(f"📝 [审计日志] 用户更新: id={event.user_id}, {event.old_username} -> {event.new_username}")
