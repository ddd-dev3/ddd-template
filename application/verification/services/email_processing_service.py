"""邮件批量处理服务"""

import asyncio
from dataclasses import dataclass
from typing import List, Optional
import logging

from domain.mail.repositories.email_repository import EmailRepository
from application.verification.services.mail_request_matching_service import (
    MailRequestMatchingService,
    MatchResult,
)


@dataclass
class BatchProcessResult:
    """批量处理结果

    Attributes:
        total_processed: 总处理数量
        matched_count: 匹配成功数量
        extraction_success_count: 提取成功数量
        results: 每个邮件的处理结果列表
    """

    total_processed: int
    matched_count: int
    extraction_success_count: int
    results: List[MatchResult]


class EmailProcessingService:
    """邮件批量处理服务

    职责：
    - 获取未处理的邮件
    - 批量调用 MailRequestMatchingService 处理
    - 返回处理统计结果

    支持同步和异步两种处理模式。
    """

    def __init__(
        self,
        email_repo: EmailRepository,
        matching_service: MailRequestMatchingService,
        logger: Optional[logging.Logger] = None,
    ):
        """初始化服务

        Args:
            email_repo: 邮件仓储
            matching_service: 邮件匹配服务
            logger: 日志记录器
        """
        self._email_repo = email_repo
        self._matching_service = matching_service
        self._logger = logger or logging.getLogger(__name__)

    def process_unprocessed_emails(self, limit: int = 100) -> BatchProcessResult:
        """处理所有未处理的邮件（同步模式）

        获取未处理邮件，逐个调用匹配服务处理。

        Args:
            limit: 单次处理的最大邮件数

        Returns:
            BatchProcessResult 批量处理结果
        """
        emails = self._email_repo.list_unprocessed(limit=limit)
        results: List[MatchResult] = []
        matched_count = 0
        extraction_success_count = 0

        self._logger.info(f"Processing {len(emails)} unprocessed emails")

        for email in emails:
            try:
                result = self._matching_service.process_email(email)
                results.append(result)

                if result.matched:
                    matched_count += 1
                    if result.extraction_value:
                        extraction_success_count += 1

            except Exception as e:
                self._logger.error(
                    f"Failed to process email {email.id}: {e}"
                )
                results.append(
                    MatchResult(
                        matched=False,
                        message=f"Processing error: {str(e)}",
                    )
                )

        self._logger.info(
            f"Batch processing complete: {len(emails)} processed, "
            f"{matched_count} matched, {extraction_success_count} extracted"
        )

        return BatchProcessResult(
            total_processed=len(emails),
            matched_count=matched_count,
            extraction_success_count=extraction_success_count,
            results=results,
        )

    async def process_unprocessed_emails_async(
        self, limit: int = 100
    ) -> BatchProcessResult:
        """处理所有未处理的邮件（异步模式）

        使用 asyncio.to_thread 包装同步处理，
        适合在异步上下文中调用。

        Args:
            limit: 单次处理的最大邮件数

        Returns:
            BatchProcessResult 批量处理结果
        """
        return await asyncio.to_thread(
            self.process_unprocessed_emails, limit
        )
