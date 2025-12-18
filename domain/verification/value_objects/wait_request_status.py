"""等待请求状态值对象"""

from enum import Enum


class WaitRequestStatus(str, Enum):
    """等待请求状态

    Attributes:
        PENDING: 等待中 - 请求已创建，等待验证邮件
        COMPLETED: 已完成 - 收到验证码/链接并成功回调
        CANCELLED: 已取消 - 用户主动取消请求
        FAILED: 失败 - 回调失败或超时
    """

    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
