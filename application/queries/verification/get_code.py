"""查询验证码/链接的 Query"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class GetCodeQuery:
    """查询验证码/链接的 Query

    用于通过 request_id 查询等待请求的状态和提取结果。
    这是一个纯读取操作，遵循 CQRS 模式。

    Attributes:
        request_id: 等待请求的唯一标识符
    """

    request_id: UUID
