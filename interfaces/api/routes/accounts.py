"""邮箱账号 API 路由"""

from datetime import datetime, timezone
from typing import Optional, Callable, List

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field

from application.commands.mailbox.add_mailbox_account import AddMailboxAccountCommand
from application.commands.mailbox.delete_mailbox_account import DeleteMailboxAccountCommand
from application.handlers.mailbox.add_mailbox_account_handler import (
    AddMailboxAccountHandler,
    AddMailboxAccountResult,
)
from application.handlers.mailbox.list_mailbox_accounts_handler import ListMailboxAccountsHandler
from application.handlers.mailbox.delete_mailbox_account_handler import DeleteMailboxAccountHandler
from application.queries.mailbox.list_mailbox_accounts import ListMailboxAccountsQuery


router = APIRouter(prefix="/accounts", tags=["Mailbox Accounts"])


# ============ Handler 依赖注入 ============

# 全局 handler getter，由 DI 容器在启动时设置
_handler_getter: Optional[Callable[[], AddMailboxAccountHandler]] = None


def set_handler_getter(getter: Callable[[], AddMailboxAccountHandler]) -> None:
    """设置 handler 获取器（由 DI 容器调用）"""
    global _handler_getter
    _handler_getter = getter


def get_add_mailbox_handler() -> Optional[AddMailboxAccountHandler]:
    """获取 AddMailboxAccountHandler 实例"""
    if _handler_getter is None:
        return None
    return _handler_getter()


# List handler getter
_list_handler_getter: Optional[Callable[[], ListMailboxAccountsHandler]] = None


def set_list_handler_getter(getter: Callable[[], ListMailboxAccountsHandler]) -> None:
    """设置 list handler 获取器（由 DI 容器调用）"""
    global _list_handler_getter
    _list_handler_getter = getter


def get_list_mailbox_handler() -> Optional[ListMailboxAccountsHandler]:
    """获取 ListMailboxAccountsHandler 实例"""
    if _list_handler_getter is None:
        return None
    return _list_handler_getter()


# Delete handler getter
_delete_handler_getter: Optional[Callable[[], DeleteMailboxAccountHandler]] = None


def set_delete_handler_getter(getter: Callable[[], DeleteMailboxAccountHandler]) -> None:
    """设置 delete handler 获取器（由 DI 容器调用）"""
    global _delete_handler_getter
    _delete_handler_getter = getter


def get_delete_mailbox_handler() -> Optional[DeleteMailboxAccountHandler]:
    """获取 DeleteMailboxAccountHandler 实例"""
    if _delete_handler_getter is None:
        return None
    return _delete_handler_getter()


# ============ Request/Response DTOs ============

class AddMailboxAccountRequest(BaseModel):
    """
    添加邮箱账号请求

    Attributes:
        type: 邮箱类型（domain_catchall 或 hotmail）
        username: 邮箱地址
        password: IMAP 密码
        imap_server: IMAP 服务器地址
        imap_port: IMAP 端口，默认 993
        domain: 域名（仅 domain_catchall 需要）
    """

    type: str = Field(..., description="邮箱类型: domain_catchall 或 hotmail")
    username: str = Field(..., description="邮箱地址", min_length=1)
    password: str = Field(..., description="IMAP 密码", min_length=1)
    imap_server: str = Field(..., description="IMAP 服务器地址", min_length=1)
    imap_port: int = Field(default=993, description="IMAP 端口", ge=1, le=65535)
    domain: Optional[str] = Field(default=None, description="域名（仅 domain_catchall 需要）")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "domain_catchall",
                    "username": "admin@example.com",
                    "password": "secret123",
                    "imap_server": "imap.example.com",
                    "imap_port": 993,
                    "domain": "example.com"
                },
                {
                    "type": "hotmail",
                    "username": "user@hotmail.com",
                    "password": "app_password",
                    "imap_server": "outlook.office365.com",
                    "imap_port": 993
                }
            ]
        }
    }


