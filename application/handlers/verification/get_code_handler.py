"""查询验证码 Handler"""

from dataclasses import dataclass
from typing import Optional
import logging

from application.queries.verification.get_code import GetCodeQuery
from domain.verification.repositories.wait_request_repository import WaitRequestRepository


@dataclass
class CodeResult:
    """查询结果

    Attributes:
        found: 是否找到请求
        status: 状态 ("completed", "pending", "cancelled", "failed", "not_found")
        data: 完成时的数据（包含 request_id, type, value, email, service, received_at）
        message: 消息（等待中或失败原因）
    """

    found: bool
    status: str
    data: Optional[dict] = None
    message: Optional[str] = None


class GetCodeHandler:
    """查询验证码 Handler

    处理 GetCodeQuery，返回等待请求的状态和提取结果。
    这是一个纯读取操作，不修改任何状态。
    """

    def __init__(
        self,
        wait_request_repo: WaitRequestRepository,
        logger: Optional[logging.Logger] = None,
    ):
        """初始化 Handler

        Args:
            wait_request_repo: 等待请求仓储
            logger: 日志记录器
        """
        self._wait_request_repo = wait_request_repo
        self._logger = logger or logging.getLogger(__name__)

    def handle(self, query: GetCodeQuery) -> CodeResult:
        """处理查询请求

        Args:
            query: 查询对象，包含 request_id

        Returns:
            CodeResult 包含查询结果
        """
        self._logger.debug(f"Handling GetCodeQuery for request_id={query.request_id}")

        wait_request = self._wait_request_repo.get_by_id(query.request_id)

        if wait_request is None:
            self._logger.debug(f"Request {query.request_id} not found")
            return CodeResult(found=False, status="not_found")

        if wait_request.is_completed:
            # 判断提取类型：URL 为 link，否则为 code
            extraction_type = self._determine_extraction_type(
                wait_request.extraction_result
            )

            self._logger.debug(
                f"Request {query.request_id} completed with {extraction_type}"
            )
            return CodeResult(
                found=True,
                status="completed",
                data={
                    "request_id": str(wait_request.id),
                    "type": extraction_type,
                    "value": wait_request.extraction_result,
                    "email": wait_request.email,
                    "service": wait_request.service_name,
                    "received_at": (
                        wait_request.completed_at.isoformat()
                        if wait_request.completed_at
                        else None
                    ),
                },
            )

        if wait_request.is_pending:
            self._logger.debug(f"Request {query.request_id} is still pending")
            return CodeResult(
                found=True,
                status="pending",
                message="正在等待验证邮件",
            )

        # CANCELLED or FAILED
        self._logger.debug(
            f"Request {query.request_id} is {wait_request.status.value}"
        )
        return CodeResult(
            found=True,
            status=wait_request.status.value,
            message=wait_request.failure_reason,
        )

    def _determine_extraction_type(self, value: Optional[str]) -> str:
        """判断提取类型

        根据提取值的内容判断是验证码还是链接。

        Args:
            value: 提取的值

        Returns:
            "link" 如果值像 URL，否则返回 "code"
        """
        if value is None:
            return "code"

        # 如果值以 http:// 或 https:// 开头，视为链接
        if value.startswith("http://") or value.startswith("https://"):
            return "link"

        return "code"
