"""Verification 领域模块

验证码服务的领域层，包含等待请求相关的实体、值对象和仓储接口。
"""

from domain.verification.entities.wait_request import WaitRequest
from domain.verification.value_objects.wait_request_status import WaitRequestStatus
from domain.verification.repositories.wait_request_repository import WaitRequestRepository

__all__ = [
    "WaitRequest",
    "WaitRequestStatus",
    "WaitRequestRepository",
]
