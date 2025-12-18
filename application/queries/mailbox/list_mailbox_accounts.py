"""查询邮箱账号列表"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class ListMailboxAccountsQuery:
    """
    查询邮箱账号列表

    Attributes:
        service: 按占用服务筛选
        status: 按状态筛选 (available/occupied)
        page: 页码，从 1 开始
        limit: 每页数量
    """

    service: Optional[str] = None
    status: Optional[str] = None
    page: int = 1
    limit: int = 20


@dataclass
class MailboxAccountItem:
    """
    邮箱账号列表项

    不包含敏感信息（密码）
    """

    id: str
    username: str
    type: str
    imap_server: str
    imap_port: int
    domain: Optional[str]
    status: str
    occupied_by_service: Optional[str]
    created_at: str


@dataclass
class PaginationInfo:
    """分页信息"""

    total: int
    page: int
    limit: int
    total_pages: int


@dataclass
class ListMailboxAccountsResult:
    """
    查询邮箱账号列表结果

    Attributes:
        success: 是否成功
        data: 邮箱账号列表
        pagination: 分页信息
        message: 消息
        error_code: 错误码（失败时）
    """

    success: bool
    data: List[MailboxAccountItem] = field(default_factory=list)
    pagination: Optional[PaginationInfo] = None
    message: str = ""
    error_code: Optional[str] = None
