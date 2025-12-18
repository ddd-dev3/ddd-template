"""验证信息提取器接口"""

from typing import Protocol

from domain.ai.value_objects.extraction_result import ExtractionResult


class VerificationExtractor(Protocol):
    """
    验证信息提取器接口

    领域服务，定义从邮件内容提取验证码/链接的契约。
    具体实现在 infrastructure 层（如 LLM 实现）。

    设计说明:
    - 使用 Protocol 而非抽象基类，支持结构化子类型
    - 方法返回值对象 ExtractionResult，封装完整提取结果
    - 提供同步和异步两种方法

    方法说明:
    - extract_code/extract_code_async: 仅提取验证码 (Story 3.1)
    - extract_link/extract_link_async: 仅提取验证链接 (Story 3.2)
    - extract/extract_async: 统一提取，自动识别类型 (Story 3.3)
    """

    def extract_code(self, content: str) -> ExtractionResult:
        """
        从邮件内容中提取验证码（同步版本）

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果，如果成功则 type=CODE 且 code 有值

        Note:
            - 实现应处理中英文邮件
            - 实现应能处理 HTML 格式邮件
            - 提取失败时返回 type=UNKNOWN
        """
        ...

    async def extract_code_async(self, content: str) -> ExtractionResult:
        """
        从邮件内容中提取验证码（异步版本）

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果，如果成功则 type=CODE 且 code 有值

        Note:
            - 实现应处理中英文邮件
            - 实现应能处理 HTML 格式邮件
            - 提取失败时返回 type=UNKNOWN
        """
        ...

    def extract_link(self, content: str) -> ExtractionResult:
        """
        从邮件内容中提取验证链接（同步版本）

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果，如果成功则 type=LINK 且 link 有值

        Note:
            - 实现应处理中英文邮件
            - 实现应能处理 HTML 格式邮件
            - 智能识别验证/确认链接，排除退订、社交媒体等无关链接
            - 提取失败时返回 type=UNKNOWN
        """
        ...

    async def extract_link_async(self, content: str) -> ExtractionResult:
        """
        从邮件内容中提取验证链接（异步版本）

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果，如果成功则 type=LINK 且 link 有值

        Note:
            - 实现应处理中英文邮件
            - 实现应能处理 HTML 格式邮件
            - 智能识别验证/确认链接，排除退订、社交媒体等无关链接
            - 提取失败时返回 type=UNKNOWN
        """
        ...

    def extract(self, content: str) -> ExtractionResult:
        """
        从邮件内容中自动识别并提取验证信息（同步版本）

        自动判断邮件类型并提取验证码或验证链接。
        如果同时存在验证码和链接，优先返回验证码，链接作为备用。

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果：
            - type=CODE 且 code 有值（可能有 backup_link）
            - type=LINK 且 link 有值
            - type=UNKNOWN 如果无验证信息

        Note:
            - 使用单次 LLM 调用完成类型识别和内容提取
            - 同时存在验证码和链接时，验证码优先，链接存入 backup_link
            - 实现应处理中英文邮件
            - 实现应能处理 HTML 格式邮件
        """
        ...

    async def extract_async(self, content: str) -> ExtractionResult:
        """
        从邮件内容中自动识别并提取验证信息（异步版本）

        自动判断邮件类型并提取验证码或验证链接。
        如果同时存在验证码和链接，优先返回验证码，链接作为备用。

        Args:
            content: 邮件正文内容（纯文本或 HTML）

        Returns:
            ExtractionResult 包含提取结果：
            - type=CODE 且 code 有值（可能有 backup_link）
            - type=LINK 且 link 有值
            - type=UNKNOWN 如果无验证信息

        Note:
            - 使用单次 LLM 调用完成类型识别和内容提取
            - 同时存在验证码和链接时，验证码优先，链接存入 backup_link
            - 实现应处理中英文邮件
            - 实现应能处理 HTML 格式邮件
        """
        ...
