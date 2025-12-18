"""AI 提取应用服务"""

import logging
from typing import Optional

from domain.ai.services.verification_extractor import VerificationExtractor
from domain.ai.value_objects.extraction_result import ExtractionResult
from domain.ai.value_objects.extraction_type import ExtractionType
from domain.mail.entities.email import Email


class AiExtractionService:
    """
    AI 提取应用服务

    协调 Email 实体与 VerificationExtractor 领域服务，
    从邮件内容中提取验证码或验证链接。
    支持同步和异步两种调用方式。

    Attributes:
        _extractor: 验证信息提取器实例
        _logger: 日志记录器
    """

    def __init__(
        self,
        extractor: VerificationExtractor,
        logger: Optional[logging.Logger] = None,
    ):
        """
        初始化 AI 提取服务

        Args:
            extractor: 验证信息提取器（VerificationExtractor Protocol 实现）
            logger: 日志记录器
        """
        self._extractor = extractor
        self._logger = logger or logging.getLogger(__name__)

    def extract_code_from_email(
        self,
        email: Email,
        mark_as_processed: bool = False,
    ) -> ExtractionResult:
        """
        从邮件中提取验证码（同步版本）

        从邮件内容（优先纯文本，无则 HTML）中提取验证码。

        Args:
            email: 邮件实体
            mark_as_processed: 是否标记邮件为已处理（默认 False）

        Returns:
            ExtractionResult 包含提取结果
        """
        # 获取邮件内容（Email.body 已处理优先级：text > html > ""）
        content = email.body

        if not content:
            self._logger.warning(
                f"Email {email.id} has no body content, skipping extraction"
            )
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response="Empty email body",
            )

        # 调用提取器
        self._logger.debug(
            f"Extracting code from email {email.id}, "
            f"content_type={'text' if email.has_text_body else 'html'}, "
            f"content_length={len(content)}"
        )

        result = self._extractor.extract_code(content)

        # 记录结果和处理标记
        self._log_result(email, result)
        self._mark_processed_if_needed(email, mark_as_processed)

        return result

    async def extract_code_from_email_async(
        self,
        email: Email,
        mark_as_processed: bool = False,
    ) -> ExtractionResult:
        """
        从邮件中提取验证码（异步版本）

        从邮件内容（优先纯文本，无则 HTML）中提取验证码。

        Args:
            email: 邮件实体
            mark_as_processed: 是否标记邮件为已处理（默认 False）

        Returns:
            ExtractionResult 包含提取结果
        """
        content = email.body

        if not content:
            self._logger.warning(
                f"Email {email.id} has no body content, skipping extraction"
            )
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response="Empty email body",
            )

        self._logger.debug(
            f"Extracting code from email {email.id} (async), "
            f"content_type={'text' if email.has_text_body else 'html'}, "
            f"content_length={len(content)}"
        )

        result = await self._extractor.extract_code_async(content)

        self._log_result(email, result)
        self._mark_processed_if_needed(email, mark_as_processed)

        return result

    def extract_from_content(self, content: str) -> ExtractionResult:
        """
        从文本内容中直接提取验证码（同步版本）

        便捷方法，用于不需要关联 Email 实体的场景。

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果
        """
        if not content:
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response="Empty content",
            )

        return self._extractor.extract_code(content)

    async def extract_from_content_async(self, content: str) -> ExtractionResult:
        """
        从文本内容中直接提取验证码（异步版本）

        便捷方法，用于不需要关联 Email 实体的场景。

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果
        """
        if not content:
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response="Empty content",
            )

        return await self._extractor.extract_code_async(content)

    def extract_link_from_email(
        self,
        email: Email,
        mark_as_processed: bool = False,
    ) -> ExtractionResult:
        """
        从邮件中提取验证链接（同步版本）

        从邮件内容（优先纯文本，无则 HTML）中提取验证链接。

        Args:
            email: 邮件实体
            mark_as_processed: 是否标记邮件为已处理（默认 False）

        Returns:
            ExtractionResult 包含提取结果
        """
        content = email.body

        if not content:
            self._logger.warning(
                f"Email {email.id} has no body content, skipping link extraction"
            )
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response="Empty email body",
            )

        self._logger.debug(
            f"Extracting link from email {email.id}, "
            f"content_type={'text' if email.has_text_body else 'html'}, "
            f"content_length={len(content)}"
        )

        result = self._extractor.extract_link(content)

        self._log_result(email, result)
        self._mark_processed_if_needed(email, mark_as_processed)

        return result

    async def extract_link_from_email_async(
        self,
        email: Email,
        mark_as_processed: bool = False,
    ) -> ExtractionResult:
        """
        从邮件中提取验证链接（异步版本）

        从邮件内容（优先纯文本，无则 HTML）中提取验证链接。

        Args:
            email: 邮件实体
            mark_as_processed: 是否标记邮件为已处理（默认 False）

        Returns:
            ExtractionResult 包含提取结果
        """
        content = email.body

        if not content:
            self._logger.warning(
                f"Email {email.id} has no body content, skipping link extraction"
            )
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response="Empty email body",
            )

        self._logger.debug(
            f"Extracting link from email {email.id} (async), "
            f"content_type={'text' if email.has_text_body else 'html'}, "
            f"content_length={len(content)}"
        )

        result = await self._extractor.extract_link_async(content)

        self._log_result(email, result)
        self._mark_processed_if_needed(email, mark_as_processed)

        return result

    def extract_link_from_content(self, content: str) -> ExtractionResult:
        """
        从文本内容中直接提取验证链接（同步版本）

        便捷方法，用于不需要关联 Email 实体的场景。

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果
        """
        if not content:
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response="Empty content",
            )

        return self._extractor.extract_link(content)

    async def extract_link_from_content_async(self, content: str) -> ExtractionResult:
        """
        从文本内容中直接提取验证链接（异步版本）

        便捷方法，用于不需要关联 Email 实体的场景。

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果
        """
        if not content:
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response="Empty content",
            )

        return await self._extractor.extract_link_async(content)

    def unified_extract_from_content(self, content: str) -> ExtractionResult:
        """
        从文本内容中自动识别并提取验证信息（同步版本）

        便捷方法，用于不需要关联 Email 实体的场景。
        自动判断内容类型并提取验证码或验证链接。

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果
        """
        if not content:
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response="Empty content",
            )

        return self._extractor.extract(content)

    async def unified_extract_from_content_async(self, content: str) -> ExtractionResult:
        """
        从文本内容中自动识别并提取验证信息（异步版本）

        便捷方法，用于不需要关联 Email 实体的场景。
        自动判断内容类型并提取验证码或验证链接。

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果
        """
        if not content:
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response="Empty content",
            )

        return await self._extractor.extract_async(content)

    def unified_extract_from_email(
        self,
        email: Email,
        mark_as_processed: bool = False,
    ) -> ExtractionResult:
        """
        从邮件中自动识别并提取验证信息（同步版本）

        自动判断邮件类型并提取验证码或验证链接。
        如果同时存在验证码和链接，优先返回验证码，链接作为备用。

        Args:
            email: 邮件实体
            mark_as_processed: 是否标记邮件为已处理（默认 False）

        Returns:
            ExtractionResult 包含提取结果
        """
        content = email.body

        if not content:
            self._logger.warning(
                f"Email {email.id} has no body content, skipping unified extraction"
            )
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response="Empty email body",
            )

        self._logger.debug(
            f"Unified extracting from email {email.id}, "
            f"content_type={'text' if email.has_text_body else 'html'}, "
            f"content_length={len(content)}"
        )

        result = self._extractor.extract(content)

        self._log_result(email, result)
        self._mark_processed_if_needed(email, mark_as_processed)

        return result

    async def unified_extract_from_email_async(
        self,
        email: Email,
        mark_as_processed: bool = False,
    ) -> ExtractionResult:
        """
        从邮件中自动识别并提取验证信息（异步版本）

        自动判断邮件类型并提取验证码或验证链接。
        如果同时存在验证码和链接，优先返回验证码，链接作为备用。

        Args:
            email: 邮件实体
            mark_as_processed: 是否标记邮件为已处理（默认 False）

        Returns:
            ExtractionResult 包含提取结果
        """
        content = email.body

        if not content:
            self._logger.warning(
                f"Email {email.id} has no body content, skipping unified extraction"
            )
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response="Empty email body",
            )

        self._logger.debug(
            f"Unified extracting from email {email.id} (async), "
            f"content_type={'text' if email.has_text_body else 'html'}, "
            f"content_length={len(content)}"
        )

        result = await self._extractor.extract_async(content)

        self._log_result(email, result)
        self._mark_processed_if_needed(email, mark_as_processed)

        return result

    def _log_result(self, email: Email, result: ExtractionResult) -> None:
        """记录提取结果（支持 code 和 link 类型）"""
        if result.is_successful:
            extract_type = "link" if result.type == ExtractionType.LINK else "code"
            self._logger.info(
                f"Successfully extracted {extract_type} from email {email.id}: "
                f"type={result.type.value}, confidence={result.confidence}"
            )
        else:
            self._logger.debug(f"No verification info found in email {email.id}")

    def _mark_processed_if_needed(
        self, email: Email, mark_as_processed: bool
    ) -> None:
        """可选：标记邮件为已处理"""
        if mark_as_processed and not email.is_processed:
            try:
                email.mark_as_processed()
                self._logger.debug(f"Marked email {email.id} as processed")
            except Exception as e:
                self._logger.warning(
                    f"Failed to mark email {email.id} as processed: {e}"
                )
