"""注册等待请求 API 路由"""

from typing import Callable, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl

from application.commands.verification.register_wait_request import (
    RegisterWaitRequestCommand,
    RegisterWaitRequestHandler,
    RegisterWaitRequestResult,
)


router = APIRouter(tags=["Verification"])


# ============ Handler 依赖注入 ============

_register_handler_getter: Optional[Callable[[], RegisterWaitRequestHandler]] = None


def set_register_handler_getter(
    getter: Callable[[], RegisterWaitRequestHandler]
) -> None:
    """设置 register handler 获取器（由 DI 容器调用）"""
    global _register_handler_getter
    _register_handler_getter = getter


def get_register_handler() -> Optional[RegisterWaitRequestHandler]:
    """获取 RegisterWaitRequestHandler 实例"""
    if _register_handler_getter is None:
        return None
    return _register_handler_getter()


# ============ Request/Response DTOs ============


class RegisterWaitRequestDTO(BaseModel):
    """注册等待请求 DTO

    Attributes:
        email: 邮箱地址（必须是已添加到系统的邮箱）
        service: 业务服务名称（如 "claude", "openai" 等）
        callback_url: Webhook 回调地址（验证信息提取后调用）
    """

    email: str = Field(
        ...,
        description="邮箱地址",
        min_length=1,
        examples=["user@example.com"],
    )
    service: str = Field(
        ...,
        description="业务服务名称",
        min_length=1,
        examples=["claude", "openai"],
    )
    callback_url: HttpUrl = Field(
        ...,
        description="Webhook 回调地址",
        examples=["https://api.example.com/webhook/verification"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "service": "claude",
                    "callback_url": "https://api.example.com/webhook/verification",
                }
            ]
        }
    }


class RegisterWaitResponseDTO(BaseModel):
    """注册等待响应 DTO

    Attributes:
        request_id: 创建的等待请求 ID（用于后续查询或取消）
        message: 结果消息
    """

    request_id: UUID = Field(..., description="等待请求 ID")
    message: str = Field(..., description="结果消息")


class ErrorResponseDTO(BaseModel):
    """错误响应 DTO"""

    detail: str = Field(..., description="错误详情")
    error_code: Optional[str] = Field(default=None, description="错误代码")


# ============ 错误码映射 ============

ERROR_CODE_TO_STATUS = {
    "MAILBOX_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "MAILBOX_OCCUPIED": status.HTTP_409_CONFLICT,
}


# ============ API Endpoints ============


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterWaitResponseDTO,
    responses={
        404: {"model": ErrorResponseDTO, "description": "邮箱不存在"},
        409: {"model": ErrorResponseDTO, "description": "邮箱已被其他服务占用"},
        422: {"model": ErrorResponseDTO, "description": "请求参数验证失败"},
    },
    summary="注册等待请求",
    description="""
    声明要用某个邮箱注册某服务，系统将监听验证邮件。

    **流程：**
    1. 验证邮箱是否存在于系统中
    2. 检查邮箱是否可用（未被其他服务占用）
    3. 将邮箱标记为被指定服务占用
    4. 创建等待请求记录
    5. 返回等待请求 ID

    **回调机制：**
    - 当系统收到验证邮件并成功提取验证码/链接后
    - 将通过 POST 请求调用 `callback_url`
    - 请求体包含 `request_id`、`type`、`value`、`email`、`service` 等信息

    **注意：**
    - 邮箱必须先通过 `/accounts` API 添加到系统
    - 同一邮箱同一时间只能被一个服务占用
    - 等待请求完成或取消后，邮箱自动释放
    """,
)
def register_wait_request(
    request: RegisterWaitRequestDTO,
    handler: Optional[RegisterWaitRequestHandler] = Depends(get_register_handler),
) -> RegisterWaitResponseDTO:
    """
    注册等待请求

    - 声明要用某个邮箱注册某服务
    - 系统将监听验证邮件
    - 返回等待请求 ID
    """
    if handler is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Handler not configured. Please configure dependency injection.",
        )

    # 创建命令
    command = RegisterWaitRequestCommand(
        email=request.email,
        service_name=request.service,
        callback_url=str(request.callback_url),
    )

    # 执行命令
    result: RegisterWaitRequestResult = handler.handle(command)

    # 处理结果
    if not result.success:
        status_code = ERROR_CODE_TO_STATUS.get(
            result.error_code,
            status.HTTP_400_BAD_REQUEST,
        )
        raise HTTPException(status_code=status_code, detail=result.message)

    # 返回成功响应
    return RegisterWaitResponseDTO(
        request_id=result.request_id,
        message=result.message,
    )
