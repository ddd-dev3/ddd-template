"""查询验证码 API 路由"""

from typing import Callable, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from application.queries.verification.get_code import GetCodeQuery
from application.handlers.verification.get_code_handler import (
    CodeResult,
    GetCodeHandler,
)


router = APIRouter(tags=["Verification"])


# ============ Handler 依赖注入 ============

_get_code_handler_getter: Optional[Callable[[], GetCodeHandler]] = None


def set_get_code_handler_getter(getter: Callable[[], GetCodeHandler]) -> None:
    """设置 get_code handler 获取器（由 DI 容器调用）"""
    global _get_code_handler_getter
    _get_code_handler_getter = getter


def get_code_handler() -> Optional[GetCodeHandler]:
    """获取 GetCodeHandler 实例"""
    if _get_code_handler_getter is None:
        return None
    return _get_code_handler_getter()


# ============ Response DTOs ============


class CodeResponseDTO(BaseModel):
    """验证码/链接响应 DTO（状态码 200）

    当请求已完成时返回此响应，格式与 Webhook 回调一致。

    Attributes:
        request_id: 请求 ID
        type: 类型 ("code" 或 "link")
        value: 验证码或链接值
        email: 邮箱地址
        service: 服务名称
        received_at: 接收时间（ISO 格式）
    """

    request_id: str = Field(..., description="请求 ID")
    type: str = Field(..., description="类型 (code/link)")
    value: str = Field(..., description="验证码或链接")
    email: str = Field(..., description="邮箱地址")
    service: str = Field(..., description="服务名称")
    received_at: Optional[str] = Field(None, description="接收时间 (ISO 格式)")


class PendingResponseDTO(BaseModel):
    """等待中响应 DTO（状态码 202）

    当请求仍在等待邮件时返回此响应。

    Attributes:
        request_id: 请求 ID
        status: 状态（固定为 "pending"）
        message: 提示消息
    """

    request_id: str = Field(..., description="请求 ID")
    status: str = Field(default="pending", description="状态")
    message: str = Field(..., description="提示消息")


class GoneResponseDTO(BaseModel):
    """已终止响应 DTO（状态码 410）

    当请求已取消或失败时返回此响应。

    Attributes:
        request_id: 请求 ID
        status: 状态 ("cancelled" 或 "failed")
        reason: 原因
    """

    request_id: str = Field(..., description="请求 ID")
    status: str = Field(..., description="状态 (cancelled/failed)")
    reason: Optional[str] = Field(None, description="原因")


class ErrorResponseDTO(BaseModel):
    """错误响应 DTO（状态码 404）"""

    detail: str = Field(..., description="错误详情")


# ============ API Endpoints ============


@router.get(
    "/code/{request_id}",
    responses={
        200: {"model": CodeResponseDTO, "description": "验证码/链接信息（已完成）"},
        202: {"model": PendingResponseDTO, "description": "正在等待验证邮件"},
        404: {"model": ErrorResponseDTO, "description": "请求不存在"},
        410: {"model": GoneResponseDTO, "description": "请求已取消或失败"},
    },
    summary="查询验证码/链接",
    description="""
    根据请求 ID 查询验证码或链接。

    **状态说明：**
    - **200 OK**: 请求已完成，返回验证码/链接信息
    - **202 Accepted**: 请求存在但尚未收到验证邮件，正在等待中
    - **404 Not Found**: 请求 ID 不存在
    - **410 Gone**: 请求已取消或失败（不可恢复）

    **使用场景：**
    - 作为 Webhook 回调的备用方案
    - 当 Webhook 不可用时主动轮询查询
    - 确认等待请求的当前状态

    **响应格式：**
    - 200 响应格式与 Webhook 回调 payload 一致
    """,
)
def query_code(
    request_id: UUID,
    handler: Optional[GetCodeHandler] = Depends(get_code_handler),
):
    """
    查询验证码/链接

    - 根据 request_id 查询等待请求状态
    - 返回相应状态的响应
    """
    if handler is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Handler not configured. Please configure dependency injection.",
        )

    # 创建查询
    query = GetCodeQuery(request_id=request_id)

    # 执行查询
    result: CodeResult = handler.handle(query)

    # 处理结果
    if result.status == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )

    if result.status == "completed":
        return JSONResponse(status_code=status.HTTP_200_OK, content=result.data)

    if result.status == "pending":
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "request_id": str(request_id),
                "status": "pending",
                "message": result.message,
            },
        )

    # cancelled or failed
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "request_id": str(request_id),
            "status": result.status,
            "reason": result.message,
        },
    )