class MailboxAccountResponse(BaseModel):
    """
    邮箱账号响应（不包含密码）

    Attributes:
        id: 邮箱 ID
        username: 邮箱地址
        type: 邮箱类型
        imap_server: IMAP 服务器地址
        imap_port: IMAP 端口
        domain: 域名
        status: 邮箱状态
        created_at: 创建时间
    """

    id: str = Field(..., description="邮箱 ID")
    username: str = Field(..., description="邮箱地址")
    type: str = Field(..., description="邮箱类型")
    imap_server: str = Field(..., description="IMAP 服务器地址")
    imap_port: int = Field(..., description="IMAP 端口")
    domain: Optional[str] = Field(default=None, description="域名")
    status: str = Field(..., description="邮箱状态")
    created_at: str = Field(..., description="创建时间")


class ErrorResponse(BaseModel):
    """错误响应"""

    detail: str = Field(..., description="错误详情")
    error_code: Optional[str] = Field(default=None, description="错误代码")


class MailboxAccountListItem(BaseModel):
    """邮箱账号列表项"""

    id: str = Field(..., description="邮箱 ID")
    username: str = Field(..., description="邮箱地址")
    type: str = Field(..., description="邮箱类型")
    imap_server: str = Field(..., description="IMAP 服务器地址")
    imap_port: int = Field(..., description="IMAP 端口")
    domain: Optional[str] = Field(default=None, description="域名")
    status: str = Field(..., description="邮箱状态")
    occupied_by_service: Optional[str] = Field(default=None, description="占用服务")
    created_at: str = Field(..., description="创建时间")


class PaginationResponse(BaseModel):
    """分页信息"""

    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")


class MailboxAccountListResponse(BaseModel):
    """邮箱账号列表响应"""

    data: List[MailboxAccountListItem] = Field(..., description="邮箱账号列表")
    pagination: PaginationResponse = Field(..., description="分页信息")


class DeleteMailboxAccountResponse(BaseModel):
    """删除邮箱账号响应"""

    message: str = Field(..., description="删除结果消息")
    id: str = Field(..., description="被删除的邮箱 ID")


