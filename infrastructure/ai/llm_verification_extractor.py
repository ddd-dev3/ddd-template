"""使用 LangChain 的验证信息提取器实现"""

import json
import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from domain.ai.value_objects.extraction_result import ExtractionResult
from domain.ai.value_objects.extraction_type import ExtractionType


class LlmVerificationExtractor:
    """
    使用 LangChain 的验证信息提取器实现

    通过 LangChain 调用 OpenAI 兼容 API 从邮件内容中提取验证码和验证链接。
    支持中英文邮件，能处理 HTML 格式邮件。
    内置重试机制和异步支持。

    功能:
        - 验证码提取 (extract_code/extract_code_async)
        - 验证链接提取 (extract_link/extract_link_async)

    Attributes:
        PROMPT_TEMPLATE: 提取验证码的 prompt 模板
        LINK_PROMPT_TEMPLATE: 提取验证链接的 prompt 模板
        DEFAULT_MODEL: 默认使用的模型
        DEFAULT_API_BASE: 默认 API 地址
        DEFAULT_TIMEOUT: 默认超时时间
        MAX_CONTENT_LENGTH: 邮件内容最大长度（避免 token 超限）
        DEFAULT_MAX_RETRIES: 默认最大重试次数
    """

    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_API_BASE = "https://api.openai.com/v1"
    DEFAULT_TIMEOUT = 30.0
    MAX_CONTENT_LENGTH = 4000
    DEFAULT_MAX_RETRIES = 3

    PROMPT_TEMPLATE = """你是一个专门提取验证码的 AI 助手。请分析以下邮件内容，提取其中的验证码。

邮件内容：
---
{content}
---

请按以下 JSON 格式返回结果（只返回 JSON，不要其他文字）：
{{
    "found": true/false,
    "code": "提取的验证码" 或 null,
    "confidence": 0.0-1.0 的置信度
}}

注意：
1. 验证码通常是 4-8 位的数字或字母数字组合
2. 如果邮件中没有验证码，found 设为 false，code 设为 null
3. 如果有多个可能的验证码，只返回最可能的一个
4. 忽略邮件中的 HTML 标签、退订链接、版权信息等"""

    LINK_PROMPT_TEMPLATE = """你是一个专门提取验证链接的 AI 助手。请分析以下邮件内容，提取其中的验证/确认链接。

邮件内容：
---
{content}
---

请按以下 JSON 格式返回结果（只返回 JSON，不要其他文字）：
{{
    "found": true/false,
    "link": "提取的验证链接 URL" 或 null,
    "confidence": 0.0-1.0 的置信度
}}

**验证链接识别规则：**
1. 包含关键词：verify, confirm, activate, validate, email-verification, signup, register
2. 带有 token、code、key 等查询参数
3. 用于邮箱验证、账号激活、注册确认

**排除链接：**
- 退订链接（unsubscribe、optout）
- 社交媒体（facebook、twitter、linkedin）
- 隐私政策/服务条款（privacy、terms）
- 帮助中心（contact、help、support）

**注意：**
1. 无验证链接时 found=false, link=null
2. 多个验证链接时只返回最可能的一个
3. 返回完整 URL（含查询参数）"""

    UNIFIED_PROMPT_TEMPLATE = """你是一个专门提取邮件验证信息的 AI 助手。请分析以下邮件内容，自动识别并提取验证码或验证链接。

邮件内容：
---
{content}
---

请按以下 JSON 格式返回结果（只返回 JSON，不要其他文字）：
{{
    "type": "code" | "link" | "unknown",
    "code": "提取的验证码" 或 null,
    "link": "提取的验证链接 URL" 或 null,
    "backup_link": "备用验证链接（仅当同时存在验证码和链接时）" 或 null,
    "confidence": 0.0-1.0 的置信度
}}

**识别规则：**

1. **验证码特征：**
   - 4-8 位数字或字母数字组合
   - 上下文提示：验证码、verification code、OTP、PIN

2. **验证链接特征：**
   - 包含关键词：verify, confirm, activate, validate, email-verification, signup, register
   - 带有 token、code、key 等查询参数
   - 用于邮箱验证、账号激活、注册确认

3. **排除内容：**
   - 退订链接（unsubscribe、optout）
   - 社交媒体链接（facebook、twitter、linkedin）
   - 隐私政策/服务条款（privacy、terms）
   - 帮助中心（contact、help、support）

**优先级规则：**
1. 同时存在验证码和验证链接时：type="code"，code 填值，backup_link 填链接
2. 仅验证码：type="code"，code 填值，link 和 backup_link 为 null
3. 仅验证链接：type="link"，link 填值，code 和 backup_link 为 null
4. 都没有：type="unknown"，所有字段为 null

**注意：**
1. 返回完整 URL（含查询参数）
2. 验证码只返回最可能的一个
3. 链接只返回最可能的验证链接"""

    DEFAULT_MAX_TOKENS = 1024

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        api_base: str = DEFAULT_API_BASE,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        logger: Optional[logging.Logger] = None,
    ):
        """
        初始化 LLM 验证信息提取器

        Args:
            api_key: OpenAI API Key（必须非空）
            model: 使用的模型名称，默认 gpt-4o-mini
            api_base: API 地址，默认 OpenAI 官方地址
            timeout: API 调用超时时间（秒）
            max_retries: 最大重试次数，默认 3 次
            max_tokens: 最大生成 token 数，默认 1024
            logger: 日志记录器

        Raises:
            ValueError: 如果 api_key 为空
        """
        # H3: API Key 验证
        if not api_key or not api_key.strip():
            raise ValueError(
                "OPENAI_API_KEY is required. "
                "Please set it in environment variables or .env file."
            )

        self._api_key = api_key
        self._model = model
        self._api_base = api_base
        self._timeout = timeout
        self._max_retries = max_retries
        self._max_tokens = max_tokens
        self._logger = logger or logging.getLogger(__name__)

        # 初始化 LangChain ChatOpenAI
        # 使用 extra_body 确保 max_tokens 被发送（某些 API 网关需要）
        self._llm = ChatOpenAI(
            api_key=api_key,
            model=model,
            base_url=api_base,
            temperature=0,  # 确定性输出
            timeout=timeout,
            max_retries=max_retries,
            extra_body={"max_tokens": max_tokens},
        )

    def extract_code(self, content: str) -> ExtractionResult:
        """
        从邮件内容中提取验证码（同步版本）

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果
        """
        try:
            truncated_content = content[: self.MAX_CONTENT_LENGTH]
            prompt = self.PROMPT_TEMPLATE.format(content=truncated_content)

            response = self._llm.invoke([HumanMessage(content=prompt)])
            return self._parse_response(response.content)

        except Exception as e:
            self._logger.error(f"AI extraction failed: {e}")
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response=str(e),
            )

    async def extract_code_async(self, content: str) -> ExtractionResult:
        """
        从邮件内容中提取验证码（异步版本）

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果
        """
        try:
            truncated_content = content[: self.MAX_CONTENT_LENGTH]
            prompt = self.PROMPT_TEMPLATE.format(content=truncated_content)

            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            return self._parse_response(response.content)

        except Exception as e:
            self._logger.error(f"AI extraction failed (async): {e}")
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response=str(e),
            )

    def _parse_response(self, response: str) -> ExtractionResult:
        """
        解析 LLM 响应

        Args:
            response: LLM 返回的原始响应文本

        Returns:
            ExtractionResult 包含解析后的结果
        """
        try:
            # 尝试提取 JSON 部分（LLM 可能添加其他文字）
            start = response.find("{")
            end = response.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                if data.get("found") and data.get("code"):
                    return ExtractionResult(
                        type=ExtractionType.CODE,
                        code=data["code"],
                        confidence=float(data.get("confidence", 0.9)),
                        raw_response=response,
                    )

            # 未找到验证码或解析失败
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response=response,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self._logger.warning(f"Failed to parse LLM response: {e}")
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response=response,
            )

    def extract_link(self, content: str) -> ExtractionResult:
        """
        从邮件内容中提取验证链接（同步版本）

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果
        """
        try:
            truncated_content = content[: self.MAX_CONTENT_LENGTH]
            prompt = self.LINK_PROMPT_TEMPLATE.format(content=truncated_content)

            response = self._llm.invoke([HumanMessage(content=prompt)])
            return self._parse_link_response(response.content)

        except Exception as e:
            self._logger.error(f"AI link extraction failed: {e}")
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response=str(e),
            )

    async def extract_link_async(self, content: str) -> ExtractionResult:
        """
        从邮件内容中提取验证链接（异步版本）

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果
        """
        try:
            truncated_content = content[: self.MAX_CONTENT_LENGTH]
            prompt = self.LINK_PROMPT_TEMPLATE.format(content=truncated_content)

            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            return self._parse_link_response(response.content)

        except Exception as e:
            self._logger.error(f"AI link extraction failed (async): {e}")
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response=str(e),
            )

    def extract(self, content: str) -> ExtractionResult:
        """
        从邮件内容中自动识别并提取验证信息（同步版本）

        自动判断邮件类型并提取验证码或验证链接。
        如果同时存在验证码和链接，优先返回验证码，链接作为备用。

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果
        """
        try:
            truncated_content = content[: self.MAX_CONTENT_LENGTH]
            prompt = self.UNIFIED_PROMPT_TEMPLATE.format(content=truncated_content)

            response = self._llm.invoke([HumanMessage(content=prompt)])
            return self._parse_unified_response(response.content)

        except Exception as e:
            self._logger.error(f"AI unified extraction failed: {e}")
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response=str(e),
            )

    async def extract_async(self, content: str) -> ExtractionResult:
        """
        从邮件内容中自动识别并提取验证信息（异步版本）

        自动判断邮件类型并提取验证码或验证链接。
        如果同时存在验证码和链接，优先返回验证码，链接作为备用。

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果
        """
        try:
            truncated_content = content[: self.MAX_CONTENT_LENGTH]
            prompt = self.UNIFIED_PROMPT_TEMPLATE.format(content=truncated_content)

            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            return self._parse_unified_response(response.content)

        except Exception as e:
            self._logger.error(f"AI unified extraction failed (async): {e}")
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response=str(e),
            )

    def _parse_unified_response(self, response: str) -> ExtractionResult:
        """
        解析统一提取的 LLM 响应

        Args:
            response: LLM 返回的原始响应文本

        Returns:
            ExtractionResult 包含解析后的结果
        """
        try:
            # 尝试提取 JSON 部分（LLM 可能添加其他文字）
            start = response.find("{")
            end = response.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                type_str = data.get("type", "unknown").lower()
                code = data.get("code")
                link = data.get("link")
                backup_link = data.get("backup_link")
                confidence = float(data.get("confidence", 0.9))

                # 验证码优先
                if type_str == "code" and code:
                    return ExtractionResult(
                        type=ExtractionType.CODE,
                        code=code,
                        backup_link=self._validate_url(backup_link),
                        confidence=confidence,
                        raw_response=response,
                    )

                # 链接
                if type_str == "link" and link:
                    validated_link = self._validate_url(link)
                    if validated_link:
                        return ExtractionResult(
                            type=ExtractionType.LINK,
                            link=validated_link,
                            confidence=confidence,
                            raw_response=response,
                        )

            # 未找到验证信息或解析失败
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response=response,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self._logger.warning(f"Failed to parse unified LLM response: {e}")
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response=response,
            )

    def _validate_url(self, url: Optional[str]) -> Optional[str]:
        """
        验证 URL 格式

        Args:
            url: 待验证的 URL

        Returns:
            验证通过返回原 URL，否则返回 None
        """
        if not url or not url.strip():
            return None
        if not url.startswith(("http://", "https://")):
            return None
        # 检查域名
        protocol_end = url.find("://") + 3
        path_start = url.find("/", protocol_end)
        domain = url[protocol_end:path_start] if path_start > 0 else url[protocol_end:]
        if ":" in domain:
            domain = domain.split(":")[0]
        if not domain or "." not in domain:
            return None
        return url

    def _parse_link_response(self, response: str) -> ExtractionResult:
        """
        解析链接提取的 LLM 响应

        Args:
            response: LLM 返回的原始响应文本

        Returns:
            ExtractionResult 包含解析后的结果
        """
        try:
            # 尝试提取 JSON 部分（LLM 可能添加其他文字）
            # 使用更健壮的方法：查找第一个 { 和最后一个 }，但需要处理嵌套情况
            start = response.find("{")
            end = response.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                if data.get("found") and data.get("link"):
                    link = data["link"]
                    # 使用 _validate_url 进行 URL 格式验证
                    validated_link = self._validate_url(link)
                    if validated_link:
                        return ExtractionResult(
                            type=ExtractionType.LINK,
                            link=validated_link,
                            confidence=float(data.get("confidence", 0.9)),
                            raw_response=response,
                        )
                    else:
                        self._logger.warning(f"Invalid URL format: {link}")
                        return ExtractionResult(
                            type=ExtractionType.UNKNOWN,
                            confidence=0.0,
                            raw_response=response,
                        )

            # 未找到验证链接或解析失败
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response=response,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self._logger.warning(f"Failed to parse link LLM response: {e}")
            return ExtractionResult(
                type=ExtractionType.UNKNOWN,
                confidence=0.0,
                raw_response=response,
            )
