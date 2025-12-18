"""处理邮件命令"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from domain.mail.repositories.email_repository import EmailRepository
from application.verification.services.mail_request_matching_service import (
    MailRequestMatchingService,
)


@dataclass
class ProcessEmailCommand:
    """处理邮件命令

    Attributes:
        email_id: 要处理的邮件 ID
    """

    email_id: UUID


@dataclass
class ProcessEmailResult:
    """命令执行结果

    Attributes:
        success: 命令是否成功执行
        matched: 是否匹配到等待请求
        wait_request_id: 匹配的等待请求 ID
        extraction_type: 提取类型（code/link）
        extraction_value: 提取的值
        message: 结果消息
        error_code: 错误代码（失败时）
    """

    success: bool
    matched: bool = False
    wait_request_id: Optional[UUID] = None
    extraction_type: Optional[str] = None
    extraction_value: Optional[str] = None
    message: str = ""
    error_code: Optional[str] = None


class ProcessEmailHandler:
    """处理邮件命令处理器

    职责：
    1. 验证邮件存在且未处理
    2. 调用 MailRequestMatchingService 执行匹配
    3. 返回处理结果
    """

    def __init__(
        self,
        email_repo: EmailRepository,
        matching_service: MailRequestMatchingService,
    ):
        """初始化处理器

        Args:
            email_repo: 邮件仓储
            matching_service: 邮件匹配服务
        """
        self._email_repo = email_repo
        self._matching_service = matching_service

    def handle(self, command: ProcessEmailCommand) -> ProcessEmailResult:
        """处理命令

        Args:
            command: 处理邮件命令

        Returns:
            ProcessEmailResult 命令执行结果
        """
        # 1. 获取邮件
        email = self._email_repo.get_by_id(command.email_id)
        if email is None:
            return ProcessEmailResult(
                success=False,
                message=f"Email not found: {command.email_id}",
                error_code="EMAIL_NOT_FOUND",
            )

        # 2. 检查是否已处理
        if email.is_processed:
            return ProcessEmailResult(
                success=False,
                message="Email already processed",
                error_code="EMAIL_ALREADY_PROCESSED",
            )

        # 3. 执行匹配
        match_result = self._matching_service.process_email(email)

        return ProcessEmailResult(
            success=True,
            matched=match_result.matched,
            wait_request_id=match_result.wait_request_id,
            extraction_type=match_result.extraction_type,
            extraction_value=match_result.extraction_value,
            message=match_result.message,
        )