# ============ API Endpoints ============

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=MailboxAccountResponse,
    responses={
        400: {"model": ErrorResponse, "description": "IMAP 连接失败"},
        409: {"model": ErrorResponse, "description": "邮箱已存在"},
        422: {"model": ErrorResponse, "description": "请求参数验证失败"},
    },
    summary="添加邮箱账号",
    description="""
    添加新的邮箱账号到系统。

    **流程：**
    1. 验证请求参数
    2. 检查邮箱是否已存在
    3. 验证 IMAP 连接有效性
    4. 创建邮箱记录（密码加密存储）

    **注意：**
    - 密码将使用 Fernet 对称加密存储
    - 响应中不返回密码字段
    - domain_catchall 类型必须提供 domain 参数
    """,
)
async def add_mailbox_account(
    request: AddMailboxAccountRequest,
    handler: Optional[AddMailboxAccountHandler] = Depends(get_add_mailbox_handler),
) -> MailboxAccountResponse:
    """
    添加邮箱账号

    - 验证 IMAP 连接有效性
    - 密码加密存储
    - 响应不返回密码
    """
    # 如果没有通过 DI 注入 handler，这里会抛出错误
    # 实际使用时应该通过 set_handler_getter 配置
    if handler is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Handler not configured. Please configure dependency injection.",
        )

    # 创建命令
    command = AddMailboxAccountCommand(
        mailbox_type=request.type,
        username=request.username,
        password=request.password,
        imap_server=request.imap_server,
        imap_port=request.imap_port,
        use_ssl=True,  # 强制使用 SSL
        domain=request.domain,
    )

    # 执行命令
    result: AddMailboxAccountResult = await handler.handle(command)

    # 处理结果
    if not result.success:
        if result.error_code == "DUPLICATE_MAILBOX":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result.message,
            )
        elif result.error_code in ["IMAP_CONNECTION_ERROR", "IMAP_AUTH_ERROR"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message,
            )
        elif result.error_code == "INVALID_MAILBOX_TYPE":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result.message,
            )
        elif result.error_code == "MISSING_DOMAIN":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result.message,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message,
            )

    # 返回成功响应
    return MailboxAccountResponse(
        id=result.mailbox_id,
        username=result.username,
        type=request.type,
        imap_server=request.imap_server,
        imap_port=request.imap_port,
        domain=request.domain,
        status="available",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=MailboxAccountListResponse,
    responses={
        422: {"model": ErrorResponse, "description": "参数验证失败"},
    },
    summary="查询邮箱账号列表",
    description="""
    查询邮箱账号列表，支持分页和筛选。

    **筛选参数：**
    - `service`: 按占用服务筛选（返回被指定服务占用的邮箱）
    - `status`: 按状态筛选（available 或 occupied）

    **分页参数：**
    - `page`: 页码，从 1 开始，默认 1
    - `limit`: 每页数量，默认 20，最大 100
    """,
)
async def list_mailbox_accounts(
    service: Optional[str] = Query(default=None, description="按占用服务筛选"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="按状态筛选 (available/occupied)"),
    page: int = Query(default=1, ge=1, description="页码"),
    limit: int = Query(default=20, ge=1, le=100, description="每页数量"),
    handler: Optional[ListMailboxAccountsHandler] = Depends(get_list_mailbox_handler),
) -> MailboxAccountListResponse:
    """
    查询邮箱账号列表

    - 支持按服务和状态筛选
    - 支持分页
    """
    if handler is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Handler not configured. Please configure dependency injection.",
        )

    # 创建查询
    query = ListMailboxAccountsQuery(
        service=service,
        status=status_filter,
        page=page,
        limit=limit,
    )

    # 执行查询
    result = await handler.handle(query)

    # 处理结果
    if not result.success:
        if result.error_code == "INVALID_STATUS":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result.message,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    # 转换为响应格式
    data = [
        MailboxAccountListItem(
            id=item.id,
            username=item.username,
            type=item.type,
            imap_server=item.imap_server,
            imap_port=item.imap_port,
            domain=item.domain,
            status=item.status,
            occupied_by_service=item.occupied_by_service,
            created_at=item.created_at,
        )
        for item in result.data
    ]

    pagination = PaginationResponse(
        total=result.pagination.total,
        page=result.pagination.page,
        limit=result.pagination.limit,
        total_pages=result.pagination.total_pages,
    )

    return MailboxAccountListResponse(data=data, pagination=pagination)


@router.delete(
    "/{mailbox_id}",
    status_code=status.HTTP_200_OK,
    response_model=DeleteMailboxAccountResponse,
    responses={
        404: {"model": ErrorResponse, "description": "邮箱不存在"},
        409: {"model": ErrorResponse, "description": "邮箱被占用，无法删除"},
    },
    summary="删除邮箱账号",
    description="""
    删除指定的邮箱账号。

    **前置条件：**
    - 邮箱必须存在
    - 邮箱状态必须为 available（未被占用）

    **错误情况：**
    - 404: 邮箱 ID 不存在
    - 409: 邮箱当前被某服务占用，需要先释放占用
    """,
)
async def delete_mailbox_account(
    mailbox_id: str,
    handler: Optional[DeleteMailboxAccountHandler] = Depends(get_delete_mailbox_handler),
) -> DeleteMailboxAccountResponse:
    """
    删除邮箱账号

    - 只有 available 状态的邮箱才能删除
    - occupied 状态需要先释放占用
    """
    if handler is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Handler not configured. Please configure dependency injection.",
        )

    # 创建命令
    command = DeleteMailboxAccountCommand(mailbox_id=mailbox_id)

    # 执行命令
    result = await handler.handle(command)

    # 处理结果
    if not result.success:
        if result.error_code == "MAILBOX_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.message,
            )
        elif result.error_code == "MAILBOX_OCCUPIED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result.message,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message,
            )

    # 返回成功响应
    return DeleteMailboxAccountResponse(
        message=result.message,
        id=result.mailbox_id,
    )
